"""Sprint 5: leak_indicator, anomaly_event, worklist_item in tenant schema

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-26

All three tables live in each tenant's PostgreSQL schema.
No public-schema DDL is needed here — tenant schemas are bootstrapped by
services/tenant.py::provision_tenant(), which now includes all three tables.
anomaly_event is a TimescaleDB hypertable (partitioned by event_time).
"""
from collections.abc import Sequence

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tenant-schema tables are created via provision_tenant() DDL.
    pass


def downgrade() -> None:
    pass
