"""Celery tasks: nightly leak detection + monthly IF retrain."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Nightly leak detection (MNF + Z-score + IF + confidence + worklist refresh)
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.nightly_leak_detection", bind=True, max_retries=3)
def nightly_leak_detection(self, tenant_slug: str, target_date_iso: str | None = None):
    """
    Run full leak detection pipeline for all active DMAs in tenant_slug.
    target_date_iso: YYYY-MM-DD (defaults to yesterday UTC).
    """
    asyncio.run(_run_leak_detection(tenant_slug, target_date_iso))


async def _run_leak_detection(tenant_slug: str, target_date_iso: str | None) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from config import get_settings
    from core.storage import get_storage_client
    from database import current_tenant_slug

    settings = get_settings()
    target = (
        date.fromisoformat(target_date_iso)
        if target_date_iso
        else (datetime.now(UTC) - timedelta(days=1)).date()
    )
    window_end = datetime(target.year, target.month, target.day, 23, 59, 59, tzinfo=UTC)
    flow_window_start = window_end - timedelta(days=90)

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        tok = current_tenant_slug.set(tenant_slug)
        try:
            await db.execute(text(f'SET search_path TO "{tenant_slug}", public'))  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
            rows = await db.execute(text("SELECT id::text, code FROM dma WHERE is_active = true"))
            dmas = [(r.id, r.code) for r in rows]
            storage = get_storage_client(settings)

            for dma_id, dma_code in dmas:
                try:
                    await _process_dma(
                        db, storage, settings, tenant_slug,
                        dma_id, dma_code, target, window_end, flow_window_start,
                    )
                except Exception as exc:
                    logger.warning("leak detection failed dma=%s: %s", dma_code, exc)

            await db.commit()
        finally:
            current_tenant_slug.reset(tok)

    await engine.dispose()


async def _process_dma(db, storage, settings, tenant_slug, dma_id, dma_code,
                        target, window_end, flow_window_start):
    from sqlalchemy import text

    from domain.confidence_score import SignalInputs, compute_confidence
    from domain.isolation_forest import IF_MIN_DAYS, build_feature_vector, score_isolation_forest
    from domain.mnf_calculator import FlowReading, compute_mnf
    from domain.zscore_detector import MetricPoint, detect_anomalies

    # 1. Fetch raw inflow data (90-day window)
    inflow_rows = await db.execute(
        text(
            "SELECT reading_date, volume_m3, flow_rate_lps, pressure_bar "
            "FROM dma_inflow WHERE dma_code = :code "
            "AND reading_date >= :start AND reading_date <= :end "
            "ORDER BY reading_date"
        ),
        {"code": dma_code, "start": flow_window_start, "end": window_end},
    )
    inflow_data = inflow_rows.fetchall()

    # 2. MNF signal
    flow_readings = [
        FlowReading(timestamp=r.reading_date, flow_m3h=float(r.flow_rate_lps or r.volume_m3))
        for r in inflow_data
    ]
    mnf_result = compute_mnf(dma_code, target, flow_readings)

    # 3. Z-score signal
    metric_points = []
    for r in inflow_data:
        if r.flow_rate_lps is not None:
            metric_points.append(MetricPoint(
                timestamp=r.reading_date, metric="flow_rate_lps", value=float(r.flow_rate_lps)
            ))
        if r.pressure_bar is not None:
            metric_points.append(MetricPoint(
                timestamp=r.reading_date, metric="pressure_bar", value=float(r.pressure_bar)
            ))

    z_result = detect_anomalies(dma_code, metric_points, window_end)

    for anom in z_result.anomalies:
        await db.execute(
            text(
                "INSERT INTO anomaly_event (dma_code, event_time, metric, value, zscore) "
                "VALUES (:code, :ts, :metric, :val, :z) ON CONFLICT DO NOTHING"
            ),
            {
                "code": dma_code, "ts": anom.timestamp,
                "metric": anom.metric, "val": anom.value, "z": anom.zscore,
            },
        )

    # 4. Isolation Forest signal
    all_flows = [float(r.flow_rate_lps or r.volume_m3) for r in inflow_data]
    pressures = [float(r.pressure_bar) for r in inflow_data if r.pressure_bar is not None]
    night_flows = [
        float(r.flow_rate_lps or r.volume_m3) for r in inflow_data
        if 2 <= r.reading_date.hour < 4
    ]
    day_flows = [
        float(r.flow_rate_lps or r.volume_m3) for r in inflow_data
        if 8 <= r.reading_date.hour < 20
    ]

    if_score = None
    if_flag = False
    if_enabled = len(inflow_data) >= IF_MIN_DAYS

    if if_enabled:
        model_key = f"{tenant_slug}/models/if_model_{dma_code}.pkl"
        try:
            model_obj = storage.get_object(Bucket=settings.minio_bucket, Key=model_key)
            model_bytes = model_obj["Body"].read()
            fv = build_feature_vector(all_flows, night_flows, day_flows, pressures)
            if fv is not None:
                result = score_isolation_forest(model_bytes, fv)
                if_score = result.score
                if_flag = result.if_flag
        except Exception:
            if_enabled = False  # no model yet — skip

    # 5. Confidence score
    inputs = SignalInputs(
        mnf_flag=mnf_result.mnf_flag,
        mnf_m3h=mnf_result.mnf_m3h,
        baseline_m3h=mnf_result.baseline_m3h,
        zscore_flag=z_result.zscore_flag,
        max_abs_zscore=z_result.max_abs_zscore,
        if_enabled=if_enabled,
        if_score=if_score,
        if_flag=if_flag,
    )
    conf = compute_confidence(inputs)

    # 6. Upsert leak_indicator
    await db.execute(
        text("""
            INSERT INTO leak_indicator
                (dma_id, dma_code, indicator_date,
                 mnf_m3h, baseline_m3h, mnf_flag,
                 max_zscore, zscore_flag,
                 if_anomaly_score, if_flag,
                 confidence_score, alert_type, computed_at)
            VALUES
                (:dma_id, :dma_code, :indicator_date,
                 :mnf_m3h, :baseline_m3h, :mnf_flag,
                 :max_zscore, :zscore_flag,
                 :if_score, :if_flag,
                 :confidence_score, :alert_type, NOW())
            ON CONFLICT (dma_code, indicator_date)
            DO UPDATE SET
                mnf_m3h          = EXCLUDED.mnf_m3h,
                baseline_m3h     = EXCLUDED.baseline_m3h,
                mnf_flag         = EXCLUDED.mnf_flag,
                max_zscore       = EXCLUDED.max_zscore,
                zscore_flag      = EXCLUDED.zscore_flag,
                if_anomaly_score = EXCLUDED.if_anomaly_score,
                if_flag          = EXCLUDED.if_flag,
                confidence_score = EXCLUDED.confidence_score,
                alert_type       = EXCLUDED.alert_type,
                computed_at      = NOW()
        """),
        {
            "dma_id": dma_id, "dma_code": dma_code, "indicator_date": target,
            "mnf_m3h": mnf_result.mnf_m3h, "baseline_m3h": mnf_result.baseline_m3h,
            "mnf_flag": mnf_result.mnf_flag,
            "max_zscore": z_result.max_abs_zscore, "zscore_flag": z_result.zscore_flag,
            "if_score": if_score, "if_flag": if_flag,
            "confidence_score": conf.confidence_score, "alert_type": conf.alert_type,
        },
    )


# ---------------------------------------------------------------------------
# Monthly IF retrain
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.monthly_if_retrain", bind=True, max_retries=2)
def monthly_if_retrain(self, tenant_slug: str):
    """Re-train Isolation Forest models for all DMAs with ≥ 90 days of data."""
    asyncio.run(_run_retrain(tenant_slug))


async def _run_retrain(tenant_slug: str) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from config import get_settings
    from core.storage import get_storage_client
    from database import current_tenant_slug
    from domain.isolation_forest import IF_MIN_DAYS, build_feature_vector, train_isolation_forest

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    now = datetime.now(UTC)
    window_start = now - timedelta(days=90)

    async with session_factory() as db:
        tok = current_tenant_slug.set(tenant_slug)
        try:
            await db.execute(text(f'SET search_path TO "{tenant_slug}", public'))  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
            rows = await db.execute(text("SELECT id::text, code FROM dma WHERE is_active = true"))
            dmas = [(r.id, r.code) for r in rows]
            storage = get_storage_client(settings)

            for _dma_id, dma_code in dmas:
                try:
                    inflow_rows = await db.execute(
                        text(
                            "SELECT reading_date, volume_m3, flow_rate_lps, pressure_bar "
                            "FROM dma_inflow WHERE dma_code = :code AND reading_date >= :start "
                            "ORDER BY reading_date"
                        ),
                        {"code": dma_code, "start": window_start},
                    )
                    inflow_data = inflow_rows.fetchall()

                    if len(inflow_data) < IF_MIN_DAYS:
                        continue

                    all_flows = [float(r.flow_rate_lps or r.volume_m3) for r in inflow_data]
                    pressures = [float(r.pressure_bar) for r in inflow_data if r.pressure_bar]
                    night_flows = [
                        float(r.flow_rate_lps or r.volume_m3) for r in inflow_data
                        if 2 <= r.reading_date.hour < 4
                    ]
                    day_flows = [
                        float(r.flow_rate_lps or r.volume_m3) for r in inflow_data
                        if 8 <= r.reading_date.hour < 20
                    ]

                    fv = build_feature_vector(all_flows, night_flows, day_flows, pressures)
                    if not fv:
                        continue

                    model_bytes = train_isolation_forest([fv])
                    model_key = f"{tenant_slug}/models/if_model_{dma_code}.pkl"
                    storage.put_object(
                        Bucket=settings.minio_bucket,
                        Key=model_key,
                        Body=model_bytes,
                        ContentLength=len(model_bytes),
                    )
                    logger.info("IF model retrained for tenant=%s dma=%s", tenant_slug, dma_code)

                except Exception as exc:
                    logger.warning("retrain failed dma=%s: %s", dma_code, exc)

        finally:
            current_tenant_slug.reset(tok)

    await engine.dispose()
