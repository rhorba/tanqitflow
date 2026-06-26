"""Repair worklist ranker — pure Python, no DB access.

rank_score = estimated_loss_m3_per_month × water_cost_mad_per_m3 × (confidence / 100)

Higher rank_score → lower rank number (1 = most urgent).
Only DMAs with confidence_score > 10 are included.
"""
from __future__ import annotations

from dataclasses import dataclass

CONFIDENCE_THRESHOLD = 10  # minimum confidence to appear on worklist


@dataclass
class DmaLeakSignal:
    dma_code: str
    dma_name: str | None
    dma_id: str | None
    nrw_m3_per_month: float       # from latest balance_period
    confidence_score: int          # 0–100 from leak_indicator
    alert_type: str


@dataclass
class RankedItem:
    dma_code: str
    dma_name: str | None
    dma_id: str | None
    rank: int
    estimated_loss_m3_per_month: float
    savings_mad_est: float
    confidence_score: int
    alert_type: str


def rank_dmas(
    signals: list[DmaLeakSignal],
    water_cost_mad_per_m3: float = 16.0,
) -> list[RankedItem]:
    """
    Rank DMAs by repair ROI. Returns sorted list (rank 1 = most urgent).
    Skips DMAs with confidence ≤ CONFIDENCE_THRESHOLD.
    """
    eligible = [s for s in signals if s.confidence_score > CONFIDENCE_THRESHOLD]

    def rank_score(s: DmaLeakSignal) -> float:
        return s.nrw_m3_per_month * water_cost_mad_per_m3 * (s.confidence_score / 100.0)

    sorted_signals = sorted(eligible, key=rank_score, reverse=True)

    result: list[RankedItem] = []
    for i, s in enumerate(sorted_signals, start=1):
        loss = s.nrw_m3_per_month
        savings = loss * water_cost_mad_per_m3 * (s.confidence_score / 100.0)
        result.append(RankedItem(
            dma_code=s.dma_code,
            dma_name=s.dma_name,
            dma_id=s.dma_id,
            rank=i,
            estimated_loss_m3_per_month=loss,
            savings_mad_est=round(savings, 2),
            confidence_score=s.confidence_score,
            alert_type=s.alert_type,
        ))

    return result
