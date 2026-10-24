"""Manual procedures for administrators (SEC-06, SEC-07), run through `python -m app.cli`.

These permanently delete data, so they are commands for a person with server
access, never API endpoints.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Article, Comment, EmailSubscription, User


def delete_user(db: Session, email: str) -> str:
    """Delete an account and everything it owns.

    Foreign keys cascade: sessions, interests, follows, bookmarks, comments,
    reports, the user's articles, their email subscribers and any pending
    email jobs for those articles go too. So deleting an author never sends
    emails to their subscribers and leaves no personal data public.
    """
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise LookupError(f"No user with email {email}")
    handle = user.handle
    db.delete(user)
    db.commit()
    return handle


def delete_article(db: Session, article_id: uuid.UUID) -> str:
    """Remove an article for good (e.g. illegal content), with its comments and bookmarks."""
    article = db.get(Article, article_id)
    if article is None:
        raise LookupError(f"No article with id {article_id}")
    title = article.title
    db.delete(article)
    db.commit()
    return title


def delete_comment(db: Session, comment_id: uuid.UUID) -> None:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError(f"No comment with id {comment_id}")
    db.delete(comment)
    db.commit()


def delete_subscriber(db: Session, email: str) -> int:
    """Forget an email address in every newsletter subscription (a deletion request)."""
    result = db.execute(
        delete(EmailSubscription).where(EmailSubscription.email_normalized == email.strip().lower())
    )
    db.commit()
    return result.rowcount  # type: ignore[attr-defined]
