from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import get_settings
from database import current_tenant_slug

settings = get_settings()

# Paths that skip tenant resolution (no JWT required)
_PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/password-reset/request",
    "/api/v1/auth/password-reset/confirm",
    "/debug/ping",
}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Decodes the Bearer JWT and sets the tenant_slug ContextVar so that
    database.get_db() routes queries to the correct PostgreSQL schema.

    Public paths (auth, health, docs) bypass tenant resolution.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        token = _extract_bearer(request)
        if token:
            try:
                payload = jwt.decode(
                    token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
                )
                slug = payload.get("tenant_slug")
                if slug:
                    token_ctx = current_tenant_slug.set(slug)
                    try:
                        return await call_next(request)
                    finally:
                        current_tenant_slug.reset(token_ctx)
            except JWTError:
                pass  # Let the route's own auth dependency return 401

        return await call_next(request)


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
