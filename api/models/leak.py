"""Leak detection ORM models — live in tenant schema."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.dma import TenantBase


class LeakIndicator(TenantBase):
    """One row per DMA per calendar day — nightly leak detection results."""
    __tablename__ = "leak_indicator"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dma_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    dma_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    indicator_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # MNF signal
    mnf_m3h: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    baseline_m3h: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    mnf_flag: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # Z-score signal
    max_zscore: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    zscore_flag: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # Isolation Forest signal
    if_anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    if_flag: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # Combined output
    confidence_score: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    alert_type: Mapped[str] = mapped_column(
        String(30), server_default="NONE", nullable=False, index=True
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnomalyEvent(TenantBase):
    """Individual anomaly points — TimescaleDB hypertable partitioned by event_time."""
    __tablename__ = "anomaly_event"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dma_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(60), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    zscore: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)


class WorklistItem(TenantBase):
    """Ranked repair worklist — one active row per DMA."""
    __tablename__ = "worklist_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dma_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    dma_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dma_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    estimated_loss_m3_per_month: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    savings_mad_est: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), server_default="NONE", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), server_default="OPEN", nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
