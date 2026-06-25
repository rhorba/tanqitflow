"""Celery task: nightly NRW balance computation per DMA per tenant."""
import asyncio
import logging
from calendar import monthrange
from datetime import UTC, datetime

from database import current_tenant_slug
from services.balance import compute_balance
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.compute_nrw_balance", bind=True, max_retries=3)
def compute_nrw_balance(self, tenant_slug: str, dma_code: str, year: int, month: int):
    """
    Compute NRW balance for one DMA for the given calendar month.
    Upserts into balance_period inside the tenant schema.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from config import get_settings

    settings = get_settings()
    period_start = datetime(year, month, 1, tzinfo=UTC)
    last_day = monthrange(year, month)[1]
    period_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

    async def _run():
        engine = create_async_engine(settings.database_url, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            tok = current_tenant_slug.set(tenant_slug)
            try:
                await session.execute(
                    __import__("sqlalchemy").text(f"SET search_path TO {tenant_slug}, public")
                )
                result = await compute_balance(session, dma_code, period_start, period_end)
                await session.commit()
                return result
            finally:
                current_tenant_slug.reset(tok)
        await engine.dispose()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "balance compute failed tenant=%s dma=%s %d-%02d: %s",
            tenant_slug, dma_code, year, month, exc,
        )
        raise self.retry(exc=exc, countdown=60)
