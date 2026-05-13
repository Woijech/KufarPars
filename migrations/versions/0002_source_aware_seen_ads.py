"""Make seen listings source-aware.

Revision ID: 0002_source_aware_seen_ads
Revises: 0001_initial
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_source_aware_seen_ads"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source columns and include source in seen-ad uniqueness."""
    op.add_column(
        "seen_ads",
        sa.Column(
            "source",
            sa.String(length=40),
            server_default="kufar",
            nullable=False,
        ),
    )
    op.add_column(
        "notification_logs",
        sa.Column(
            "source",
            sa.String(length=40),
            server_default="kufar",
            nullable=False,
        ),
    )
    op.drop_constraint("seen_ads_pkey", "seen_ads", type_="primary")
    op.create_primary_key(
        "seen_ads_pkey",
        "seen_ads",
        ["subscription_id", "source", "ad_id"],
    )
    op.alter_column("seen_ads", "source", server_default=None)
    op.alter_column("notification_logs", "source", server_default=None)


def downgrade() -> None:
    """Return to Kufar-only seen-ad uniqueness."""
    op.drop_constraint("seen_ads_pkey", "seen_ads", type_="primary")
    op.create_primary_key("seen_ads_pkey", "seen_ads", ["subscription_id", "ad_id"])
    op.drop_column("notification_logs", "source")
    op.drop_column("seen_ads", "source")
