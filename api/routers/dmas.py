"""DMA CRUD — analyst+ can read, utility_admin can write."""
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user, require_role
from database import get_db
from models.dma import DMA
from models.user import User, UserRole
from schemas.dma import DMACreate, DMAResponse, DMAUpdate

router = APIRouter(prefix="/api/v1/dmas", tags=["dmas"])

AnyAuth = Annotated[User, Depends(get_current_user)]
AdminOnly = Annotated[User, Depends(require_role(UserRole.utility_admin))]


async def _set_geometry(db: AsyncSession, dma_id: uuid.UUID, geojson: dict) -> None:
    """Write a GeoJSON geometry to the PostGIS geometry column via ST_GeomFromGeoJSON."""
    await db.execute(
        text("UPDATE dma SET geometry = ST_GeomFromGeoJSON(:g) WHERE id = :id"),
        {"g": json.dumps(geojson), "id": str(dma_id)},
    )


@router.get("/geojson", response_model=None, summary="DMA GeoJSON + heatmap points", description="GeoJSON FeatureCollection of all active DMAs with their latest NRW balance. Also returns `heat_points` (lat/lng/intensity) for the NRW heatmap layer.")
async def get_dmas_geojson(
    _user: AnyAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    GeoJSON FeatureCollection of all active DMAs with their latest NRW balance data.
    Also returns heat_points (centroid lat/lng + NRW intensity) for the heatmap layer.
    """
    result = await db.execute(text("""
        SELECT
            d.id::text                              AS id,
            d.code,
            d.name,
            d.zone,
            d.pipe_length_km::float                AS pipe_length_km,
            d.connection_count,
            CASE WHEN d.geometry IS NOT NULL
                 THEN ST_AsGeoJSON(d.geometry)::json
                 ELSE NULL END                      AS geom_json,
            CASE WHEN d.geometry IS NOT NULL
                 THEN ST_Y(ST_Centroid(d.geometry))
                 ELSE NULL END                      AS centroid_lat,
            CASE WHEN d.geometry IS NOT NULL
                 THEN ST_X(ST_Centroid(d.geometry))
                 ELSE NULL END                      AS centroid_lon,
            b.nrw_pct::float                        AS nrw_pct,
            b.nrw_m3::float                         AS nrw_m3,
            b.siv_m3::float                         AS siv_m3,
            b.scv_m3::float                         AS scv_m3,
            b.flag_level
        FROM dma d
        LEFT JOIN LATERAL (
            SELECT nrw_pct, nrw_m3, siv_m3, scv_m3, flag_level
            FROM balance_period
            WHERE dma_code = d.code
            ORDER BY period_start DESC
            LIMIT 1
        ) b ON true
        WHERE d.is_active = true
        ORDER BY d.code
    """))

    rows = result.mappings().all()
    features = []
    heat_points: list[list[float]] = []

    for row in rows:
        geom = row["geom_json"]
        # asyncpg may return ::json as a dict already; guard against raw string
        if isinstance(geom, str):
            geom = json.loads(geom)

        props: dict = {
            "id": row["id"],
            "code": row["code"],
            "name": row["name"],
            "zone": row["zone"],
            "pipe_length_km": row["pipe_length_km"],
            "connection_count": row["connection_count"],
            "nrw_pct": row["nrw_pct"],
            "nrw_m3": row["nrw_m3"],
            "siv_m3": row["siv_m3"],
            "scv_m3": row["scv_m3"],
            "flag_level": row["flag_level"] or "normal",
        }

        features.append({
            "type": "Feature",
            "id": row["id"],
            "geometry": geom,
            "properties": props,
        })

        if row["centroid_lat"] is not None and row["centroid_lon"] is not None:
            intensity = min((row["nrw_pct"] or 0.0) / 100.0, 1.0)
            heat_points.append([
                float(row["centroid_lat"]),
                float(row["centroid_lon"]),
                intensity,
            ])

    return {
        "type": "FeatureCollection",
        "features": features,
        "heat_points": heat_points,
    }


@router.get("/table", response_model=dict, summary="DMA table view with balance + leak data", description="Paginated DMA list enriched with the latest balance period and leak indicator. Used by the DMA table UI.")
async def list_dmas_table(
    _user: AnyAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict:
    """
    DMA list enriched with latest balance period + latest leak indicator.
    Used by the DMA table view in the frontend.
    """
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM dma WHERE is_active = true")
    )
    total: int = count_result.scalar() or 0

    rows = await db.execute(
        text("""
            SELECT
                d.id::text          AS id,
                d.code,
                d.name,
                d.zone,
                d.pipe_length_km::float  AS pipe_length_km,
                d.connection_count,
                b.siv_m3::float     AS siv_m3,
                b.scv_m3::float     AS scv_m3,
                b.nrw_m3::float     AS nrw_m3,
                b.nrw_pct::float    AS nrw_pct,
                b.flag_level,
                li.confidence_score,
                li.alert_type,
                (COALESCE(li.mnf_flag, false) OR COALESCE(li.zscore_flag, false)) AS has_leak_flag
            FROM dma d
            LEFT JOIN LATERAL (
                SELECT siv_m3, scv_m3, nrw_m3, nrw_pct, flag_level
                FROM balance_period
                WHERE dma_code = d.code
                ORDER BY period_start DESC
                LIMIT 1
            ) b ON true
            LEFT JOIN LATERAL (
                SELECT confidence_score, alert_type, mnf_flag, zscore_flag
                FROM leak_indicator
                WHERE dma_code = d.code
                ORDER BY indicator_date DESC
                LIMIT 1
            ) li ON true
            WHERE d.is_active = true
            ORDER BY d.code
            LIMIT :limit OFFSET :offset
        """),
        {"limit": page_size, "offset": (page - 1) * page_size},
    )

    data = [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "zone": r.zone,
            "pipe_length_km": r.pipe_length_km,
            "connection_count": r.connection_count,
            "siv_m3": r.siv_m3,
            "scv_m3": r.scv_m3,
            "nrw_m3": r.nrw_m3,
            "nrw_pct": r.nrw_pct,
            "flag_level": r.flag_level or "normal",
            "confidence_score": r.confidence_score or 0,
            "alert_type": r.alert_type or "NONE",
            "has_leak_flag": bool(r.has_leak_flag),
        }
        for r in rows
    ]

    return {"data": data, "meta": {"page": page, "page_size": page_size, "total": total}}


@router.get("/{dma_id}/balance", response_model=dict, summary="DMA balance history", description="Last N months of IWA balance periods for a single DMA. Used by the DMA detail page chart.")
async def get_dma_balance_history(
    dma_id: uuid.UUID,
    _user: AnyAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    months: int = Query(12, ge=1, le=60),
) -> dict:
    """Last N months of balance periods for a single DMA (used by detail page)."""
    result = await db.execute(select(DMA).where(DMA.id == dma_id))
    dma = result.scalar_one_or_none()
    if dma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DMA not found")

    rows = await db.execute(
        text("""
            SELECT
                id::text    AS id,
                dma_code,
                period_start,
                period_end,
                siv_m3::float       AS siv_m3,
                scv_m3::float       AS scv_m3,
                nrw_m3::float       AS nrw_m3,
                nrw_pct::float      AS nrw_pct,
                leakage_index::float AS leakage_index,
                flag_level
            FROM balance_period
            WHERE dma_code = :code
              AND period_start >= NOW() - (:months || ' months')::interval
            ORDER BY period_start DESC
            LIMIT :limit
        """),
        {"code": dma.code, "months": months, "limit": months},
    )

    data = [
        {
            "id": r.id,
            "dma_code": r.dma_code,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "siv_m3": r.siv_m3,
            "scv_m3": r.scv_m3,
            "nrw_m3": r.nrw_m3,
            "nrw_pct": r.nrw_pct,
            "leakage_index": r.leakage_index,
            "flag_level": r.flag_level or "normal",
        }
        for r in rows
    ]
    return {"data": data, "dma_code": dma.code, "dma_name": dma.name}


@router.get("", response_model=dict, summary="List DMAs", description="Paginated list of District Metered Areas in the current tenant. Filter by zone or active status.")
async def list_dmas(
    _user: AnyAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    zone: str | None = None,
    active_only: bool = True,
) -> dict:
    q = select(DMA)
    if active_only:
        q = q.where(DMA.is_active.is_(True))
    if zone:
        q = q.where(DMA.zone == zone)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    items_result = await db.execute(
        q.order_by(DMA.code).offset((page - 1) * page_size).limit(page_size)
    )
    items = items_result.scalars().all()

    return {
        "data": [DMAResponse.model_validate(d) for d in items],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.post("", response_model=DMAResponse, status_code=status.HTTP_201_CREATED, summary="Create DMA", description="Create a new District Metered Area. Optionally include a GeoJSON geometry for the map. `utility_admin` only.")
async def create_dma(
    body: DMACreate,
    _admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DMAResponse:
    existing = await db.execute(select(DMA).where(DMA.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"DMA code '{body.code}' already exists in this tenant.",
        )

    create_data = body.model_dump(exclude={"geometry_geojson"})
    dma = DMA(**create_data)
    db.add(dma)
    await db.flush()

    if body.geometry_geojson:
        await _set_geometry(db, dma.id, body.geometry_geojson)

    return DMAResponse.model_validate(dma)


@router.get("/{dma_id}", response_model=DMAResponse, summary="Get DMA by ID", description="Retrieve a single DMA's metadata by UUID.")
async def get_dma(
    dma_id: uuid.UUID,
    _user: AnyAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DMAResponse:
    result = await db.execute(select(DMA).where(DMA.id == dma_id))
    dma = result.scalar_one_or_none()
    if dma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DMA not found")
    return DMAResponse.model_validate(dma)


@router.patch("/{dma_id}", response_model=DMAResponse, summary="Update DMA", description="Partial update of DMA metadata or geometry. `utility_admin` only.")
async def update_dma(
    dma_id: uuid.UUID,
    body: DMAUpdate,
    _admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DMAResponse:
    result = await db.execute(select(DMA).where(DMA.id == dma_id))
    dma = result.scalar_one_or_none()
    if dma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DMA not found")

    for field, value in body.model_dump(exclude_none=True, exclude={"geometry_geojson"}).items():
        setattr(dma, field, value)

    if body.geometry_geojson is not None:
        await _set_geometry(db, dma.id, body.geometry_geojson)

    await db.flush()
    return DMAResponse.model_validate(dma)
