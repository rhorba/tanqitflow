"""Add language_pref to users

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "language_pref",
            sa.String(2),
            server_default="fr",
            nullable=False,
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "language_pref", schema="public")
