"""Pydantic schemas for the balance API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BalancePeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    dma_code: str
    period_start: datetime
    period_end: datetime
    siv_m3: float
    scv_m3: float
    nrw_m3: float
    nrw_pct: float
    leakage_index: float | None = None
    flag_level: str
    computed_at: datetime | None = None


class BalanceSummaryOut(BaseModel):
    siv_m3: float
    scv_m3: float
    nrw_m3: float
    nrw_pct: float
    flagged_dmas: int


class BalanceTrendPoint(BaseModel):
    month: str
    siv_m3: float
    nrw_m3: float
    nrw_pct: float


class ComputeRequest(BaseModel):
    dma_code: str
    year: int
    month: int
