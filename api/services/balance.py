"""NRW balance calculation service."""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_FLAG_WARNING = Decimal("25.0")
_FLAG_CRITICAL = Decimal("40.0")


def _flag_level(nrw_pct: Decimal) -> str:
    if nrw_pct >= _FLAG_CRITICAL:
        return "critical"
    if nrw_pct >= _FLAG_WARNING:
        return "warning"
    return "normal"


async def compute_balance(
    db: AsyncSession,
    dma_code: str,
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """
    Aggregate inflow and customer reads for one DMA over [period_start, period_end],
    compute NRW metrics, upsert into balance_period, and return the row as a dict.
    """
    siv_row = await db.execute(
        text(
            "SELECT COALESCE(SUM(volume_m3), 0) FROM dma_inflow "
            "WHERE dma_code = :code AND reading_date >= :start AND reading_date < :end"
        ),
        {"code": dma_code, "start": period_start, "end": period_end},
    )
    siv_m3: Decimal = Decimal(str(siv_row.scalar() or 0))

    scv_row = await db.execute(
        text(
            "SELECT COALESCE(SUM(volume_m3), 0) FROM customer_reads "
            "WHERE dma_code = :code AND reading_date >= :start AND reading_date < :end"
        ),
        {"code": dma_code, "start": period_start, "end": period_end},
    )
    scv_m3: Decimal = Decimal(str(scv_row.scalar() or 0))

    nrw_m3 = siv_m3 - scv_m3
    nrw_pct = (nrw_m3 / siv_m3 * 100).quantize(Decimal("0.0001")) if siv_m3 > 0 else Decimal("0")

    dma_row = await db.execute(
        text("SELECT id, pipe_length_km FROM dma WHERE code = :code"),
        {"code": dma_code},
    )
    dma = dma_row.first()
    dma_id = dma.id if dma else None
    pipe_km = Decimal(str(dma.pipe_length_km)) if dma and dma.pipe_length_km else None
    leakage_index = (nrw_m3 / pipe_km).quantize(Decimal("0.0001")) if pipe_km and pipe_km > 0 else None

    flag = _flag_level(nrw_pct)
    now = datetime.now(UTC)

    await db.execute(
        text("""
            INSERT INTO balance_period
                (dma_id, dma_code, period_start, period_end,
                 siv_m3, scv_m3, nrw_m3, nrw_pct, leakage_index, flag_level, computed_at)
            VALUES
                (:dma_id, :dma_code, :period_start, :period_end,
                 :siv_m3, :scv_m3, :nrw_m3, :nrw_pct, :leakage_index, :flag_level, :computed_at)
            ON CONFLICT (dma_code, period_start)
            DO UPDATE SET
                siv_m3        = EXCLUDED.siv_m3,
                scv_m3        = EXCLUDED.scv_m3,
                nrw_m3        = EXCLUDED.nrw_m3,
                nrw_pct       = EXCLUDED.nrw_pct,
                leakage_index = EXCLUDED.leakage_index,
                flag_level    = EXCLUDED.flag_level,
                computed_at   = EXCLUDED.computed_at
        """),
        {
            "dma_id": str(dma_id) if dma_id else None,
            "dma_code": dma_code,
            "period_start": period_start,
            "period_end": period_end,
            "siv_m3": float(siv_m3),
            "scv_m3": float(scv_m3),
            "nrw_m3": float(nrw_m3),
            "nrw_pct": float(nrw_pct),
            "leakage_index": float(leakage_index) if leakage_index is not None else None,
            "flag_level": flag,
            "computed_at": now,
        },
    )

    return {
        "dma_code": dma_code,
        "period_start": period_start,
        "period_end": period_end,
        "siv_m3": float(siv_m3),
        "scv_m3": float(scv_m3),
        "nrw_m3": float(nrw_m3),
        "nrw_pct": float(nrw_pct),
        "leakage_index": float(leakage_index) if leakage_index is not None else None,
        "flag_level": flag,
        "computed_at": now.isoformat(),
    }


async def get_summary(db: AsyncSession) -> dict:
    """Latest-period aggregate KPIs across all DMAs."""
    row = await db.execute(
        text("""
            SELECT
                COALESCE(SUM(siv_m3), 0)                                   AS total_siv,
                COALESCE(SUM(scv_m3), 0)                                   AS total_scv,
                COALESCE(SUM(nrw_m3), 0)                                   AS total_nrw,
                CASE WHEN SUM(siv_m3) > 0
                     THEN ROUND(SUM(nrw_m3) / SUM(siv_m3) * 100, 2)
                     ELSE 0 END                                            AS nrw_pct,
                COUNT(*) FILTER (WHERE flag_level IN ('warning','critical')) AS flagged_dmas
            FROM balance_period
            WHERE period_start = (SELECT MAX(period_start) FROM balance_period)
        """)
    )
    r = row.first()
    return {
        "siv_m3": float(r.total_siv or 0),
        "scv_m3": float(r.total_scv or 0),
        "nrw_m3": float(r.total_nrw or 0),
        "nrw_pct": float(r.nrw_pct or 0),
        "flagged_dmas": int(r.flagged_dmas or 0),
    }


async def get_trend(db: AsyncSession, months: int = 12) -> list[dict]:
    """Monthly NRW trend aggregated across all DMAs, most recent `months` periods."""
    rows = await db.execute(
        text("""
            SELECT
                TO_CHAR(period_start, 'YYYY-MM')          AS month,
                COALESCE(SUM(siv_m3), 0)                  AS siv_m3,
                COALESCE(SUM(nrw_m3), 0)                  AS nrw_m3,
                CASE WHEN SUM(siv_m3) > 0
                     THEN ROUND(SUM(nrw_m3) / SUM(siv_m3) * 100, 2)
                     ELSE 0 END                           AS nrw_pct
            FROM balance_period
            GROUP BY TO_CHAR(period_start, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT :months
        """),
        {"months": months},
    )
    return [
        {
            "month": r.month,
            "siv_m3": float(r.siv_m3),
            "nrw_m3": float(r.nrw_m3),
            "nrw_pct": float(r.nrw_pct),
        }
        for r in rows
    ]
