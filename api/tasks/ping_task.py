from tasks.celery_app import celery_app


@celery_app.task(name="tasks.ping", bind=True)
def ping_task(self) -> dict:
    """Smoke-test task: confirms the worker is alive and connected."""
    return {"pong": True, "task_id": self.request.id}
