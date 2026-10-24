import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tag import Tag
from app.models.user import User


class ArticleStatus(StrEnum):
    DRAFT = "draft"  # never published; only the author sees it
    PUBLISHED = "published"  # public
    UNPUBLISHED = "unpublished"  # was public, taken down by the author


article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Article(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'unpublished')", name="status"),
        Index("ix_articles_status_published_at", "status", "published_at"),
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    # Follows the title while the article is a draft; frozen at the first publish
    # so public links never break (ART-02).
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    summary: Mapped[str] = mapped_column(String(300), server_default="")
    body_markdown: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[str] = mapped_column(String(16), server_default=ArticleStatus.DRAFT.value)
    # Time of the FIRST publication. Never reset, so republishing does not
    # look like a new article (and does not send emails again, Stage 5).
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Soft delete: the row stays for integrity, but nobody sees the article.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=article_tags, order_by=Tag.slug)
