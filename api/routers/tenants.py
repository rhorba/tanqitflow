"""Tenant provisioning — utility_admin only."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import require_role
from database import get_db
from models.user import User, UserRole
from schemas.tenant import TenantCreate, TenantResponse
from services.tenant import provision_tenant

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.utility_admin))]


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    _admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantResponse:
    # Check slug uniqueness
    existing = await db.execute(
        text("SELECT id FROM public.tenants WHERE slug = :slug"),
        {"slug": body.slug},
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant slug '{body.slug}' already exists.",
        )

    # Insert into public.tenants
    result = await db.execute(
        text("""
            INSERT INTO public.tenants
                (slug, name, region, cost_conventional_mad, cost_desalinated_mad)
            VALUES
                (:slug, :name, :region, :conv, :desal)
            RETURNING id, slug, name, region, cost_conventional_mad,
                      cost_desalinated_mad, is_active, created_at
        """),
        {
            "slug": body.slug,
            "name": body.name,
            "region": body.region,
            "conv": body.cost_conventional_mad,
            "desal": body.cost_desalinated_mad,
        },
    )
    row = result.mappings().one()

    # Provision schema + MinIO prefix
    await provision_tenant(body.slug, db)

    return TenantResponse(**dict(row))


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    _admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TenantResponse]:
    result = await db.execute(
        text("""
            SELECT id, slug, name, region, cost_conventional_mad,
                   cost_desalinated_mad, is_active, created_at
            FROM public.tenants
            ORDER BY created_at DESC
        """)
    )
    return [TenantResponse(**dict(r)) for r in result.mappings()]
