"""add email subscriptions and jobs

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-24 08:56:06.525390
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_subscriptions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(length=254), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("confirm_token_hash", sa.String(length=64), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribe_token_hash", sa.String(length=64), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'unsubscribed')",
            name=op.f("ck_email_subscriptions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_email_subscriptions_author_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_subscriptions")),
        sa.UniqueConstraint(
            "author_id", "email_normalized", name=op.f("uq_email_subscriptions_author_id")
        ),
        sa.UniqueConstraint(
            "confirm_token_hash", name=op.f("uq_email_subscriptions_confirm_token_hash")
        ),
        sa.UniqueConstraint(
            "unsubscribe_token_hash", name=op.f("uq_email_subscriptions_unsubscribe_token_hash")
        ),
    )
    op.create_table(
        "email_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'cancelled')",
            name=op.f("ck_email_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name=op.f("fk_email_jobs_article_id_articles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["email_subscriptions.id"],
            name=op.f("fk_email_jobs_subscription_id_email_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_jobs")),
        sa.UniqueConstraint("article_id", "subscription_id", name=op.f("uq_email_jobs_article_id")),
    )
    op.create_index(
        "ix_email_jobs_status_next_retry_at",
        "email_jobs",
        ["status", "next_retry_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_jobs_subscription_id"), "email_jobs", ["subscription_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_email_jobs_subscription_id"), table_name="email_jobs")
    op.drop_index("ix_email_jobs_status_next_retry_at", table_name="email_jobs")
    op.drop_table("email_jobs")
    op.drop_table("email_subscriptions")
