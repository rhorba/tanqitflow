import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DMACreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    zone: str | None = None
    pipe_length_km: float | None = None
    connection_count: int | None = None
    geometry_wkt: str | None = None


class DMAUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    zone: str | None = None
    pipe_length_km: float | None = None
    connection_count: int | None = None
    geometry_wkt: str | None = None
    is_active: bool | None = None


class DMAResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    zone: str | None
    pipe_length_km: float | None
    connection_count: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
