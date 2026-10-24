"""Double opt-in email subscriptions to an author (MAIL-01, MAIL-02, MAIL-03)."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_token, new_token, unsubscribe_token
from app.models import (
    Article,
    EmailJob,
    EmailSubscription,
    SubscriptionStatus,
    User,
)
from app.services import mailer

logger = logging.getLogger(__name__)

INVALID_LINK = "This link is invalid or has expired. Please subscribe again."


def confirm_url(token: str) -> str:
    # The token travels in the #fragment, which browsers never send to servers,
    # so it cannot end up in web server or proxy logs.
    return f"{get_settings().public_base_url}/newsletter/confirm#token={token}"


def unsubscribe_url(subscription_id: uuid.UUID) -> str:
    token = unsubscribe_token(subscription_id)
    return f"{get_settings().public_base_url}/newsletter/unsubscribe#token={token}"


def request_subscription(db: Session, author_id: uuid.UUID, email: str) -> EmailMessage | None:
    """Start (or restart) a subscription; return the confirmation email to send, if any.

    The caller answers the same way whatever happens here and sends the email
    after the response (see `send_confirmation`), so neither the answer nor its
    timing reveals whether an address is already subscribed.
    """
    author = db.get(User, author_id)
    if author is None:
        raise AppError(404, "not_found", "Author not found")
    settings = get_settings()
    now = datetime.now(UTC)

    # Create the row if needed, then lock it: concurrent requests for the same
    # address queue up here instead of each sending a confirmation email.
    new_id = uuid.uuid4()
    db.execute(
        insert(EmailSubscription)
        .values(
            id=new_id,
            author_id=author_id,
            email_normalized=email,
            unsubscribe_token_hash=hash_token(unsubscribe_token(new_id)),
        )
        .on_conflict_do_nothing(constraint="uq_email_subscriptions_author_id")
    )
    subscription = db.execute(
        select(EmailSubscription)
        .where(
            EmailSubscription.author_id == author_id, EmailSubscription.email_normalized == email
        )
        .with_for_update()
    ).scalar_one()
    recently_sent = subscription.confirmation_sent_at is not None and (
        now - subscription.confirmation_sent_at
        < timedelta(minutes=settings.newsletter_resend_minutes)
    )
    if subscription.status == SubscriptionStatus.CONFIRMED or (
        subscription.status == SubscriptionStatus.PENDING and recently_sent
    ):
        # Already receiving emails, or a link went out moments ago: send nothing
        # (no inbox flooding, SEC-03) and reveal nothing.
        db.commit()
        return None

    token = new_token()
    subscription.status = SubscriptionStatus.PENDING
    subscription.confirm_token_hash = hash_token(token)
    subscription.token_expires_at = now + timedelta(hours=settings.newsletter_confirm_ttl_hours)
    subscription.confirmation_sent_at = now
    db.commit()

    # Only the author's @handle (letters, digits, underscores) goes into the email:
    # display names are free text and must not let anyone write to strangers.
    return mailer.build_message(
        to=email,
        subject="Confirm your Aporia subscription",
        body=(
            "Someone, hopefully you, asked to receive new essays by "
            f"@{author.handle} on Aporia at this address.\n\n"
            f"Confirm the subscription:\n{confirm_url(token)}\n\n"
            f"The link expires in {settings.newsletter_confirm_ttl_hours} hours. "
            "If this was not you, ignore this email: you will not hear from us again.\n"
        ),
    )


def send_confirmation(message: EmailMessage) -> None:
    """Runs after the response has been sent. On failure the visitor can ask again
    once NEWSLETTER_RESEND_MINUTES have passed; no address or token is logged."""
    try:
        mailer.send(message)
    except (mailer.TemporaryEmailError, mailer.PermanentEmailError) as exc:
        logger.warning("Confirmation email failed: %s", exc)


def confirm(db: Session, token: str) -> EmailSubscription:
    """Confirm with the emailed token. Confirming twice is harmless."""
    subscription = db.scalar(
        select(EmailSubscription).where(EmailSubscription.confirm_token_hash == hash_token(token))
    )
    if subscription is None:
        raise AppError(400, "invalid_token", INVALID_LINK)
    if subscription.status == SubscriptionStatus.CONFIRMED:
        return subscription
    if subscription.token_expires_at is None or subscription.token_expires_at < datetime.now(UTC):
        raise AppError(400, "invalid_token", INVALID_LINK)
    subscription.status = SubscriptionStatus.CONFIRMED
    subscription.confirmed_at = datetime.now(UTC)
    db.commit()
    return subscription


def unsubscribe(db: Session, token: str) -> EmailSubscription:
    """Stop all emails for this subscription. Works without signing in; safe to repeat."""
    subscription = db.scalar(
        select(EmailSubscription).where(
            EmailSubscription.unsubscribe_token_hash == hash_token(token)
        )
    )
    if subscription is None:
        raise AppError(400, "invalid_token", "This unsubscribe link is invalid.")
    subscription.status = SubscriptionStatus.UNSUBSCRIBED
    # An old confirmation link must not silently re-subscribe the address.
    subscription.confirm_token_hash = None
    subscription.token_expires_at = None
    db.commit()
    return subscription


def queue_new_article_emails(db: Session, article: Article) -> None:
    """Create one email job per confirmed subscriber of the author (MAIL-03).

    Called inside the transaction that publishes the article for the first
    time, so the jobs exist exactly when the publication does. The unique
    (article_id, subscription_id) key makes a repeated call harmless.
    """
    subscribers = select(EmailSubscription.id).where(
        EmailSubscription.author_id == article.author_id,
        EmailSubscription.status == SubscriptionStatus.CONFIRMED,
    )
    now = datetime.now(UTC)
    rows = [
        {"article_id": article.id, "subscription_id": sid, "next_retry_at": now}
        for sid in db.scalars(subscribers)
    ]
    if rows:
        db.execute(insert(EmailJob).values(rows).on_conflict_do_nothing())
