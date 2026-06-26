"""Celery task: generate bilingual PDF water-balance report."""
from __future__ import annotations

import asyncio
import io
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.report_task.generate_pdf_report", bind=True, max_retries=2)
def generate_pdf_report(
    self,
    tenant_slug: str,
    from_date: str,
    to_date: str,
    lang: str,
    report_id: str,
) -> dict:
    """Fetch balance + worklist data, render PDF, upload to MinIO."""
    try:
        return asyncio.run(_generate(tenant_slug, from_date, to_date, lang, report_id))
    except Exception as exc:
        logger.exception("PDF generation failed for %s", tenant_slug)
        raise self.retry(exc=exc, countdown=30) from exc


async def _generate(
    tenant_slug: str,
    from_date: str,
    to_date: str,
    lang: str,
    report_id: str,
) -> dict:
    from datetime import UTC, datetime

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from config import get_settings
    from core.storage import get_storage_client
    from database import current_tenant_slug
    from domain.pdf_report import (
        DmaSummaryRow,
        ReportData,
        ReportPeriod,
        WorklistRow,
        render_pdf,
    )

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        tok = current_tenant_slug.set(tenant_slug)
        try:
            await db.execute(text(f'SET search_path TO "{tenant_slug}", public'))  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text

            tenant_row = await db.execute(
                text("SELECT name FROM public.tenants WHERE slug = :slug"),
                {"slug": tenant_slug},
            )
            tenant_name = (tenant_row.fetchone() or (tenant_slug,))[0]

            dma_rows_raw = await db.execute(
                text("""
                    SELECT
                        d.code, d.name,
                        b.siv_m3::float, b.scv_m3::float,
                        b.nrw_m3::float, b.nrw_pct::float,
                        b.flag_level
                    FROM dma d
                    LEFT JOIN LATERAL (
                        SELECT siv_m3, scv_m3, nrw_m3, nrw_pct, flag_level
                        FROM balance_period
                        WHERE dma_code = d.code
                          AND period_start >= :from_dt
                          AND period_start <= :to_dt
                        ORDER BY period_start DESC
                        LIMIT 1
                    ) b ON true
                    WHERE d.is_active = true AND b.nrw_m3 IS NOT NULL
                    ORDER BY b.nrw_m3 DESC
                    LIMIT 10
                """),
                {"from_dt": from_date, "to_dt": to_date},
            )

            wl_raw = await db.execute(
                text("""
                    SELECT wi.rank, wi.dma_code, d.name AS dma_name,
                           wi.estimated_loss_m3_per_month,
                           wi.savings_mad_est,
                           wi.confidence_score,
                           wi.alert_type,
                           wi.status
                    FROM worklist_item wi
                    LEFT JOIN dma d ON d.code = wi.dma_code
                    ORDER BY wi.rank
                    LIMIT 20
                """),
            )
        finally:
            current_tenant_slug.reset(tok)

    dma_rows = [
        DmaSummaryRow(
            code=r.code, name=r.name,
            siv_m3=r.siv_m3 or 0, scv_m3=r.scv_m3 or 0,
            nrw_m3=r.nrw_m3 or 0, nrw_pct=r.nrw_pct or 0,
            flag_level=r.flag_level or "normal",
        )
        for r in dma_rows_raw.fetchall()
    ]

    worklist_rows = [
        WorklistRow(
            rank=r.rank, dma_code=r.dma_code, dma_name=r.dma_name,
            estimated_loss_m3=r.estimated_loss_m3_per_month,
            savings_mad=r.savings_mad_est,
            confidence_score=r.confidence_score,
            alert_type=r.alert_type,
            status=r.status,
        )
        for r in wl_raw.fetchall()
    ]

    await engine.dispose()

    report = ReportData(
        tenant_name=tenant_name,
        period=ReportPeriod(from_date=from_date, to_date=to_date),
        lang=lang,
        dma_rows=dma_rows,
        worklist_rows=worklist_rows,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    pdf_bytes = render_pdf(report)

    minio_key = f"{tenant_slug}/reports/{report_id}.pdf"
    s3 = get_storage_client(settings)
    s3.upload_fileobj(
        io.BytesIO(pdf_bytes),
        settings.minio_bucket,
        minio_key,
        ExtraArgs={"ContentType": "application/pdf"},
    )

    return {"minio_key": minio_key, "size_bytes": len(pdf_bytes)}
