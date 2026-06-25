"""Tenant provisioning: create PostgreSQL schema + MinIO path prefix."""
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.storage import get_storage_client

settings = get_settings()

_SLUG_RE = re.compile(r"^[a-z0-9_]{2,50}$")

# DDL to bootstrap a fresh tenant schema with the audit_log table
_TENANT_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.audit_log (
    id          UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID        NOT NULL,
    user_email  TEXT        NOT NULL,
    method      TEXT        NOT NULL,
    path        TEXT        NOT NULL,
    status_code INTEGER     NOT NULL,
    ip_address  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_{schema}_audit_log_user_id
    ON {schema}.audit_log (user_id);

CREATE INDEX IF NOT EXISTS ix_{schema}_audit_log_created_at
    ON {schema}.audit_log (created_at DESC);

-- Prevent any UPDATE or DELETE on audit_log rows (append-only)
CREATE OR REPLACE RULE audit_log_no_update AS
    ON UPDATE TO {schema}.audit_log DO INSTEAD NOTHING;
CREATE OR REPLACE RULE audit_log_no_delete AS
    ON DELETE TO {schema}.audit_log DO INSTEAD NOTHING;
"""


async def provision_tenant(slug: str, db: AsyncSession) -> None:
    """Create Postgres schema + seed tables + MinIO path prefix for a new tenant."""
    if not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid tenant slug: {slug!r}")

    # 1. Create the PostgreSQL schema
    await db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {slug}"))

    # 2. Bootstrap tables inside the schema
    for statement in _TENANT_SCHEMA_DDL.format(schema=slug).split(";"):
        stmt = statement.strip()
        if stmt:
            await db.execute(text(stmt))

    # 3. Create MinIO "folder" (zero-byte object acting as path prefix)
    try:
        client = get_storage_client(settings)
        prefix_key = f"{slug}/.keep"
        client.put_object(
            Bucket=settings.minio_bucket,
            Key=prefix_key,
            Body=b"",
            ContentLength=0,
        )
    except Exception as exc:
        # Non-fatal: MinIO prefix is cosmetic; log and continue
        import logging
        logging.getLogger(__name__).warning("MinIO prefix creation failed for %s: %s", slug, exc)
