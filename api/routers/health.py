import redis.asyncio as aioredis
from fastapi import APIRouter

from config import get_settings
from core.storage import get_storage_client
from database import check_db_connection

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", summary="Service health check")
async def health_check() -> dict:
    result = {"status": "ok", "db": "ok", "redis": "ok", "minio": "ok"}

    if not await check_db_connection():
        result["db"] = "error"
        result["status"] = "degraded"

    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
    except Exception:
        result["redis"] = "error"
        result["status"] = "degraded"

    try:
        client = get_storage_client(settings)
        client.list_buckets()
    except Exception:
        result["minio"] = "error"
        result["status"] = "degraded"

    return result
