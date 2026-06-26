"""Minimum Night Flow (MNF) calculator — pure Python, no DB access.

MNF = minimum flow recorded between 02:00–04:00 Africa/Casablanca local time.
Baseline = rolling median of the last 30 nights (requires ≥ 7 nights).
Flag: mnf > baseline × MNF_THRESHOLD_FACTOR (default 1.5, configurable).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from statistics import median

import pytz

_CASABLANCA_TZ = pytz.timezone("Africa/Casablanca")
MNF_WINDOW_START_HOUR = 2  # 02:00 local
MNF_WINDOW_END_HOUR = 4    # exclusive — 04:00 local
MNF_MIN_NIGHTS = 7
MNF_ROLLING_DAYS = 30
MNF_DEFAULT_THRESHOLD = 1.5


@dataclass
class MnfResult:
    dma_code: str
    indicator_date: date
    mnf_m3h: float | None
    baseline_m3h: float | None
    mnf_flag: bool


@dataclass
class FlowReading:
    """A single hourly (or sub-hourly) flow measurement."""
    timestamp: datetime  # UTC-aware
    flow_m3h: float


def _to_casablanca(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(_CASABLANCA_TZ)


def _night_min(readings: Sequence[FlowReading], target_date: date) -> float | None:
    """Return minimum flow in the 02:00–04:00 window for target_date (local Casablanca)."""
    window = [
        r.flow_m3h for r in readings
        if (local := _to_casablanca(r.timestamp))
        and local.date() == target_date
        and MNF_WINDOW_START_HOUR <= local.hour < MNF_WINDOW_END_HOUR
    ]
    return min(window) if window else None


def compute_mnf(
    dma_code: str,
    target_date: date,
    readings: Sequence[FlowReading],
    threshold: float = MNF_DEFAULT_THRESHOLD,
) -> MnfResult:
    """
    Compute MNF for dma_code on target_date given a sequence of historical readings.
    readings must include at least the 30 days prior to target_date for a good baseline.
    """
    mnf = _night_min(readings, target_date)

    # Collect night minimums for baseline (exclude target_date itself)
    night_mins: list[float] = []
    seen_dates: set[date] = set()

    for r in readings:
        local = _to_casablanca(r.timestamp)
        d = local.date()
        if d == target_date or d in seen_dates:
            continue
        nm = _night_min(readings, d)
        if nm is not None:
            night_mins.append(nm)
            seen_dates.add(d)

    # Keep only the most recent MNF_ROLLING_DAYS nights
    night_mins = night_mins[-MNF_ROLLING_DAYS:]

    if len(night_mins) < MNF_MIN_NIGHTS:
        baseline = None
        flag = False
    else:
        baseline = median(night_mins)
        flag = mnf is not None and mnf > baseline * threshold

    return MnfResult(
        dma_code=dma_code,
        indicator_date=target_date,
        mnf_m3h=mnf,
        baseline_m3h=baseline,
        mnf_flag=flag,
    )
