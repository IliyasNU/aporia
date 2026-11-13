"""add social features and moderation

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-24 08:41:35.312403
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("follower_id <> author_id", name=op.f("ck_follows_not_self")),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_follows_author_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["follower_id"],
            ["users.id"],
            name=op.f("fk_follows_follower_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("follower_id", "author_id", name=op.f("pk_follows")),
    )
    op.create_index(op.f("ix_follows_author_id"), "follows", ["author_id"], unique=False)
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('open', 'resolved')", name=op.f("ck_reports_status")),
        sa.CheckConstraint(
            "target_type IN ('article', 'comment')", name=op.f("ck_reports_target_type")
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name=op.f("fk_reports_reporter_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint(
            "reporter_id", "target_type", "target_id", name="uq_reports_reporter_target"
        ),
    )
    op.create_index(
        "ix_reports_status_created_at", "reports", ["status", "created_at"], unique=False
    )
    op.create_table(
        "bookmarks",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name=op.f("fk_bookmarks_article_id_articles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_bookmarks_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "article_id", name=op.f("pk_bookmarks")),
    )
    op.create_index(op.f("ix_bookmarks_article_id"), "bookmarks", ["article_id"], unique=False)
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=2000), nullable=False),
        sa.Column(
            "moderation_status", sa.String(length=16), server_default="visible", nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            "moderation_status IN ('visible', 'hidden')", name=op.f("ck_comments_moderation_status")
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name=op.f("fk_comments_article_id_articles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_comments_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(
        "ix_comments_article_id_created_at", "comments", ["article_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_comments_user_id"), "comments", ["user_id"], unique=False)
    op.add_column(
        "articles",
        sa.Column(
            "moderation_status", sa.String(length=16), server_default="visible", nullable=False
        ),
    )
    # Autogenerate does not detect CHECK constraints on existing tables; added by hand.
    op.create_check_constraint(
        op.f("ck_articles_moderation_status"),
        "articles",
        "moderation_status IN ('visible', 'hidden')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_articles_moderation_status"), "articles", type_="check")
    op.drop_column("articles", "moderation_status")
    op.drop_index(op.f("ix_comments_user_id"), table_name="comments")
    op.drop_index("ix_comments_article_id_created_at", table_name="comments")
    op.drop_table("comments")
    op.drop_index(op.f("ix_bookmarks_article_id"), table_name="bookmarks")
    op.drop_table("bookmarks")
    op.drop_index("ix_reports_status_created_at", table_name="reports")
    op.drop_table("reports")
    op.drop_index(op.f("ix_follows_author_id"), table_name="follows")
    op.drop_table("follows")
