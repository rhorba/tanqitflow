"""Combined confidence score — pure Python, no DB access.

Weighted average of three signals:
  MNF contribution   (default weight 0.4)
  Z-score contribution (default weight 0.3)
  IF contribution    (default weight 0.3)

If IF is disabled, weights are redistributed: MNF=0.6, Z-score=0.4.
Output: integer 0–100 + alert_type string.
"""
from __future__ import annotations

from dataclasses import dataclass

# Default weights (sum must equal 1.0)
DEFAULT_WEIGHTS = {"mnf": 0.4, "zscore": 0.3, "if": 0.3}
NO_IF_WEIGHTS = {"mnf": 0.6, "zscore": 0.4, "if": 0.0}


@dataclass
class SignalInputs:
    mnf_flag: bool
    mnf_m3h: float | None
    baseline_m3h: float | None

    zscore_flag: bool
    max_abs_zscore: float | None

    if_enabled: bool
    if_score: float | None   # 0–1
    if_flag: bool


@dataclass
class ConfidenceResult:
    confidence_score: int   # 0–100
    alert_type: str         # NONE | MNF | ZSCORE | ISOLATION_FOREST | COMBINED


def _mnf_contribution(inputs: SignalInputs) -> float:
    """0–100 contribution from MNF signal."""
    if not inputs.mnf_flag or inputs.mnf_m3h is None or inputs.baseline_m3h is None:
        return 0.0
    if inputs.baseline_m3h <= 0:
        return 50.0
    ratio = inputs.mnf_m3h / inputs.baseline_m3h  # e.g. 2.0 means 200% of baseline
    # Clamp: ratio 1.5 → 50, ratio 3.0 → 100
    return min(100.0, max(0.0, (ratio - 1.0) / 2.0 * 100.0))


def _zscore_contribution(inputs: SignalInputs) -> float:
    """0–100 contribution from Z-score signal."""
    if not inputs.zscore_flag or inputs.max_abs_zscore is None:
        return 0.0
    # |z|=3 → 50, |z|=6 → 100
    return min(100.0, max(0.0, (inputs.max_abs_zscore - 3.0) / 3.0 * 100.0))


def _if_contribution(inputs: SignalInputs) -> float:
    """0–100 contribution from Isolation Forest signal (only when flag fires)."""
    if not inputs.if_enabled or inputs.if_score is None or not inputs.if_flag:
        return 0.0
    return min(100.0, max(0.0, inputs.if_score * 100.0))


def compute_confidence(
    inputs: SignalInputs,
    weights: dict[str, float] | None = None,
) -> ConfidenceResult:
    """Compute combined confidence score and determine alert_type."""
    if weights is None:
        weights = NO_IF_WEIGHTS if not inputs.if_enabled else DEFAULT_WEIGHTS

    mnf_c = _mnf_contribution(inputs)
    z_c = _zscore_contribution(inputs)
    if_c = _if_contribution(inputs)

    raw = (
        weights["mnf"] * mnf_c
        + weights["zscore"] * z_c
        + weights["if"] * if_c
    )
    score = min(100, max(0, round(raw)))

    # Determine alert_type
    signals_fired = []
    if inputs.mnf_flag:
        signals_fired.append("MNF")
    if inputs.zscore_flag:
        signals_fired.append("ZSCORE")
    if inputs.if_enabled and inputs.if_flag:
        signals_fired.append("ISOLATION_FOREST")

    if len(signals_fired) == 0:
        alert_type = "NONE"
    elif len(signals_fired) == 1:
        alert_type = signals_fired[0]
    else:
        alert_type = "COMBINED"

    return ConfidenceResult(confidence_score=score, alert_type=alert_type)
