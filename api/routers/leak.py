"""Leak detection API: indicators + anomaly events."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import UserRole, get_current_user, require_role
from database import get_db
from models.user import User
from schemas.leak import AnomalyEventOut, LeakIndicatorOut

router = APIRouter(prefix="/api/v1/leak", tags=["leak-detection"])

_Auth = Annotated[User, Depends(get_current_user)]
_DB = Annotated[AsyncSession, Depends(get_db)]
_AnalystPlus = Depends(require_role(UserRole.analyst, UserRole.utility_admin))


@router.get("/indicators", response_model=dict, summary="List leak indicators", description="Paginated MNF leak indicators per DMA. Each row combines MNF flag, Z-score flag, Isolation Forest flag, and a weighted confidence score (0–100).")
async def list_indicators(
    _user: _Auth,
    db: _DB,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    dma_code: Annotated[str | None, Query()] = None,
    alert_type: Annotated[str | None, Query()] = None,
    flagged_only: Annotated[bool, Query()] = False,
    _role: Annotated[User, _AnalystPlus] = None,
) -> dict:
    filters = []
    params: dict = {"limit": size, "offset": (page - 1) * size}

    if dma_code:
        filters.append("dma_code = :dma_code")
        params["dma_code"] = dma_code
    if alert_type:
        filters.append("alert_type = :alert_type")
        params["alert_type"] = alert_type
    if flagged_only:
        filters.append("(mnf_flag = true OR zscore_flag = true OR if_flag = true)")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM leak_indicator {where}"), params  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
    )
    total: int = count_row.scalar() or 0

    rows = await db.execute(
        text(  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
            f"SELECT id::text, dma_code, indicator_date, "
            f"mnf_m3h, baseline_m3h, mnf_flag, "
            f"max_zscore, zscore_flag, if_anomaly_score, if_flag, "
            f"confidence_score, alert_type, computed_at "
            f"FROM leak_indicator {where} "
            f"ORDER BY indicator_date DESC, dma_code "
            f"LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    items = [
        LeakIndicatorOut(
            id=r.id,
            dma_code=r.dma_code,
            indicator_date=r.indicator_date,
            mnf_m3h=float(r.mnf_m3h) if r.mnf_m3h is not None else None,
            baseline_m3h=float(r.baseline_m3h) if r.baseline_m3h is not None else None,
            mnf_flag=r.mnf_flag,
            max_zscore=float(r.max_zscore) if r.max_zscore is not None else None,
            zscore_flag=r.zscore_flag,
            if_anomaly_score=float(r.if_anomaly_score) if r.if_anomaly_score is not None else None,
            if_flag=r.if_flag,
            confidence_score=r.confidence_score,
            alert_type=r.alert_type,
            computed_at=r.computed_at,
        )
        for r in rows
    ]

    return {"data": items, "total": total, "page": page, "size": size}


@router.get("/anomalies", response_model=dict, summary="List anomaly events", description="Paginated Z-score anomaly events from the rolling 30-day detection window. Filter by DMA code or metric name.")
async def list_anomalies(
    _user: _Auth,
    db: _DB,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
    dma_code: Annotated[str | None, Query()] = None,
    metric: Annotated[str | None, Query()] = None,
    _role: Annotated[User, _AnalystPlus] = None,
) -> dict:
    filters = []
    params: dict = {"limit": size, "offset": (page - 1) * size}

    if dma_code:
        filters.append("dma_code = :dma_code")
        params["dma_code"] = dma_code
    if metric:
        filters.append("metric = :metric")
        params["metric"] = metric

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM anomaly_event {where}"), params  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
    )
    total: int = count_row.scalar() or 0

    rows = await db.execute(
        text(  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
            f"SELECT id::text, dma_code, event_time, metric, value, zscore "
            f"FROM anomaly_event {where} "
            f"ORDER BY event_time DESC "
            f"LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    items = [
        AnomalyEventOut(
            id=r.id, dma_code=r.dma_code, event_time=r.event_time,
            metric=r.metric, value=float(r.value), zscore=float(r.zscore),
        )
        for r in rows
    ]

    return {"data": items, "total": total, "page": page, "size": size}
