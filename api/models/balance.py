"""BalancePeriod model — lives in tenant schema."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.dma import TenantBase


class BalancePeriod(TenantBase):
    """
    One row per DMA per calendar month.
    SIV (System Input Volume) - SCV (System Customer Volume) = NRW.
    Computed by the nightly Celery task or triggered after ingestion.
    """
    __tablename__ = "balance_period"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dma_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    dma_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    siv_m3: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    scv_m3: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    nrw_m3: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    nrw_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    leakage_index: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    flag_level: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="normal", index=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
