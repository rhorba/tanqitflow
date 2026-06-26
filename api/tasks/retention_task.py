"""Monthly PII retention task — Law 09-08 compliance.

Nulls out PII fields for user accounts inactive for > 5 years.
Does NOT hard-delete rows (audit trail is preserved).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_RETENTION_YEARS = 5


@celery_app.task(name="tasks.retention_task.monthly_pii_retention")
def monthly_pii_retention() -> dict:
    """Null PII fields for users with last_login_at > 5 years ago (or never logged in > 5y)."""
    return asyncio.run(_run_retention())


async def _run_retention() -> dict:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from config import get_settings

    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=365 * _RETENTION_YEARS)

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        result = await db.execute(
            text("""
                UPDATE public.users
                SET full_name_enc = NULL
                WHERE full_name_enc IS NOT NULL
                  AND (
                      last_login_at IS NULL AND created_at < :cutoff
                      OR last_login_at < :cutoff
                  )
                RETURNING id
            """),
            {"cutoff": cutoff},
        )
        erased_count = len(result.fetchall())
        await db.commit()

    await engine.dispose()
    logger.info("PII retention: erased full_name_enc for %d users (cutoff %s)", erased_count, cutoff.date())
    return {"erased_users": erased_count, "cutoff": cutoff.isoformat()}
