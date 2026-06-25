"""DMA CRUD — analyst+ can read, utility_admin can write."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user, require_role
from database import get_db
from models.dma import DMA
from models.user import User, UserRole
from schemas.dma import DMACreate, DMAResponse, DMAUpdate

router = APIRouter(prefix="/api/v1/dmas", tags=["dmas"])

AnyAuth = Annotated[User, Depends(get_current_user)]
AdminOnly = Annotated[User, Depends(require_role(UserRole.utility_admin))]


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
    dma = DMA(**body.model_dump())
    db.add(dma)
    await db.flush()
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

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(dma, field, value)

    await db.flush()
    return DMAResponse.model_validate(dma)
