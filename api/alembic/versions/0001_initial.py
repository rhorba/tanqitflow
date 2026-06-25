"""Initial schema: extensions + public.tenants

Revision ID: 0001
Revises:
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL extensions (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # public.tenants — one row per ONEE region or SRM distributor
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(50), nullable=False, unique=True, comment="Used as PostgreSQL schema name"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("cost_conventional_mad", sa.Numeric(8, 4), server_default="4.0", nullable=False),
        sa.Column("cost_desalinated_mad", sa.Numeric(8, 4), server_default="16.0", nullable=False),
        sa.Column("enable_ml_detection", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        schema="public",
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True, schema="public")


def downgrade() -> None:
    op.drop_index("ix_tenants_slug", table_name="tenants", schema="public")
    op.drop_table("tenants", schema="public")
