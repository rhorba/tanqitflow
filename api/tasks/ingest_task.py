"""Celery tasks for CSV ingestion: DMA inflow and customer reads."""
from __future__ import annotations

import io
import logging
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from celery import shared_task
from sqlalchemy import create_engine, text

from config import get_settings
from core.storage import get_storage_client

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Column specs per job type
# ---------------------------------------------------------------------------

_DMA_INFLOW_REQUIRED = {"dma_code", "reading_date", "volume_m3"}
_DMA_INFLOW_OPTIONAL = {"pressure_bar", "flow_rate_lps", "notes"}

_CUSTOMER_READS_REQUIRED = {"meter_id", "reading_date", "volume_m3"}
_CUSTOMER_READS_OPTIONAL = {"dma_code", "customer_type", "notes"}


def _validate_columns(df: pd.DataFrame, required: set[str], job_type: str) -> None:
    missing = required - set(df.columns.str.lower().str.strip())
    if missing:
        raise ValueError(f"[{job_type}] Missing required columns: {sorted(missing)}")


def _coerce_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    bad = df[col].isna().sum()
    if bad > 0:
        raise ValueError(f"Column '{col}' has {bad} unparseable date values")
    return df


def _load_csv_from_minio(minio_key: str) -> pd.DataFrame:
    client = get_storage_client(settings)
    obj = client.get_object(Bucket=settings.minio_bucket, Key=minio_key)
    raw = obj["Body"].read()
    try:
        return pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception:
        import chardet
        enc = chardet.detect(raw)["encoding"] or "utf-8"
        return pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str)


def _update_job(job_id: str, status: str, **kwargs: Any) -> None:
    """Sync update to public.ingestion_jobs via synchronous psycopg2 connection."""
    engine = create_engine(settings.database_sync_url, pool_pre_ping=True)
    sets = ", ".join(f"{k} = :{k}" for k in kwargs)
    if sets:
        sets = ", " + sets
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE public.ingestion_jobs SET status = :status{sets} WHERE id = :id"),
            {"status": status, "id": job_id, **kwargs},
        )
    engine.dispose()


def _insert_dma_inflow_rows(tenant_slug: str, df: pd.DataFrame) -> int:
    engine = create_engine(settings.database_sync_url, pool_pre_ping=True)
    df.columns = df.columns.str.lower().str.strip()
    df = _coerce_date(df, "reading_date")
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")

    rows_written = 0
    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {tenant_slug}, public"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dma_inflow (
                id              UUID    NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
                dma_code        TEXT    NOT NULL,
                reading_date    TIMESTAMPTZ NOT NULL,
                volume_m3       NUMERIC(14,4) NOT NULL,
                pressure_bar    NUMERIC(8,4),
                flow_rate_lps   NUMERIC(10,4),
                notes           TEXT,
                imported_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO dma_inflow
                        (dma_code, reading_date, volume_m3, pressure_bar, flow_rate_lps, notes)
                    VALUES
                        (:dma_code, :reading_date, :volume_m3, :pressure_bar, :flow_rate_lps, :notes)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "dma_code": str(row.get("dma_code", "")),
                    "reading_date": row["reading_date"],
                    "volume_m3": float(row["volume_m3"]) if pd.notna(row["volume_m3"]) else None,
                    "pressure_bar": float(row["pressure_bar"]) if "pressure_bar" in row and pd.notna(row.get("pressure_bar")) else None,
                    "flow_rate_lps": float(row["flow_rate_lps"]) if "flow_rate_lps" in row and pd.notna(row.get("flow_rate_lps")) else None,
                    "notes": row.get("notes") if pd.notna(row.get("notes", None)) else None,
                },
            )
            rows_written += 1
    engine.dispose()
    return rows_written


def _insert_customer_reads_rows(tenant_slug: str, df: pd.DataFrame) -> int:
    engine = create_engine(settings.database_sync_url, pool_pre_ping=True)
    df.columns = df.columns.str.lower().str.strip()
    df = _coerce_date(df, "reading_date")
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")

    rows_written = 0
    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {tenant_slug}, public"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_reads (
                id              UUID    NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
                meter_id        TEXT    NOT NULL,
                reading_date    TIMESTAMPTZ NOT NULL,
                volume_m3       NUMERIC(14,4) NOT NULL,
                dma_code        TEXT,
                customer_type   TEXT,
                notes           TEXT,
                imported_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO customer_reads
                        (meter_id, reading_date, volume_m3, dma_code, customer_type, notes)
                    VALUES
                        (:meter_id, :reading_date, :volume_m3, :dma_code, :customer_type, :notes)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "meter_id": str(row["meter_id"]),
                    "reading_date": row["reading_date"],
                    "volume_m3": float(row["volume_m3"]) if pd.notna(row["volume_m3"]) else None,
                    "dma_code": row.get("dma_code") if "dma_code" in row and pd.notna(row.get("dma_code")) else None,
                    "customer_type": row.get("customer_type") if "customer_type" in row and pd.notna(row.get("customer_type")) else None,
                    "notes": row.get("notes") if "notes" in row and pd.notna(row.get("notes")) else None,
                },
            )
            rows_written += 1
    engine.dispose()
    return rows_written


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, name="tasks.process_dma_inflow", max_retries=3)
def process_dma_inflow(self, job_id: str, tenant_slug: str, minio_key: str) -> dict:
    """Parse and load a DMA inflow CSV into the tenant schema."""
    _update_job(job_id, "processing")
    try:
        df = _load_csv_from_minio(minio_key)
        _validate_columns(df, _DMA_INFLOW_REQUIRED, "dma_inflow")
        rows = _insert_dma_inflow_rows(tenant_slug, df)
        _update_job(
            job_id, "done",
            row_count=rows,
            completed_at=datetime.now(UTC).isoformat(),
        )
        return {"rows": rows}
    except Exception as exc:
        logger.exception("DMA inflow task failed for job %s", job_id)
        _update_job(
            job_id, "error",
            error_detail=str(exc)[:2000],
            completed_at=datetime.now(UTC).isoformat(),
        )
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, name="tasks.process_customer_reads", max_retries=3)
def process_customer_reads(self, job_id: str, tenant_slug: str, minio_key: str) -> dict:
    """Parse and load a customer reads CSV into the tenant schema."""
    _update_job(job_id, "processing")
    try:
        df = _load_csv_from_minio(minio_key)
        _validate_columns(df, _CUSTOMER_READS_REQUIRED, "customer_reads")
        rows = _insert_customer_reads_rows(tenant_slug, df)
        _update_job(
            job_id, "done",
            row_count=rows,
            completed_at=datetime.now(UTC).isoformat(),
        )
        return {"rows": rows}
    except Exception as exc:
        logger.exception("Customer reads task failed for job %s", job_id)
        _update_job(
            job_id, "error",
            error_detail=str(exc)[:2000],
            completed_at=datetime.now(UTC).isoformat(),
        )
        raise self.retry(exc=exc, countdown=30)
