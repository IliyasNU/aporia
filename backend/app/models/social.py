"""Follows, bookmarks, comments and reports (SOC-01, SOC-02, MOD-01)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import User


class ModerationStatus(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"  # hidden by an admin; gone from every public view


class Follow(Base):
    """`follower` reads `author`. The primary key makes each pair unique."""

    __tablename__ = "follows"
    __table_args__ = (CheckConstraint("follower_id <> author_id", name="not_self"),)

    follower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship(foreign_keys=[author_id])


class Bookmark(Base):
    __tablename__ = "bookmarks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A flat comment (no replies in v1.0)."""

    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("moderation_status IN ('visible', 'hidden')", name="moderation_status"),
        Index("ix_comments_article_id_created_at", "article_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(2000))
    moderation_status: Mapped[str] = mapped_column(
        String(16), server_default=ModerationStatus.VISIBLE.value
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship()


class ReportTarget(StrEnum):
    ARTICLE = "article"
    COMMENT = "comment"


class ReportStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class Report(UUIDPrimaryKeyMixin, Base):
    """A user's complaint about an article or comment, for admins to review."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("target_type IN ('article', 'comment')", name="target_type"),
        CheckConstraint("status IN ('open', 'resolved')", name="status"),
        # One report per user and target: repeated clicks do not flood the queue.
        UniqueConstraint(
            "reporter_id", "target_type", "target_id", name="uq_reports_reporter_target"
        ),
        Index("ix_reports_status_created_at", "status", "created_at"),
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Polymorphic target (article or comment), so no foreign key; checked in the service.
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[uuid.UUID]
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), server_default=ReportStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
