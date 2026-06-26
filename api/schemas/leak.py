"""Pydantic schemas for leak detection + worklist endpoints."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# LeakIndicator
# ---------------------------------------------------------------------------

class LeakIndicatorOut(BaseModel):
    id: uuid.UUID
    dma_code: str
    indicator_date: date
    mnf_m3h: float | None
    baseline_m3h: float | None
    mnf_flag: bool
    max_zscore: float | None
    zscore_flag: bool
    if_anomaly_score: float | None
    if_flag: bool
    confidence_score: int
    alert_type: str
    computed_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# AnomalyEvent
# ---------------------------------------------------------------------------

class AnomalyEventOut(BaseModel):
    id: uuid.UUID
    dma_code: str
    event_time: datetime
    metric: str
    value: float
    zscore: float

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# WorklistItem
# ---------------------------------------------------------------------------

AlertType = Literal["NONE", "MNF", "ZSCORE", "ISOLATION_FOREST", "COMBINED"]
WorklistStatus = Literal["OPEN", "IN_PROGRESS", "RESOLVED", "DEFERRED"]


class WorklistItemOut(BaseModel):
    id: uuid.UUID
    dma_code: str
    dma_name: str | None
    rank: int
    estimated_loss_m3_per_month: float | None
    savings_mad_est: float | None
    confidence_score: int
    alert_type: str
    status: str
    generated_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorklistGenerateRequest(BaseModel):
    water_cost_mad_per_m3: float = Field(default=16.0, ge=0.1, le=100.0)


class WorklistStatusPatch(BaseModel):
    status: WorklistStatus
