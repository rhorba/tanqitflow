"""Unit tests for services/balance.py — pure logic, no DB."""
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

from services.balance import _flag_level, compute_balance, get_summary, get_trend


class TestFlagLevel:
    def test_below_warning_is_normal(self):
        assert _flag_level(Decimal("20.0")) == "normal"

    def test_at_warning_threshold(self):
        assert _flag_level(Decimal("25.0")) == "warning"

    def test_between_thresholds_is_warning(self):
        assert _flag_level(Decimal("32.5")) == "warning"

    def test_at_critical_threshold(self):
        assert _flag_level(Decimal("40.0")) == "critical"

    def test_above_critical_is_critical(self):
        assert _flag_level(Decimal("55.0")) == "critical"


class TestComputeBalance:
    def _make_db(self, siv: float, scv: float, pipe_km: float | None = None):
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

    async def test_normal_nrw_below_threshold(self):
        db = self._make_db(siv=10000.0, scv=8500.0)
        period_start = datetime(2026, 5, 1, tzinfo=UTC)
        period_end = datetime(2026, 5, 31, tzinfo=UTC)

        result = await compute_balance(db, "DMA001", period_start, period_end)

        assert result["siv_m3"] == 10000.0
        assert result["scv_m3"] == 8500.0
        assert result["nrw_m3"] == 1500.0
        assert result["nrw_pct"] == pytest.approx(15.0, rel=1e-3)
        assert result["flag_level"] == "normal"

    async def test_warning_flag_when_nrw_exceeds_25pct(self):
        db = self._make_db(siv=10000.0, scv=7000.0)  # 30% NRW
        period_start = datetime(2026, 5, 1, tzinfo=UTC)
        period_end = datetime(2026, 5, 31, tzinfo=UTC)

        result = await compute_balance(db, "DMA002", period_start, period_end)
        assert result["flag_level"] == "warning"

    async def test_critical_flag_when_nrw_exceeds_40pct(self):
        db = self._make_db(siv=10000.0, scv=5000.0)  # 50% NRW
        period_start = datetime(2026, 5, 1, tzinfo=UTC)
        period_end = datetime(2026, 5, 31, tzinfo=UTC)

        result = await compute_balance(db, "DMA003", period_start, period_end)
        assert result["flag_level"] == "critical"

    async def test_zero_siv_yields_zero_nrw_pct(self):
        db = self._make_db(siv=0.0, scv=0.0)
        period_start = datetime(2026, 5, 1, tzinfo=UTC)
        period_end = datetime(2026, 5, 31, tzinfo=UTC)

        result = await compute_balance(db, "DMA004", period_start, period_end)
        assert result["nrw_pct"] == 0.0
        assert result["flag_level"] == "normal"

    async def test_leakage_index_computed_when_pipe_length_known(self):
        db = self._make_db(siv=10000.0, scv=8000.0, pipe_km=25.0)
        period_start = datetime(2026, 5, 1, tzinfo=UTC)
        period_end = datetime(2026, 5, 31, tzinfo=UTC)

        result = await compute_balance(db, "DMA005", period_start, period_end)
        # NRW = 2000, pipe_km = 25 → leakage_index = 80
        assert result["leakage_index"] == pytest.approx(80.0, rel=1e-3)


class TestGetSummary:
    async def test_returns_summary_dict(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock(
            total_siv=50000.0,
            total_scv=38000.0,
            total_nrw=12000.0,
            nrw_pct=24.0,
            flagged_dmas=3,
        )
        db.execute = AsyncMock(return_value=mock_result)

        summary = await get_summary(db)
        assert summary["siv_m3"] == 50000.0
        assert summary["nrw_m3"] == 12000.0
        assert summary["flagged_dmas"] == 3


class TestGetTrend:
    async def test_returns_list_of_monthly_points(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([
            MagicMock(month="2026-06", siv_m3=5000.0, nrw_m3=1200.0, nrw_pct=24.0),
            MagicMock(month="2026-05", siv_m3=4800.0, nrw_m3=1100.0, nrw_pct=22.9),
        ]))
        db.execute = AsyncMock(return_value=mock_result)

        trend = await get_trend(db, months=2)
        assert len(trend) == 2
        assert trend[0]["month"] == "2026-06"
        assert trend[0]["nrw_pct"] == 24.0
