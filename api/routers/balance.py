"""Balance API: NRW computation results and KPI summaries."""
from calendar import monthrange
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import UserRole, get_current_user, require_role
from database import get_db
from models.user import User
from schemas.balance import (
    BalancePeriodOut,
    BalanceSummaryOut,
    BalanceTrendPoint,
    ComputeRequest,
)
from services.balance import compute_balance, get_summary, get_trend

router = APIRouter(prefix="/api/v1/balance", tags=["balance"])

_Auth = Annotated[User, Depends(get_current_user)]
_DB = Annotated[AsyncSession, Depends(get_db)]
_AnalystPlus = Depends(require_role(UserRole.analyst, UserRole.utility_admin))


# ---------------------------------------------------------------------------
# GET /summary  — dashboard KPI cards
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BalanceSummaryOut)
async def balance_summary(
    _user: _Auth,
    db: _DB,
    _role: Annotated[User, _AnalystPlus] = None,
) -> BalanceSummaryOut:
    data = await get_summary(db)
    return BalanceSummaryOut(**data)


# ---------------------------------------------------------------------------
# GET /trend  — 12-month sparkline
# ---------------------------------------------------------------------------

@router.get("/trend", response_model=list[BalanceTrendPoint])
async def balance_trend(
    _user: _Auth,
    db: _DB,
    months: Annotated[int, Query(ge=1, le=36)] = 12,
    _role: Annotated[User, _AnalystPlus] = None,
) -> list[BalanceTrendPoint]:
    data = await get_trend(db, months)
    return [BalanceTrendPoint(**row) for row in data]


# ---------------------------------------------------------------------------
# GET /periods  — paginated list
# ---------------------------------------------------------------------------

@router.get("/periods", response_model=dict)
async def list_periods(
    _user: _Auth,
    db: _DB,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    dma_code: Annotated[str | None, Query()] = None,
    flag: Annotated[str | None, Query()] = None,
    _role: Annotated[User, _AnalystPlus] = None,
) -> dict:
    filters = []
    params: dict = {"limit": size, "offset": (page - 1) * size}

    if dma_code:
        filters.append("dma_code = :dma_code")
        params["dma_code"] = dma_code
    if flag:
        filters.append("flag_level = :flag")
        params["flag"] = flag

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM balance_period {where}"), params
    )
    total: int = count_row.scalar() or 0

    rows = await db.execute(
        text(
            f"SELECT id::text, dma_code, period_start, period_end, "
            f"siv_m3, scv_m3, nrw_m3, nrw_pct, leakage_index, flag_level, computed_at "
            f"FROM balance_period {where} "
            f"ORDER BY period_start DESC, dma_code "
            f"LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    items = [
        BalancePeriodOut(
            id=r.id,
            dma_code=r.dma_code,
            period_start=r.period_start,
            period_end=r.period_end,
            siv_m3=float(r.siv_m3),
            scv_m3=float(r.scv_m3),
            nrw_m3=float(r.nrw_m3),
            nrw_pct=float(r.nrw_pct),
            leakage_index=float(r.leakage_index) if r.leakage_index else None,
            flag_level=r.flag_level,
            computed_at=r.computed_at,
        )
        for r in rows
    ]

    return {"data": items, "total": total, "page": page, "size": size}


# ---------------------------------------------------------------------------
# POST /compute  — on-demand trigger (utility_admin only)
# ---------------------------------------------------------------------------

@router.post("/compute", response_model=BalancePeriodOut, status_code=status.HTTP_200_OK)
async def trigger_compute(
    body: ComputeRequest,
    db: _DB,
    _user: Annotated[User, Depends(require_role(UserRole.utility_admin))],
) -> BalancePeriodOut:
    if not (1 <= body.month <= 12):
        raise HTTPException(status_code=422, detail="month must be 1–12")

    last_day = monthrange(body.year, body.month)[1]
    period_start = datetime(body.year, body.month, 1, tzinfo=UTC)
    period_end = datetime(body.year, body.month, last_day, 23, 59, 59, tzinfo=UTC)

    result = await compute_balance(db, body.dma_code, period_start, period_end)
    return BalancePeriodOut(**result)
