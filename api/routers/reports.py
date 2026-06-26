"""PDF report generation — any authenticated user can request."""
from __future__ import annotations

import uuid
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from config import get_settings
from core.security import get_current_user
from core.storage import get_storage_client
from models.user import User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

AnyAuth = Annotated[User, Depends(get_current_user)]


class ReportRequest(BaseModel):
    from_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    lang: str = Field(default="fr", pattern="^(fr|ar)$")


@router.post("/water-balance", status_code=status.HTTP_202_ACCEPTED)
async def request_water_balance_report(
    body: ReportRequest,
    current_user: AnyAuth,
) -> dict:
    """Dispatch PDF generation task, return task_id for polling."""
    from tasks.celery_app import celery_app
    from tasks.report_task import generate_pdf_report  # noqa: F401 — registers task

    report_id = str(uuid.uuid4())

    # Derive tenant_slug from JWT (stored in current_user's tenant relationship).
    # We query the tenant slug via the tenant_id → tenants table lookup at call time.
    from database import current_tenant_slug
    tenant_slug = current_tenant_slug.get() or "default"

    task = celery_app.send_task(
        "tasks.report_task.generate_pdf_report",
        args=[tenant_slug, body.from_date, body.to_date, body.lang, report_id],
    )
    return {"task_id": task.id, "report_id": report_id}


@router.get("/download/{task_id}")
async def download_report(
    task_id: str,
    current_user: AnyAuth,
    expires: int = Query(default=3600, ge=60, le=86400),
) -> dict:
    """Poll task state; when SUCCESS return a presigned MinIO URL."""
    result = AsyncResult(task_id)

    if result.state == "PENDING":
        return {"status": "pending"}
    if result.state == "STARTED":
        return {"status": "processing"}
    if result.state == "FAILURE":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report generation failed.",
        )
    if result.state != "SUCCESS":
        return {"status": result.state.lower()}

    task_result: dict = result.get()
    minio_key: str = task_result["minio_key"]

    settings = get_settings()
    s3 = get_storage_client(settings)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": minio_key},
        ExpiresIn=expires,
    )
    return {"status": "ready", "url": url, "size_bytes": task_result.get("size_bytes")}
