from celery import Celery

from config import get_settings

settings = get_settings()

celery_app = Celery(
    "tanqitflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.ping_task",
        # Sprint 3+: ingest_task, balance_task, detection_task, worklist_task, report_task
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Casablanca",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    beat_schedule={
        # Sprint 5+: nightly MNF, monthly IF retrain
    },
)
