"""One definition of "the public may see this article", used by every public query.

Lists, search, tag counts and (later) feeds and recommendations all go through
this, so drafts, unpublished and deleted articles cannot leak into one of them.
"""

from sqlalchemy import ColumnElement, and_

from app.models import Article, ArticleStatus


def publicly_visible() -> ColumnElement[bool]:
    return and_(Article.status == ArticleStatus.PUBLISHED, Article.deleted_at.is_(None))
