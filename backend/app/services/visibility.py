"""One definition of "the public may see this article", used by every public query.

Lists, search, tag counts, feeds, bookmarks and recommendations all go through
this, so drafts, unpublished, deleted and moderator-hidden articles cannot leak
into any of them.
"""

from sqlalchemy import ColumnElement, and_

from app.models import Article, ArticleStatus, Comment, ModerationStatus


def publicly_visible() -> ColumnElement[bool]:
    return and_(
        Article.status == ArticleStatus.PUBLISHED,
        Article.deleted_at.is_(None),
        Article.moderation_status == ModerationStatus.VISIBLE,
    )


def comment_visible() -> ColumnElement[bool]:
    return and_(Comment.deleted_at.is_(None), Comment.moderation_status == ModerationStatus.VISIBLE)
