"""CSV ingestion: upload → MinIO → Celery + status/history endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.security import get_current_user
from core.storage import get_storage_client
from database import current_tenant_slug, get_db
from models.ingestion_job import IngestionJob
from models.user import User
from schemas.ingestion import IngestionJobResponse, JobType

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

settings = get_settings()

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


@router.post("/upload", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    job_type: JobType = Form(...),
) -> IngestionJobResponse:
    tenant_slug = current_tenant_slug.get()
    if not tenant_slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tenant context")

    # Size guard (read into memory — 50 MB max)
    raw = await file.read()
    if len(raw) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 50 MB limit",
        )

    # Store in MinIO under tenant prefix
    job_id = uuid.uuid4()
    ext = "xlsx" if (file.filename or "").endswith(".xlsx") else "csv"
    minio_key = f"{tenant_slug}/ingestion/{job_type}/{job_id}.{ext}"

    try:
        client = get_storage_client(settings)
        client.put_object(
            Bucket=settings.minio_bucket,
            Key=minio_key,
            Body=raw,
            ContentLength=len(raw),
            ContentType=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed: {exc}",
        ) from exc

    # Create job record
    job = IngestionJob(
        id=job_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        job_type=job_type.value,
        original_filename=file.filename or "upload",
        minio_key=minio_key,
        status="queued",
    )
    db.add(job)
    await db.flush()

    # Enqueue Celery task
    from tasks.celery_app import celery_app
    task_name = (
        "tasks.process_dma_inflow"
        if job_type == JobType.dma_inflow
        else "tasks.process_customer_reads"
    )
    result = celery_app.send_task(
        task_name,
        args=[str(job_id), tenant_slug, minio_key],
    )
    job.celery_task_id = result.id

    return IngestionJobResponse.model_validate(job)


@router.get("/jobs", response_model=dict)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_type: JobType | None = None,
) -> dict:
    q = select(IngestionJob).where(IngestionJob.tenant_id == current_user.tenant_id)
    if job_type:
        q = q.where(IngestionJob.job_type == job_type.value)

    from sqlalchemy import func
    total_r = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_r.scalar_one()

    items_r = await db.execute(
        q.order_by(IngestionJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = items_r.scalars().all()

    return {
        "data": [IngestionJobResponse.model_validate(j) for j in items],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IngestionJobResponse:
    result = await db.execute(
        select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.tenant_id == current_user.tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return IngestionJobResponse.model_validate(job)
