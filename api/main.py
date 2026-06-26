from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import get_settings
from core.security import decode_token
from core.storage import create_bucket_if_missing
from middleware.audit import AuditLogMiddleware
from middleware.tenant import TenantContextMiddleware
from routers import (
    auth,
    balance,
    debug,
    dmas,
    health,
    ingestion,
    leak,
    reports,
    tenants,
    users,
    worklist,
)

settings = get_settings()

_OPENAPI_TAGS = [
    {"name": "health", "description": "Service health and dependency status checks."},
    {
        "name": "auth",
        "description": (
            "JWT authentication: login, token refresh, logout, and password reset. "
            "Login returns an `access_token` (Bearer) and sets an httpOnly `refresh_token` cookie."
        ),
    },
    {
        "name": "tenants",
        "description": "Tenant provisioning and management. `utility_admin` only.",
    },
    {
        "name": "users",
        "description": "User management within the current tenant. Role-based access.",
    },
    {
        "name": "dmas",
        "description": "District Metered Area (DMA) CRUD, GeoJSON export, and balance history.",
    },
    {
        "name": "ingestion",
        "description": "CSV file ingestion: upload DMA inflow or customer reads files for async processing.",
    },
    {
        "name": "balance",
        "description": "IWA water balance computation: NRW %, leakage index, KPI summary, 12-month trend.",
    },
    {
        "name": "leak-detection",
        "description": "Leak detection signals: MNF indicators, Z-score anomaly events, Isolation Forest flags.",
    },
    {
        "name": "worklist",
        "description": "ROI-ranked repair worklist: generate, list, update status, export to CSV.",
    },
    {
        "name": "reports",
        "description": "Bilingual PDF report generation (FR/AR) per DMA.",
    },
]

_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


class DocsAuthMiddleware(BaseHTTPMiddleware):
    """In production, gate /docs, /redoc, /openapi.json to utility_admin JWT."""

    async def dispatch(self, request: Request, call_next):
        if settings.is_production and request.url.path in _DOCS_PATHS:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            try:
                token = auth_header.split(" ", 1)[1]
                payload = decode_token(token)
                if payload.get("role") != "utility_admin":
                    return JSONResponse({"detail": "Forbidden — utility_admin only"}, status_code=403)
            except Exception:
                return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_bucket_if_missing(settings)
    except Exception as exc:
        print(f"[WARN] MinIO bucket init failed (will retry on next request): {exc}")
    yield


app = FastAPI(
    title="TanqitFlow API v1.0",
    version="1.0.0",
    description=(
        "Non-Revenue Water Intelligence Platform for Moroccan water utilities. "
        "Built for ONEE regional branches.\n\n"
        "**Authentication**: All endpoints (except `/health`) require a Bearer JWT obtained from `/api/v1/auth/login`.\n\n"
        "```\ncurl -X POST /api/v1/auth/login \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"email\": \"admin@tenant.ma\", \"password\": \"yourpassword\"}'\n```\n\n"
        "The response contains `access_token`. Pass it as `Authorization: Bearer <token>` on all subsequent requests."
    ),
    openapi_tags=_OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(DocsAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(TenantContextMiddleware)

app.include_router(health.router)
app.include_router(debug.router)
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(dmas.router)
app.include_router(ingestion.router)
app.include_router(balance.router)
app.include_router(leak.router)
app.include_router(worklist.router)
app.include_router(reports.router)
