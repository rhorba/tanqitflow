from celery import Celery
from celery.schedules import crontab

from config import get_settings

settings = get_settings()


def _crontab(**kwargs) -> crontab:
    return crontab(**kwargs)

celery_app = Celery(
    "tanqitflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.ping_task",
        "tasks.ingest_task",
        "tasks.balance_task",
        "tasks.leak_detection_task",
        "tasks.report_task",
        "tasks.retention_task",
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
        # Nightly leak detection: 05:00 Africa/Casablanca (all active tenants handled by task)
        "nightly-leak-detection": {
            "task": "tasks.nightly_leak_detection",
            "schedule": _crontab(hour=5, minute=0),
            "args": ("default",),  # tenant_slug; override per deployment
        },
        # Monthly IF retrain: 1st of each month at 03:00 Casablanca
        "monthly-if-retrain": {
            "task": "tasks.monthly_if_retrain",
            "schedule": _crontab(hour=3, minute=0, day_of_month=1),
            "args": ("default",),
        },
        # Monthly PII retention (Law 09-08): 1st of month at 02:00 Casablanca
        "monthly-pii-retention": {
            "task": "tasks.retention_task.monthly_pii_retention",
            "schedule": _crontab(hour=2, minute=0, day_of_month=1),
        },
    },
)
