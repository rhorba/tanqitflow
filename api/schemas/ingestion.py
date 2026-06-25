import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobType(StrEnum):
    dma_inflow = "dma_inflow"
    customer_reads = "customer_reads"
    pressure_flow = "pressure_flow"


class JobStatus(StrEnum):
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"


class IngestionJobResponse(BaseModel):
    id: uuid.UUID
    job_type: JobType
    original_filename: str
    status: JobStatus
    row_count: int | None
    error_detail: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
