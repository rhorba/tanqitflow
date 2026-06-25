import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=2, max_length=200)
    region: str | None = None
    cost_conventional_mad: float = 4.0
    cost_desalinated_mad: float = 16.0


class TenantResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    region: str | None
    cost_conventional_mad: float
    cost_desalinated_mad: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
