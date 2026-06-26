from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from core.storage import create_bucket_if_missing
from middleware.audit import AuditLogMiddleware
from middleware.tenant import TenantContextMiddleware
from routers import auth, balance, debug, dmas, health, ingestion, leak, reports, tenants, users, worklist

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure MinIO bucket exists
    try:
        create_bucket_if_missing(settings)
    except Exception as exc:
        print(f"[WARN] MinIO bucket init failed (will retry on next request): {exc}")
    yield
    # Shutdown: nothing to clean up for now


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Non-Revenue Water Intelligence Platform for Moroccan water utilities.",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS — tighten origins in production via env var
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
