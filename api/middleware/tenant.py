from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from database import current_tenant_slug

_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/debug/ping"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Extracts the tenant slug from the JWT and sets it in the ContextVar so that
    database.get_db() can route queries to the correct PostgreSQL schema.

    Sprint 1: skeleton — tenant routing is wired up fully in Sprint 2 when JWT
    auth is implemented. For now, passes all requests through.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Sprint 2 will decode the JWT here and set:
        #   token = current_tenant_slug.set(tenant_slug)
        # For Sprint 1, leave the ContextVar as None (queries use public schema)
        response = await call_next(request)
        return response
