"""Z-score anomaly detector — pure Python, no DB access.

Computes rolling 30-day z-score per time-series metric.
Flags individual readings where |z| > threshold (default 3.0).
Returns the maximum |z| observed in the window (used for confidence score).
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

ZSCORE_ROLLING_DAYS = 30
ZSCORE_DEFAULT_THRESHOLD = 3.0
ZSCORE_MIN_SAMPLES = 10  # need enough data for meaningful std


@dataclass
class MetricPoint:
    timestamp: datetime  # UTC-aware
    metric: str          # e.g. 'flow_rate_lps', 'pressure_bar', 'volume_m3'
    value: float


@dataclass
class AnomalyPoint:
    timestamp: datetime
    metric: str
    value: float
    zscore: float


@dataclass
class ZscoreResult:
    dma_code: str
    anomalies: list[AnomalyPoint]
    max_abs_zscore: float | None
    zscore_flag: bool


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return (values[0] if n == 1 else 0.0), 0.0
    mu = sum(values) / n
    variance = sum((v - mu) ** 2 for v in values) / (n - 1)
    return mu, math.sqrt(variance)


def detect_anomalies(
    dma_code: str,
    points: Sequence[MetricPoint],
    target_window_end: datetime,
    threshold: float = ZSCORE_DEFAULT_THRESHOLD,
) -> ZscoreResult:
    """
    Detect z-score anomalies in a rolling 30-day window ending at target_window_end.
    Returns flagged points and the max |z| observed.
    """
    if target_window_end.tzinfo is None:
        target_window_end = target_window_end.replace(tzinfo=UTC)

    window_start = target_window_end - timedelta(days=ZSCORE_ROLLING_DAYS)

    # Group by metric
    by_metric: dict[str, list[MetricPoint]] = {}
    for p in points:
        ts = p.timestamp if p.timestamp.tzinfo else p.timestamp.replace(tzinfo=UTC)
        if window_start <= ts <= target_window_end:
            by_metric.setdefault(p.metric, []).append(p)

    anomalies: list[AnomalyPoint] = []
    global_max_z: float | None = None

    for metric, metric_points in by_metric.items():
        if len(metric_points) < ZSCORE_MIN_SAMPLES:
            continue

        values = [p.value for p in metric_points]
        mu, sigma = _mean_std(values)
        if sigma == 0:
            continue

        for p, v in zip(metric_points, values):
            z = (v - mu) / sigma
            abs_z = abs(z)
            if global_max_z is None or abs_z > global_max_z:
                global_max_z = abs_z
            if abs_z > threshold:
                anomalies.append(AnomalyPoint(
                    timestamp=p.timestamp,
                    metric=metric,
                    value=v,
                    zscore=z,
                ))

    flag = global_max_z is not None and global_max_z > threshold

    return ZscoreResult(
        dma_code=dma_code,
        anomalies=anomalies,
        max_abs_zscore=global_max_z,
        zscore_flag=flag,
    )
