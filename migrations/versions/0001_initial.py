"""Initial bot storage schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create chats, subscriptions, seen ads, and notification logs."""
    op.create_table(
        "chats",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("watch_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "title", name="uq_subscriptions_chat_title"),
    )
    op.create_index(
        "idx_subscriptions_enabled",
        "subscriptions",
        ["enabled"],
        unique=False,
    )
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("ad_id", sa.BigInteger(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_notification_logs_subscription_sent_at",
        "notification_logs",
        ["subscription_id", "sent_at"],
        unique=False,
    )
    op.create_table(
        "seen_ads",
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("ad_id", sa.BigInteger(), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("subscription_id", "ad_id"),
    )
    op.create_index(
        "idx_seen_ads_subscription_seen_at",
        "seen_ads",
        ["subscription_id", "seen_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop bot storage tables."""
    op.drop_index("idx_seen_ads_subscription_seen_at", table_name="seen_ads")
    op.drop_table("seen_ads")
    op.drop_index(
        "idx_notification_logs_subscription_sent_at",
        table_name="notification_logs",
    )
    op.drop_table("notification_logs")
    op.drop_index("idx_subscriptions_enabled", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("chats")
