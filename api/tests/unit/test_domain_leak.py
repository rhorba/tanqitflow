"""Unit tests for Sprint 5 domain modules (no DB, no Celery)."""
from datetime import UTC, date, datetime, timedelta

import pytest

from domain.confidence_score import ConfidenceResult, SignalInputs, compute_confidence
from domain.mnf_calculator import FlowReading, MnfResult, compute_mnf
from domain.worklist_ranker import DmaLeakSignal, rank_dmas
from domain.zscore_detector import MetricPoint, ZscoreResult, detect_anomalies

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _casablanca_midnight_utc(d: date) -> datetime:
    """Africa/Casablanca is UTC+1 (winter) / UTC+0 (summer).
    Use UTC+1 so that 02:00 local = 01:00 UTC for simplicity in tests."""
    return datetime(d.year, d.month, d.day, 1, tzinfo=UTC)  # 02:00 Casablanca (UTC+1)


# ---------------------------------------------------------------------------
# MNF Calculator
# ---------------------------------------------------------------------------

class TestMnfCalculator:

    def _steady_readings(self, target: date, n_nights: int = 15, flow: float = 5.0) -> list[FlowReading]:
        """Generate n_nights of historical night-window readings (excludes target_date itself).
        01:30 UTC = 02:30 Africa/Casablanca (UTC+1) — inside the 02:00–04:00 window.
        """
        readings = []
        for i in range(1, n_nights + 1):  # start at 1 — exclude target_date
            d = target - timedelta(days=i)
            ts = datetime(d.year, d.month, d.day, 1, 30, tzinfo=UTC)
            readings.append(FlowReading(timestamp=ts, flow_m3h=flow))
        return readings

    def test_steady_flow_no_flag(self):
        target = date(2026, 6, 1)
        readings = self._steady_readings(target, n_nights=15, flow=5.0)
        # Add a steady target-date reading
        readings.append(FlowReading(timestamp=datetime(2026, 6, 1, 1, 30, tzinfo=UTC), flow_m3h=5.0))
        result = compute_mnf("DMA-01", target, readings)
        assert isinstance(result, MnfResult)
        assert result.mnf_m3h == pytest.approx(5.0)
        assert result.baseline_m3h == pytest.approx(5.0)
        assert result.mnf_flag is False

    def test_sudden_spike_flags(self):
        target = date(2026, 6, 15)
        # History is steady at 5.0; only the spike exists on target date
        readings = self._steady_readings(target, n_nights=15, flow=5.0)
        readings.append(FlowReading(
            timestamp=datetime(2026, 6, 15, 1, 30, tzinfo=UTC),
            flow_m3h=12.0,  # 12 > 5.0 × 1.5 = 7.5
        ))
        result = compute_mnf("DMA-01", target, readings, threshold=1.5)
        assert result.mnf_flag is True
        assert result.mnf_m3h == pytest.approx(12.0)

    def test_insufficient_history_no_flag(self):
        target = date(2026, 6, 1)
        # Only 5 nights — below the 7-night minimum (target date has no reading → mnf=None)
        readings = self._steady_readings(target, n_nights=5, flow=20.0)
        result = compute_mnf("DMA-02", target, readings)
        assert result.baseline_m3h is None
        assert result.mnf_flag is False

    def test_no_readings_in_window(self):
        target = date(2026, 6, 1)
        result = compute_mnf("DMA-03", target, [])
        assert result.mnf_m3h is None
        assert result.mnf_flag is False


# ---------------------------------------------------------------------------
# Z-score Detector
# ---------------------------------------------------------------------------

class TestZscoreDetector:

    def _stationary_series(self, n: int = 50, value: float = 10.0, metric: str = "flow_rate_lps") -> list[MetricPoint]:
        base = datetime(2026, 5, 1, tzinfo=UTC)
        return [
            MetricPoint(timestamp=base + timedelta(hours=i), metric=metric, value=value)
            for i in range(n)
        ]

    def test_stationary_no_anomalies(self):
        points = self._stationary_series(n=50, value=10.0)
        window_end = datetime(2026, 6, 1, tzinfo=UTC)
        result = detect_anomalies("DMA-01", points, window_end)
        assert isinstance(result, ZscoreResult)
        assert result.zscore_flag is False
        assert len(result.anomalies) == 0

    def test_injected_spike_detected(self):
        points = self._stationary_series(n=50, value=10.0)
        # Inject a massive spike
        points.append(MetricPoint(
            timestamp=datetime(2026, 5, 25, 12, tzinfo=UTC),
            metric="flow_rate_lps",
            value=1000.0,
        ))
        window_end = datetime(2026, 6, 1, tzinfo=UTC)
        result = detect_anomalies("DMA-01", points, window_end)
        assert result.zscore_flag is True
        assert len(result.anomalies) >= 1
        assert result.max_abs_zscore is not None and result.max_abs_zscore > 3.0

    def test_sparse_data_no_crash(self):
        # Fewer than ZSCORE_MIN_SAMPLES points — should return no anomalies gracefully
        points = self._stationary_series(n=5, value=10.0)
        window_end = datetime(2026, 6, 1, tzinfo=UTC)
        result = detect_anomalies("DMA-02", points, window_end)
        assert result.zscore_flag is False
        assert result.max_abs_zscore is None


