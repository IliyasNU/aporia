"""Manual procedures for administrators (SEC-06, SEC-07), run through `python -m app.cli`.

These permanently delete data, so they are commands for a person with server
access, never API endpoints. Every deletion also closes the open reports of
what it removes, so the admin queue never fills with reports nobody can act on.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import (
    Article,
    Comment,
    EmailJob,
    EmailJobStatus,
    EmailSubscription,
    ReportTarget,
    SubscriptionStatus,
    User,
)
from app.services.moderation import close_reports


def _close_reports_for_articles(db: Session, article_ids: list[uuid.UUID]) -> None:
    """Close reports on these articles and on every comment under them."""
    close_reports(db, ReportTarget.ARTICLE, article_ids)
    if article_ids:
        comments = db.scalars(select(Comment.id).where(Comment.article_id.in_(article_ids)))
        close_reports(db, ReportTarget.COMMENT, list(comments))


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
    _close_reports_for_articles(
        db, list(db.scalars(select(Article.id).where(Article.author_id == user.id)))
    )
    close_reports(
        db,
        ReportTarget.COMMENT,
        list(db.scalars(select(Comment.id).where(Comment.user_id == user.id))),
    )
    db.delete(user)
    db.commit()
    return handle


def delete_article(db: Session, article_id: uuid.UUID) -> str:
    """Remove an article for good (e.g. illegal content), with its comments and bookmarks."""
    article = db.get(Article, article_id)
    if article is None:
        raise LookupError(f"No article with id {article_id}")
    title = article.title
    _close_reports_for_articles(db, [article_id])
    db.delete(article)
    db.commit()
    return title


def delete_comment(db: Session, comment_id: uuid.UUID) -> None:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise LookupError(f"No comment with id {comment_id}")
    close_reports(db, ReportTarget.COMMENT, [comment_id])
    db.delete(comment)
    db.commit()


def delete_subscriber(db: Session, email: str) -> int:
    """Forget an email address in every newsletter subscription (a deletion request)."""
    result = db.execute(
        delete(EmailSubscription).where(EmailSubscription.email_normalized == email.strip().lower())
    )
    db.commit()
    return result.rowcount  # type: ignore[attr-defined]


def requeue_failed_emails(db: Session) -> int:
    """Give failed email jobs a fresh start, e.g. after fixing SMTP credentials.

    Only jobs whose subscriber is still confirmed are requeued; the worker
    re-checks that the essay is still public before sending.
    """
    confirmed = select(EmailSubscription.id).where(
        EmailSubscription.status == SubscriptionStatus.CONFIRMED
    )
    result = db.execute(
        update(EmailJob)
        .where(EmailJob.status == EmailJobStatus.FAILED, EmailJob.subscription_id.in_(confirmed))
        .values(
            status=EmailJobStatus.PENDING,
            attempts=0,
            error_code=None,
            next_retry_at=datetime.now(UTC),
        )
    )
    db.commit()
    return result.rowcount  # type: ignore[attr-defined]


def purge_deleted_content(db: Session, older_than: datetime) -> None:
    """Hard-delete essays and comments that were soft-deleted before `older_than`,
    and subscriptions unsubscribed before then (SEC-06). Does not commit."""
    old_articles = list(db.scalars(select(Article.id).where(Article.deleted_at < older_than)))
    _close_reports_for_articles(db, old_articles)
    if old_articles:
        db.execute(delete(Article).where(Article.id.in_(old_articles)))
    old_comments = list(db.scalars(select(Comment.id).where(Comment.deleted_at < older_than)))
    close_reports(db, ReportTarget.COMMENT, old_comments)
    if old_comments:
        db.execute(delete(Comment).where(Comment.id.in_(old_comments)))
    db.execute(
        delete(EmailSubscription).where(
            EmailSubscription.status == SubscriptionStatus.UNSUBSCRIBED,
            EmailSubscription.updated_at < older_than,
        )
    )
