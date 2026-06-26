"""IWA water balance edge cases — Story 9.1.

Tests the IWA-compliant NRW computation from services/balance.py,
focusing on edge cases not covered in test_balance_service.py:
negative NRW (SCV > SIV), component identity (SIV = SCV + NRW),
zero pipe_length, and high apparent loss scenarios.
"""
import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
os.environ.setdefault("MINIO_ACCESS_KEY", "t")
os.environ.setdefault("MINIO_SECRET_KEY", "t")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")

from services.balance import _flag_level, compute_balance


def _make_db(siv: float, scv: float, pipe_km: float | None = None):
    db = AsyncMock()
    siv_mock = MagicMock()
    siv_mock.scalar.return_value = siv
    scv_mock = MagicMock()
    scv_mock.scalar.return_value = scv
    dma_row = MagicMock()
    dma_row.id = "test-uuid"
    dma_row.pipe_length_km = pipe_km
    dma_mock = MagicMock()
    dma_mock.first.return_value = dma_row
    upsert_mock = MagicMock()
    db.execute = AsyncMock(side_effect=[siv_mock, scv_mock, dma_mock, upsert_mock])
    return db


PERIOD_START = datetime(2026, 5, 1, tzinfo=UTC)
PERIOD_END = datetime(2026, 5, 31, tzinfo=UTC)


class TestIwaBalanceComponents:
    """IWA identity: SIV = SCV + NRW."""

    async def test_components_sum_correctly(self):
        db = _make_db(siv=12500.0, scv=9000.0)
        result = await compute_balance(db, "DMA-IWA-01", PERIOD_START, PERIOD_END)
        assert result["nrw_m3"] == pytest.approx(result["siv_m3"] - result["scv_m3"])

    async def test_negative_nrw_when_scv_exceeds_siv(self):
        """Meter over-registration or billing error can yield SCV > SIV (negative apparent NRW)."""
        db = _make_db(siv=8000.0, scv=9000.0)
        result = await compute_balance(db, "DMA-IWA-02", PERIOD_START, PERIOD_END)
        assert result["nrw_m3"] < 0
        assert result["nrw_pct"] <= 0
        # Flag must still be valid string
        assert result["flag_level"] in ("normal", "warning", "critical")

    async def test_negative_nrw_is_flagged_normal(self):
        db = _make_db(siv=8000.0, scv=9000.0)
        result = await compute_balance(db, "DMA-IWA-03", PERIOD_START, PERIOD_END)
        assert result["flag_level"] == "normal"

    async def test_high_apparent_loss_critical_flag(self):
        """When SCV is very low relative to SIV, flag should be critical (>40%)."""
        db = _make_db(siv=100_000.0, scv=50_000.0)  # 50% NRW
        result = await compute_balance(db, "DMA-IWA-04", PERIOD_START, PERIOD_END)
        assert result["flag_level"] == "critical"
        assert result["nrw_pct"] == pytest.approx(50.0, rel=1e-3)

    async def test_zero_pipe_length_no_leakage_index(self):
        """pipe_length_km = None → leakage_index should be None (not crash)."""
        db = _make_db(siv=10000.0, scv=8000.0, pipe_km=None)
        result = await compute_balance(db, "DMA-IWA-05", PERIOD_START, PERIOD_END)
        assert result["leakage_index"] is None

    async def test_perfect_balance_zero_nrw(self):
        """All water accounted for — NRW = 0, flag normal."""
        db = _make_db(siv=10000.0, scv=10000.0)
        result = await compute_balance(db, "DMA-IWA-06", PERIOD_START, PERIOD_END)
        assert result["nrw_m3"] == pytest.approx(0.0)
        assert result["nrw_pct"] == pytest.approx(0.0)
        assert result["flag_level"] == "normal"

    async def test_exactly_at_warning_threshold(self):
        db = _make_db(siv=10000.0, scv=7500.0)  # 25% NRW exactly
        result = await compute_balance(db, "DMA-IWA-07", PERIOD_START, PERIOD_END)
        assert result["nrw_pct"] == pytest.approx(25.0, rel=1e-3)
        assert result["flag_level"] == "warning"

    async def test_exactly_at_critical_threshold(self):
        db = _make_db(siv=10000.0, scv=6000.0)  # 40% NRW exactly
        result = await compute_balance(db, "DMA-IWA-08", PERIOD_START, PERIOD_END)
        assert result["nrw_pct"] == pytest.approx(40.0, rel=1e-3)
        assert result["flag_level"] == "critical"


class TestFlagLevelBoundaries:
    def test_zero_nrw_pct_is_normal(self):
        assert _flag_level(Decimal("0")) == "normal"

    def test_just_below_warning(self):
        assert _flag_level(Decimal("24.9999")) == "normal"

    def test_just_above_warning(self):
        assert _flag_level(Decimal("25.0001")) == "warning"

    def test_just_below_critical(self):
        assert _flag_level(Decimal("39.9999")) == "warning"

    def test_just_above_critical(self):
        assert _flag_level(Decimal("40.0001")) == "critical"

    def test_extreme_nrw_stays_critical(self):
        assert _flag_level(Decimal("99.9")) == "critical"
