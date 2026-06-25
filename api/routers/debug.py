from fastapi import APIRouter

from tasks.ping_task import ping_task

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/ping", summary="Smoke-test Celery worker")
async def trigger_ping() -> dict:
    """Dispatches a no-op Celery task and returns the task ID."""
    result = ping_task.delay()
    return {"task_id": result.id, "status": "queued"}
