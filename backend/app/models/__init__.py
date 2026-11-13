"""All ORM models, imported here so Alembic sees the complete metadata."""

from app.models.article import Article, ArticleStatus, article_tags
from app.models.newsletter import (
    EmailJob,
    EmailJobStatus,
    EmailSubscription,
    SubscriptionStatus,
)
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
    "EmailJob",
    "EmailJobStatus",
    "EmailSubscription",
    "Follow",
    "ModerationStatus",
    "Report",
    "ReportStatus",
    "ReportTarget",
    "SubscriptionStatus",
    "Tag",
    "User",
    "UserRole",
    "UserSession",
    "article_tags",
    "user_interest_tags",
]
