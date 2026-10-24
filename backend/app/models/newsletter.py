"""Email subscriptions to an author and the queue of emails to send (MAIL-01..04)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.article import Article
from app.models.user import User


class SubscriptionStatus(StrEnum):
    PENDING = "pending"  # waiting for the confirmation link (double opt-in)
    CONFIRMED = "confirmed"  # receives new-essay emails
    UNSUBSCRIBED = "unsubscribed"


class EmailSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A visitor's email address subscribed to one author. Independent of accounts."""

    __tablename__ = "email_subscriptions"
    __table_args__ = (
        UniqueConstraint("author_id", "email_normalized"),
        CheckConstraint("status IN ('pending', 'confirmed', 'unsubscribed')", name="status"),
    )

    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    email_normalized: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(16), server_default=SubscriptionStatus.PENDING)
    # One-time confirmation token: only its hash, and it expires.
    confirm_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Hash of the HMAC-derived unsubscribe token (see app.core.security.unsubscribe_token).
    unsubscribe_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship()


class EmailJobStatus(StrEnum):
    PENDING = "pending"  # waiting for the worker (or for a retry)
    SENT = "sent"
    FAILED = "failed"  # gave up: permanent error or too many attempts
    CANCELLED = "cancelled"  # unsubscribed or article no longer public before sending


class EmailJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One "new essay" email for one subscriber.

    UNIQUE(article_id, subscription_id) guarantees at most one job per article
    and subscriber, however often publish or the worker runs.
    """

    __tablename__ = "email_jobs"
    __table_args__ = (
        UniqueConstraint("article_id", "subscription_id"),
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'cancelled')", name="status"),
        Index("ix_email_jobs_status_next_retry_at", "status", "next_retry_at"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("email_subscriptions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), server_default=EmailJobStatus.PENDING)
    attempts: Mapped[int] = mapped_column(server_default="0")
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Short machine-readable reason of the last failure; never contains addresses.
    error_code: Mapped[str | None] = mapped_column(String(64))

    article: Mapped[Article] = relationship()
    subscription: Mapped[EmailSubscription] = relationship()
