"""Sprint 5: enable PostGIS extension

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-26

PostGIS is required for the DMA spatial map feature.
The extension is database-level; once enabled it covers all tenant schemas.
Tenant DDL (services/tenant.py) is updated separately to use geometry columns.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    # Intentionally not dropping postgis — dropping it would destroy all geometry
    # columns across every tenant schema, which is not safely reversible here.
    pass
