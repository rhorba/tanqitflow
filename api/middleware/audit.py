"""Audit log middleware — persists write operations to the tenant's audit_log table."""
from jose import JWTError, jwt
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import get_settings
from database import AsyncSessionLocal, current_tenant_slug

settings = get_settings()

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/debug/ping"}


def _extract_user_info(request: Request) -> tuple[str | None, str | None]:
    """Return (user_id, user_email) from the Bearer JWT, or (None, None)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    try:
        payload = jwt.decode(
            auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub"), payload.get("email")
    except JWTError:
        return None, None


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    After any write operation on a tenant-scoped path, persists an audit_log
    row inside the current tenant's PostgreSQL schema.

    Runs best-effort: failures are logged but never propagate to the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if (
            request.method not in _WRITE_METHODS
            or request.url.path in _SKIP_PATHS
        ):
            return response

        tenant = current_tenant_slug.get()
        if not tenant:
            return response  # No tenant context — skip (e.g., public auth endpoints)

        user_id, user_email = _extract_user_info(request)
        if not user_id:
            return response  # Unauthenticated write — auth layer will reject it

        ip = request.client.host if request.client else None

        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(f'SET search_path TO "{tenant}", public')  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
                )
                await session.execute(
                    text("""
                        INSERT INTO audit_log
                            (user_id, user_email, method, path, status_code, ip_address)
                        VALUES
                            (:uid, :email, :method, :path, :status, :ip)
                    """),
                    {
                        "uid": user_id,
                        "email": user_email or "",
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "ip": ip,
                    },
                )
                await session.commit()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Audit log write failed: %s", exc)

        return response
