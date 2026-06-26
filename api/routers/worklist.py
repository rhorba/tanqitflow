"""Worklist API: generate, list, patch status, export."""
import csv
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import UserRole, get_current_user, require_role
from database import get_db
from domain.worklist_ranker import DmaLeakSignal, rank_dmas
from models.user import User
from schemas.leak import WorklistGenerateRequest, WorklistItemOut, WorklistStatusPatch

router = APIRouter(prefix="/api/v1/worklist", tags=["worklist"])

_Auth = Annotated[User, Depends(get_current_user)]
_DB = Annotated[AsyncSession, Depends(get_db)]
_AnalystPlus = Depends(require_role(UserRole.analyst, UserRole.utility_admin))
_AdminOnly = Depends(require_role(UserRole.utility_admin))


@router.post("/generate", response_model=dict, status_code=status.HTTP_200_OK, summary="Generate ROI-ranked repair worklist", description="Ranks all DMAs by NRW repair ROI score (loss_m3 × water_cost × confidence/100) and upserts results into the worklist. Existing entries are updated in place.")
async def generate_worklist(
    body: WorklistGenerateRequest,
    db: _DB,
    _user: Annotated[User, Depends(require_role(UserRole.utility_admin, UserRole.analyst))],
) -> dict:
    """Rank all DMAs by NRW repair ROI and upsert into worklist_item."""

    # Fetch latest leak_indicator per DMA (most recent indicator_date)
    rows = await db.execute(
        text("""
            SELECT DISTINCT ON (li.dma_code)
                li.dma_code,
                d.name   AS dma_name,
                d.id::text AS dma_id,
                li.confidence_score,
                li.alert_type,
                COALESCE(bp.nrw_m3, 0) AS nrw_m3
            FROM leak_indicator li
            LEFT JOIN dma d ON d.code = li.dma_code
            LEFT JOIN LATERAL (
                SELECT nrw_m3
                FROM balance_period
                WHERE dma_code = li.dma_code
                ORDER BY period_start DESC
                LIMIT 1
            ) bp ON true
            ORDER BY li.dma_code, li.indicator_date DESC
        """)
    )
    signals = [
        DmaLeakSignal(
            dma_code=r.dma_code,
            dma_name=r.dma_name,
            dma_id=r.dma_id,
            nrw_m3_per_month=float(r.nrw_m3 or 0),
            confidence_score=r.confidence_score,
            alert_type=r.alert_type,
        )
        for r in rows
    ]

    ranked = rank_dmas(signals, water_cost_mad_per_m3=body.water_cost_mad_per_m3)

    # Upsert worklist_item (UNIQUE on dma_code — update if already exists)
    for item in ranked:
        await db.execute(
            text("""
                INSERT INTO worklist_item
                    (dma_id, dma_code, dma_name, rank,
                     estimated_loss_m3_per_month, savings_mad_est,
                     confidence_score, alert_type, status, generated_at, updated_at)
                VALUES
                    (:dma_id, :dma_code, :dma_name, :rank,
                     :loss, :savings,
                     :confidence, :alert_type, 'OPEN', NOW(), NOW())
                ON CONFLICT (dma_code)
                DO UPDATE SET
                    dma_id                      = EXCLUDED.dma_id,
                    dma_name                    = EXCLUDED.dma_name,
                    rank                        = EXCLUDED.rank,
                    estimated_loss_m3_per_month = EXCLUDED.estimated_loss_m3_per_month,
                    savings_mad_est             = EXCLUDED.savings_mad_est,
                    confidence_score            = EXCLUDED.confidence_score,
                    alert_type                  = EXCLUDED.alert_type,
                    generated_at                = NOW(),
                    updated_at                  = NOW()
            """),
            {
                "dma_id": item.dma_id, "dma_code": item.dma_code, "dma_name": item.dma_name,
                "rank": item.rank, "loss": item.estimated_loss_m3_per_month,
                "savings": item.savings_mad_est, "confidence": item.confidence_score,
                "alert_type": item.alert_type,
            },
        )

    await db.commit()
    return {"generated": len(ranked), "water_cost_mad_per_m3": body.water_cost_mad_per_m3}


