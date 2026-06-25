"""Sprint 4: balance_period table in tenant schema template

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-25

NOTE: balance_period lives in each tenant's PostgreSQL schema, not in public.
No public-schema DDL is needed here. Tenant schemas are bootstrapped by
services/tenant.py::provision_tenant(), which now includes the balance_period
table. Existing tenants must run the ALTER statement in the downgrade notes
manually (no-op for dev/test environments where tenants are re-provisioned).
"""
from collections.abc import Sequence

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No public-schema changes; balance_period is a tenant-schema table.
    pass


def downgrade() -> None:
    pass
