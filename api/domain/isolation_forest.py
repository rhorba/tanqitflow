"""Isolation Forest anomaly detector — scikit-learn, no DB access.

Features per DMA (90-day window):
  hourly_mean_flow, hourly_std_flow, mnf_m3h, daily_range_flow,
  night_day_ratio, mean_pressure, std_pressure

Model serialised as pickle → MinIO at {tenant}/models/if_model_{dma_code}.pkl
Returns score 0–1 (higher = more anomalous). Requires ≥ 90 days of data.
"""
from __future__ import annotations

import math
import pickle
from dataclasses import dataclass

IF_MIN_DAYS = 90
IF_CONTAMINATION = 0.05  # expected fraction of anomalies


@dataclass
class IFFeatureVector:
    """Feature row for one DMA measurement window."""
    hourly_mean_flow: float
    hourly_std_flow: float
    mnf_m3h: float
    daily_range_flow: float
    night_day_ratio: float
    mean_pressure: float
    std_pressure: float

    def to_list(self) -> list[float]:
        return [
            self.hourly_mean_flow,
            self.hourly_std_flow,
            self.mnf_m3h,
            self.daily_range_flow,
            self.night_day_ratio,
            self.mean_pressure,
            self.std_pressure,
        ]


@dataclass
class IFResult:
    dma_code: str
    score: float | None       # 0–1, higher = more anomalous
    if_flag: bool
    reason: str | None        # set when score is None


def train_isolation_forest(feature_rows: list[IFFeatureVector]) -> bytes:
    """Train an IF model on historical feature vectors; return pickled bytes."""
    from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

    x = [row.to_list() for row in feature_rows]
    model = IsolationForest(
        n_estimators=100,
        contamination=IF_CONTAMINATION,
        random_state=42,
    )
    model.fit(x)
    return pickle.dumps(model)


def score_isolation_forest(
    model_bytes: bytes,
    feature: IFFeatureVector,
    flag_threshold: float = 0.6,
) -> IFResult:
    """Score a single feature vector against a trained model."""
    model = pickle.loads(model_bytes)  # noqa: S301 — internal trusted pickle
    raw_score = model.decision_function([feature.to_list()])[0]
    # decision_function returns negative for anomalies; map to [0,1] (higher=anomaly)
    score = float(max(0.0, min(1.0, 0.5 - raw_score / 2)))
    flag = score >= flag_threshold
    return IFResult(dma_code="", score=score, if_flag=flag, reason=None)


def build_feature_vector(
    flow_readings: list[float],
    night_flows: list[float],
    day_flows: list[float],
    pressure_readings: list[float],
) -> IFFeatureVector | None:
    """Build a feature vector from raw lists. Returns None if data is insufficient."""
    if not flow_readings:
        return None

    def safe_std(vals: list[float]) -> float:
        if len(vals) < 2:
            return 0.0
        mu = sum(vals) / len(vals)
        return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))

    mu_flow = sum(flow_readings) / len(flow_readings)
    std_flow = safe_std(flow_readings)
    mnf = min(night_flows) if night_flows else mu_flow
    daily_range = max(flow_readings) - min(flow_readings)
    mean_night = sum(night_flows) / len(night_flows) if night_flows else mu_flow
    mean_day = sum(day_flows) / len(day_flows) if day_flows else mu_flow
    night_day_ratio = mean_night / mean_day if mean_day > 0 else 1.0
    mu_pressure = sum(pressure_readings) / len(pressure_readings) if pressure_readings else 0.0
    std_pressure = safe_std(pressure_readings) if pressure_readings else 0.0

    return IFFeatureVector(
        hourly_mean_flow=mu_flow,
        hourly_std_flow=std_flow,
        mnf_m3h=mnf,
        daily_range_flow=daily_range,
        night_day_ratio=night_day_ratio,
        mean_pressure=mu_pressure,
        std_pressure=std_pressure,
    )