@router.get("", response_model=dict, summary="List worklist items", description="Paginated repair worklist sorted by rank (ascending). Filter by status: OPEN | IN_PROGRESS | RESOLVED | DEFERRED.")
async def list_worklist(
    _user: _Auth,
    db: _DB,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    _role: Annotated[User, _AnalystPlus] = None,
) -> dict:
    filters = []
    params: dict = {"limit": size, "offset": (page - 1) * size}

    if status_filter:
        filters.append("status = :status")
        params["status"] = status_filter

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM worklist_item {where}"), params
    )
    total: int = count_row.scalar() or 0

    rows = await db.execute(
        text(
            f"SELECT id::text, dma_code, dma_name, rank, "
            f"estimated_loss_m3_per_month, savings_mad_est, "
            f"confidence_score, alert_type, status, generated_at, updated_at "
            f"FROM worklist_item {where} "
            f"ORDER BY rank ASC "
            f"LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    items = [
        WorklistItemOut(
            id=r.id,
            dma_code=r.dma_code,
            dma_name=r.dma_name,
            rank=r.rank,
            estimated_loss_m3_per_month=float(r.estimated_loss_m3_per_month) if r.estimated_loss_m3_per_month else None,
            savings_mad_est=float(r.savings_mad_est) if r.savings_mad_est else None,
            confidence_score=r.confidence_score,
            alert_type=r.alert_type,
            status=r.status,
            generated_at=r.generated_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]

    return {"data": items, "total": total, "page": page, "size": size}


@router.patch("/{item_id}", response_model=WorklistItemOut, summary="Update worklist item status", description="Transition a worklist item through its lifecycle: OPEN → IN_PROGRESS → RESOLVED | DEFERRED.")
async def update_worklist_status(
    item_id: uuid.UUID,
    body: WorklistStatusPatch,
    db: _DB,
    _user: Annotated[User, Depends(require_role(UserRole.analyst, UserRole.utility_admin))],
) -> WorklistItemOut:
    row = await db.execute(
        text("SELECT id::text FROM worklist_item WHERE id = :id"),
        {"id": str(item_id)},
    )
    if not row.first():
        raise HTTPException(status_code=404, detail="Worklist item not found")

    await db.execute(
        text("UPDATE worklist_item SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"status": body.status, "id": str(item_id)},
    )
    await db.commit()

    updated = await db.execute(
        text(
            "SELECT id::text, dma_code, dma_name, rank, "
            "estimated_loss_m3_per_month, savings_mad_est, "
            "confidence_score, alert_type, status, generated_at, updated_at "
            "FROM worklist_item WHERE id = :id"
        ),
        {"id": str(item_id)},
    )
    r = updated.first()
    return WorklistItemOut(
        id=r.id, dma_code=r.dma_code, dma_name=r.dma_name, rank=r.rank,
        estimated_loss_m3_per_month=float(r.estimated_loss_m3_per_month) if r.estimated_loss_m3_per_month else None,
        savings_mad_est=float(r.savings_mad_est) if r.savings_mad_est else None,
        confidence_score=r.confidence_score, alert_type=r.alert_type, status=r.status,
        generated_at=r.generated_at, updated_at=r.updated_at,
    )


@router.get("/export", summary="Export worklist as CSV", description="Download the full worklist as a UTF-8-sig CSV file, ordered by rank. Compatible with Excel and French locale decimal separators.")
async def export_worklist(
    _user: _Auth,
    db: _DB,
    format: Annotated[str, Query(pattern="^(csv)$")] = "csv",
    _role: Annotated[User, _AnalystPlus] = None,
) -> StreamingResponse:
    rows = await db.execute(
        text(
            "SELECT dma_code, dma_name, rank, estimated_loss_m3_per_month, "
            "savings_mad_est, confidence_score, alert_type, status "
            "FROM worklist_item ORDER BY rank ASC"
        )
    )
    items = rows.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Rank", "DMA Code", "DMA Name",
        "Est. Loss m³/month", "Savings MAD/month",
        "Confidence %", "Alert Type", "Status",
    ])
    for r in items:
        writer.writerow([
            r.rank, r.dma_code, r.dma_name or "",
            round(float(r.estimated_loss_m3_per_month or 0), 2),
            round(float(r.savings_mad_est or 0), 2),
            r.confidence_score, r.alert_type, r.status,
        ])

    buf.seek(0)
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=worklist.csv"},
    )
