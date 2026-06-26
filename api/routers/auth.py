"""Auth endpoints: login, refresh, logout, password reset."""
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import (
    check_brute_force,
    clear_brute_force,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    record_failed_login,
    verify_password,
)
from database import get_db
from models.user import User
from schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_REFRESH_COOKIE_NAME = "refresh_token"
_RESET_TOKEN_TTL_HOURS = 2


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/api/v1/auth",
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtain access token",
    description=(
        "Authenticate with email and password. Returns a short-lived `access_token` (15 min) "
        "and sets an httpOnly `refresh_token` cookie (7 days). "
        "Brute-force protection locks the account for 15 min after 5 failed attempts."
    ),
)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    await check_brute_force(body.email)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        await record_failed_login(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    await clear_brute_force(body.email)

    # Fetch tenant slug for JWT payload
    from sqlalchemy import text
    row = await db.execute(
        text("SELECT slug FROM public.tenants WHERE id = :tid"),
        {"tid": str(user.tenant_id)},
    )
    tenant_slug = row.scalar_one()

    access_token = create_access_token(str(user.id), tenant_slug, user.role)
    refresh_token = create_refresh_token(str(user.id), tenant_slug)

    # Update last_login_at (no audit log needed — not a write to tenant data)
    user.last_login_at = datetime.now(UTC)

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange the httpOnly refresh_token cookie (or body field) for a new access token and rotated refresh token.",
)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE_NAME)] = None,
    body: RefreshRequest | None = None,
) -> TokenResponse:
    # Accept token from httpOnly cookie (preferred) or request body (for clients that can't use cookies)
    token = refresh_token or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    tenant_slug = payload["tenant_slug"]
    new_access = create_access_token(str(user.id), tenant_slug, user.role)
    new_refresh = create_refresh_token(str(user.id), tenant_slug)

    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Invalidate session", description="Clears the httpOnly refresh_token cookie.")
async def logout(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path="/api/v1/auth")


# ---------------------------------------------------------------------------
# POST /password-reset/request
# ---------------------------------------------------------------------------

@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED, summary="Request password reset", description="Sends a reset link to the email if it exists. Always returns 202 to prevent email enumeration.")
async def request_password_reset(
    body: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always return 202 to prevent email enumeration
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires_at = datetime.now(UTC) + timedelta(
            hours=_RESET_TOKEN_TTL_HOURS
        )
        # TODO: send email via aiosmtplib (Sprint 3 SMTP integration)

    return {"detail": "If that email exists, a reset link has been sent."}


# ---------------------------------------------------------------------------
# POST /password-reset/confirm
# ---------------------------------------------------------------------------

@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK, summary="Confirm password reset", description="Set a new password using the token from the reset email. Token is valid for 2 hours.")
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(
        select(User).where(User.password_reset_token == body.token)
    )
    user = result.scalar_one_or_none()

    if user is None or user.password_reset_expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password too short")

    user.hashed_password = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None

    return {"detail": "Password updated successfully."}
