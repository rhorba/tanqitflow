"""Add full_name_enc (encrypted PII) to public.users

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("full_name_enc", sa.String(1024), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "full_name_enc", schema="public")
