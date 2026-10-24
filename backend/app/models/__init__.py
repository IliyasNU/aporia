"""All ORM models, imported here so Alembic sees the complete metadata."""

from app.models.article import Article, ArticleStatus, article_tags
from app.models.social import (
    Bookmark,
    Comment,
    Follow,
    ModerationStatus,
    Report,
    ReportStatus,
    ReportTarget,
)
from app.models.tag import Tag
from app.models.user import User, UserRole, UserSession, user_interest_tags

__all__ = [
    "Article",
    "ArticleStatus",
    "Bookmark",
    "Comment",
    "Follow",
    "ModerationStatus",
    "Report",
    "ReportStatus",
    "ReportTarget",
    "Tag",
    "User",
    "UserRole",
    "UserSession",
    "article_tags",
    "user_interest_tags",
]
