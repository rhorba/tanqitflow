"""User management within the current tenant — utility_admin only."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.pii import encrypt_pii
from core.security import get_current_user, hash_password, require_role
from database import get_db
from models.user import User, UserRole
from schemas.user import MeUpdate, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.utility_admin))]
AnyAuth = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: AnyAuth) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: MeUpdate,
    current_user: AnyAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    pii_key = get_settings().pii_encryption_key
    if body.language_pref is not None:
        current_user.language_pref = body.language_pref
    if body.full_name is not None:
        current_user.full_name_enc = encrypt_pii(body.full_name, pii_key)
    await db.flush()
    return current_user


@router.delete("/{user_id}/pii", status_code=status.HTTP_204_NO_CONTENT)
async def erase_user_pii(
    user_id: uuid.UUID,
    admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Law 09-08 erasure: set all PII fields to NULL for the given user."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.full_name_enc = None
    await db.flush()


@router.get("", response_model=list[UserResponse])
async def list_users(
    admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserResponse]:
    result = await db.execute(
        select(User).where(User.tenant_id == admin.tenant_id).order_by(User.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    # Role constraint: utility_admin can create any role, analyst/field_viewer can't create
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role.value,
        tenant_id=admin.tenant_id,
    )
    db.add(user)
    await db.flush()
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.role is not None:
        user.role = body.role.value
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-deletion
    await get_current_user.__wrapped__ if hasattr(get_current_user, "__wrapped__") else None
    await db.delete(user)
