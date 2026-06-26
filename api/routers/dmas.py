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


@router.get("/geojson", response_model=None)
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


@router.get("", response_model=dict)
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


@router.post("", response_model=DMAResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/{dma_id}", response_model=DMAResponse)
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


@router.patch("/{dma_id}", response_model=DMAResponse)
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
