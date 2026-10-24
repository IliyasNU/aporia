"""Sends queued "new essay" emails (MAIL-03, MAIL-04).

Guarantees and their limits (also in the README):
- At most one job per article and subscriber (database unique key).
- Each job is locked while it is processed (FOR UPDATE SKIP LOCKED), so two
  worker processes never send the same job at the same time.
- A job is marked "sent" only after the SMTP server accepted the message. If
  the worker dies between those two steps, the job is still "pending" and the
  email is sent again on the next run. Exactly-once delivery is impossible to
  guarantee with SMTP; Aporia guarantees at-least-once with duplicates only in
  that rare crash window.
"""

import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Article,
    EmailJob,
    EmailJobStatus,
    EmailSubscription,
    SubscriptionStatus,
)
from app.services import mailer
from app.services.newsletter import unsubscribe_url
from app.services.visibility import publicly_visible

logger = logging.getLogger(__name__)


def retry_delay(attempts: int) -> timedelta:
    """1, 5, 25, 125 ... minutes, capped at 6 hours."""
    return timedelta(minutes=min(5 ** (attempts - 1), 360))


def _new_article_message(job: EmailJob) -> mailer.EmailMessage:
    settings = get_settings()
    article = job.article
    author = article.author.display_name
    link = f"{settings.public_base_url}/articles/{article.slug}"
    stop = unsubscribe_url(job.subscription_id)
    summary = f"{article.summary}\n\n" if article.summary else ""
    return mailer.build_message(
        to=job.subscription.email_normalized,
        subject=f"New essay by {author}: {article.title}",
        body=(
            f"{author} published a new essay on Aporia:\n\n"
            f"{article.title}\n{summary}"
            f"Read it: {link}\n\n"
            f"--\nYou receive this because you subscribed to {author}'s essays.\n"
            f"Unsubscribe: {stop}\n"
        ),
        unsubscribe_url=stop,
    )


def _still_wanted(db: Session, job: EmailJob) -> bool:
    if job.subscription.status != SubscriptionStatus.CONFIRMED:
        return False
    return (
        db.scalar(select(Article.id).where(Article.id == job.article_id, publicly_visible()))
        is not None
    )


def process_one(db: Session) -> bool:
    """Send the next due job. Returns False when there is nothing to do."""
    settings = get_settings()
    now = datetime.now(UTC)
    job = db.scalar(
        select(EmailJob)
        .where(EmailJob.status == EmailJobStatus.PENDING, EmailJob.next_retry_at <= now)
        .order_by(EmailJob.next_retry_at, EmailJob.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return False

    if not _still_wanted(db, job):
        job.status = EmailJobStatus.CANCELLED
        db.commit()
        logger.info("Email job %s cancelled (unsubscribed or article not public)", job.id)
        return True

    job.attempts += 1
    try:
        mailer.send(_new_article_message(job))
    except mailer.PermanentEmailError as exc:
        job.status = EmailJobStatus.FAILED
        job.error_code = str(exc)
        logger.error("Email job %s failed permanently: %s", job.id, exc)
    except mailer.TemporaryEmailError as exc:
        job.error_code = str(exc)
        if job.attempts >= settings.worker_max_attempts:
            job.status = EmailJobStatus.FAILED
            logger.error("Email job %s gave up after %s attempts: %s", job.id, job.attempts, exc)
        else:
            job.next_retry_at = now + retry_delay(job.attempts)
            logger.warning(
                "Email job %s attempt %s failed, will retry: %s", job.id, job.attempts, exc
            )
    else:
        job.status = EmailJobStatus.SENT
        job.sent_at = datetime.now(UTC)
        job.error_code = None
        logger.info("Email job %s sent", job.id)
    db.commit()
    return True


def run_batch(db: Session) -> int:
    """Send up to WORKER_BATCH_SIZE due emails, pausing between them. Returns how many."""
    settings = get_settings()
    handled = 0
    while handled < settings.worker_batch_size and process_one(db):
        handled += 1
        time.sleep(settings.worker_send_delay_seconds)
    return handled


def clean_up(db: Session) -> None:
    """Data minimisation (SEC-06): drop finished jobs and abandoned pending subscriptions."""
    settings = get_settings()
    now = datetime.now(UTC)
    db.execute(
        delete(EmailJob).where(
            EmailJob.status != EmailJobStatus.PENDING,
            EmailJob.updated_at < now - timedelta(days=settings.email_job_retention_days),
        )
    )
    db.execute(
        delete(EmailSubscription).where(
            EmailSubscription.status == SubscriptionStatus.PENDING,
            EmailSubscription.token_expires_at < now - timedelta(days=7),
        )
    )
    db.commit()