# ---------------------------------------------------------------------------
# Confidence Score
# ---------------------------------------------------------------------------

class TestConfidenceScore:

    def test_no_signals_score_zero(self):
        inputs = SignalInputs(
            mnf_flag=False, mnf_m3h=5.0, baseline_m3h=5.0,
            zscore_flag=False, max_abs_zscore=1.0,
            if_enabled=True, if_score=0.1, if_flag=False,
        )
        result = compute_confidence(inputs)
        assert result.confidence_score == 0
        assert result.alert_type == "NONE"

    def test_only_mnf_fires(self):
        inputs = SignalInputs(
            mnf_flag=True, mnf_m3h=10.0, baseline_m3h=5.0,  # ratio=2x
            zscore_flag=False, max_abs_zscore=1.0,
            if_enabled=False, if_score=None, if_flag=False,
        )
        result = compute_confidence(inputs)
        assert result.confidence_score > 0
        assert result.alert_type == "MNF"

    def test_all_signals_combined(self):
        inputs = SignalInputs(
            mnf_flag=True, mnf_m3h=15.0, baseline_m3h=5.0,  # 3x ratio → high
            zscore_flag=True, max_abs_zscore=5.0,
            if_enabled=True, if_score=0.85, if_flag=True,
        )
        result = compute_confidence(inputs)
        assert result.confidence_score > 50
        assert result.alert_type == "COMBINED"

    def test_if_disabled_weights_redistributed(self):
        inputs = SignalInputs(
            mnf_flag=True, mnf_m3h=10.0, baseline_m3h=5.0,
            zscore_flag=False, max_abs_zscore=None,
            if_enabled=False, if_score=None, if_flag=False,
        )
        result = compute_confidence(inputs)
        # Should still compute (no crash) and return MNF-only alert
        assert isinstance(result, ConfidenceResult)
        assert result.alert_type == "MNF"

    def test_score_clamped_0_100(self):
        inputs = SignalInputs(
            mnf_flag=True, mnf_m3h=1000.0, baseline_m3h=1.0,
            zscore_flag=True, max_abs_zscore=100.0,
            if_enabled=True, if_score=1.0, if_flag=True,
        )
        result = compute_confidence(inputs)
        assert 0 <= result.confidence_score <= 100


# ---------------------------------------------------------------------------
# Worklist Ranker
# ---------------------------------------------------------------------------

class TestWorklistRanker:

    def _signal(self, code: str, nrw: float, confidence: int, alert: str = "MNF") -> DmaLeakSignal:
        return DmaLeakSignal(
            dma_code=code, dma_name=f"DMA {code}", dma_id=None,
            nrw_m3_per_month=nrw, confidence_score=confidence, alert_type=alert,
        )

    def test_ranked_by_roi(self):
        signals = [
            self._signal("A", nrw=1000.0, confidence=90),
            self._signal("B", nrw=500.0, confidence=80),
            self._signal("C", nrw=2000.0, confidence=50),
        ]
        ranked = rank_dmas(signals, water_cost_mad_per_m3=16.0)
        # A: 1000×16×0.9=14400; C: 2000×16×0.5=16000; B: 500×16×0.8=6400
        assert ranked[0].dma_code == "C"
        assert ranked[1].dma_code == "A"
        assert ranked[2].dma_code == "B"
        assert ranked[0].rank == 1

    def test_low_confidence_excluded(self):
        signals = [
            self._signal("A", nrw=5000.0, confidence=5),   # below threshold
            self._signal("B", nrw=100.0, confidence=50),
        ]
        ranked = rank_dmas(signals)
        assert len(ranked) == 1
        assert ranked[0].dma_code == "B"

    def test_empty_signals(self):
        assert rank_dmas([]) == []

    def test_savings_calculation(self):
        signals = [self._signal("X", nrw=1000.0, confidence=100)]
        ranked = rank_dmas(signals, water_cost_mad_per_m3=16.0)
        assert ranked[0].savings_mad_est == pytest.approx(16000.0)
