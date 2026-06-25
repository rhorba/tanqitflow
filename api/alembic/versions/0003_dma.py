"""Sprint 3: DMA table in tenant schema template

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25

NOTE: This migration creates tables in the public schema as a template.
Actual per-tenant DMA tables are created by the tenant provisioning service
using provision_tenant() which clones this structure into each tenant schema.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # public.ingestion_jobs — tracks all upload jobs across all tenants
    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),  # dma_inflow | customer_reads | pressure_flow
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("minio_key", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),  # queued|processing|done|error
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_ingestion_jobs_tenant_id", "ingestion_jobs", ["tenant_id"], schema="public"
    )
    op.create_index(
        "ix_ingestion_jobs_status", "ingestion_jobs", ["status"], schema="public"
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs", schema="public")
    op.drop_index("ix_ingestion_jobs_tenant_id", table_name="ingestion_jobs", schema="public")
    op.drop_table("ingestion_jobs", schema="public")
