"""Double opt-in email subscriptions (MAIL-01, MAIL-02) and job creation (MAIL-03)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import EmailJob, EmailSubscription
from app.services.mailer import TemporaryEmailError
from tests.conftest import Outbox, link_token, me, publish, signed_in, write_article

API = "/api/v1"


@pytest.fixture
def author(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "author", "Simone Weil")


@pytest.fixture
def visitor(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()  # no account needed


def subscribe(client: TestClient, author: TestClient, email: str = "Fan@Example.com"):
    return client.post(
        f"{API}/authors/{me(author)['id']}/newsletter-subscriptions", json={"email": email}
    )


def subscriptions(db: Session) -> list[EmailSubscription]:
    return list(db.scalars(select(EmailSubscription)))


def confirmed_subscriber(
    visitor: TestClient, author: TestClient, outbox: Outbox, email: str = "fan@example.com"
) -> None:
    subscribe(visitor, author, email)
    token = link_token(outbox[-1], "confirm")
    assert visitor.post(f"{API}/newsletter/confirm", json={"token": token}).status_code == 200


# --- Subscribing --------------------------------------------------------------


def test_subscribe_creates_pending_subscription_and_sends_confirmation(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    response = subscribe(visitor, author, "  Fan@Example.COM ")

    assert response.status_code == 202
    [subscription] = subscriptions(db_session)
    assert subscription.status == "pending"
    assert subscription.email_normalized == "fan@example.com"
    [message] = outbox
    assert message["To"] == "fan@example.com"
    assert message["Subject"] == "Confirm your Aporia subscription"
    # Only the @handle, never the free-text display name, reaches strangers' inboxes.
    assert "@author" in message.get_content()
    assert "Simone Weil" not in message.get_content()
    token = link_token(message, "confirm")
    # Only a hash of the token is stored.
    assert subscription.confirm_token_hash != token
    assert token not in str(subscription.__dict__)


def test_answer_is_identical_whatever_the_address_state(
    visitor: TestClient, author: TestClient, outbox: Outbox
) -> None:
    new = subscribe(visitor, author, "new@example.com")
    confirmed_subscriber(visitor, author, outbox, "old@example.com")
    already = subscribe(visitor, author, "old@example.com")
    pending_again = subscribe(visitor, author, "new@example.com")

    assert new.status_code == already.status_code == pending_again.status_code == 202
    assert new.json() == already.json() == pending_again.json()


def test_repeated_requests_do_not_duplicate_or_flood(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    for _ in range(3):
        subscribe(visitor, author)

    assert len(subscriptions(db_session)) == 1
    assert len(outbox) == 1  # resend cooldown


def test_confirmation_is_resent_after_the_cooldown(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    subscribe(visitor, author)
    db_session.execute(
        update(EmailSubscription).values(
            confirmation_sent_at=datetime.now(UTC) - timedelta(minutes=11)
        )
    )

    subscribe(visitor, author)

    assert len(outbox) == 2
    # The first link no longer works: only the newest token is valid.
    old = link_token(outbox[0], "confirm")
    assert visitor.post(f"{API}/newsletter/confirm", json={"token": old}).status_code == 400


def test_already_confirmed_address_gets_no_new_email(
    visitor: TestClient, author: TestClient, outbox: Outbox
) -> None:
    confirmed_subscriber(visitor, author, outbox)

    subscribe(visitor, author)

    assert len(outbox) == 1


def test_smtp_failure_still_answers_202_and_allows_retry_after_cooldown(
    visitor: TestClient,
    author: TestClient,
    outbox: Outbox,
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    outbox.failure = TemporaryEmailError("smtp_unavailable")

    assert subscribe(visitor, author).status_code == 202
    assert "Confirmation email failed" in caplog.text
    assert "fan@example.com" not in caplog.text

    outbox.failure = None
    subscribe(visitor, author)
    assert outbox == []  # within the cooldown nothing is sent, failed or not
    db_session.execute(
        update(EmailSubscription).values(
            confirmation_sent_at=datetime.now(UTC) - timedelta(minutes=11)
        )
    )
    subscribe(visitor, author)
    assert len(outbox) == 1


@pytest.mark.parametrize("email", ["not-an-email", "", "a" * 250 + "@example.com"])
def test_invalid_email_is_rejected(visitor: TestClient, author: TestClient, email: str) -> None:
    assert subscribe(visitor, author, email).status_code == 422


def test_unknown_author_is_404(visitor: TestClient) -> None:
    response = visitor.post(
        f"{API}/authors/00000000-0000-0000-0000-000000000000/newsletter-subscriptions",
        json={"email": "fan@example.com"},
    )
    assert response.status_code == 404


def test_subscriptions_are_independent_of_accounts(
    author: TestClient, outbox: Outbox, make_client: Callable[[], TestClient]
) -> None:
    reader = signed_in(make_client, "reader")  # has an account with this email

    assert subscribe(reader, author, "reader@example.com").status_code == 202
    assert len(outbox) == 1


# --- Confirming ----------------------------------------------------------------


def test_confirm_activates_and_is_safe_to_repeat(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    subscribe(visitor, author)
    token = link_token(outbox[0], "confirm")

    first = visitor.post(f"{API}/newsletter/confirm", json={"token": token})
    second = visitor.post(f"{API}/newsletter/confirm", json={"token": token})

    assert first.status_code == second.status_code == 200
    assert first.json()["author"]["display_name"] == "Simone Weil"
    [subscription] = subscriptions(db_session)
    assert subscription.status == "confirmed"
    assert subscription.confirmed_at is not None


@pytest.mark.parametrize("token", ["wrong", "x" * 43])
def test_invalid_token_is_rejected(visitor: TestClient, token: str) -> None:
    response = visitor.post(f"{API}/newsletter/confirm", json={"token": token})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_token"


def test_expired_token_is_rejected(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    subscribe(visitor, author)
    db_session.execute(
        update(EmailSubscription).values(token_expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )

    response = visitor.post(
        f"{API}/newsletter/confirm", json={"token": link_token(outbox[0], "confirm")}
    )

    assert response.status_code == 400
    assert subscriptions(db_session)[0].status == "pending"


# --- Unsubscribing -------------------------------------------------------------


def test_unsubscribe_is_safe_to_repeat_and_kills_old_confirmation_links(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    subscribe(visitor, author)
    confirm_token = link_token(outbox[0], "confirm")
    visitor.post(f"{API}/newsletter/confirm", json={"token": confirm_token})
    publish(author, write_article(author)["id"])
    from app.worker.email_jobs import run_batch

    run_batch(db_session)
    unsubscribe_token = link_token(outbox[-1], "unsubscribe")

    first = visitor.post(f"{API}/newsletter/unsubscribe", json={"token": unsubscribe_token})
    second = visitor.post(f"{API}/newsletter/unsubscribe", json={"token": unsubscribe_token})

    assert first.status_code == second.status_code == 204
    assert subscriptions(db_session)[0].status == "unsubscribed"
    again = visitor.post(f"{API}/newsletter/confirm", json={"token": confirm_token})
    assert again.status_code == 400


def test_invalid_unsubscribe_token_is_rejected(visitor: TestClient) -> None:
    response = visitor.post(f"{API}/newsletter/unsubscribe", json={"token": "forged"})

    assert response.status_code == 400


def test_resubscribing_after_unsubscribe_needs_a_new_confirmation(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    from app.core.security import unsubscribe_token

    confirmed_subscriber(visitor, author, outbox)
    [subscription] = subscriptions(db_session)
    visitor.post(
        f"{API}/newsletter/unsubscribe", json={"token": unsubscribe_token(subscription.id)}
    )

    subscribe(visitor, author)

    assert len(outbox) == 2
    assert subscriptions(db_session)[0].status == "pending"


# --- Jobs on publish (MAIL-03) -----------------------------------------------------


def jobs(db: Session) -> list[EmailJob]:
    return list(db.scalars(select(EmailJob)))


def test_first_publication_queues_one_job_per_confirmed_subscriber(
    visitor: TestClient,
    author: TestClient,
    outbox: Outbox,
    db_session: Session,
    make_client: Callable[[], TestClient],
) -> None:
    confirmed_subscriber(visitor, author, outbox, "one@example.com")
    confirmed_subscriber(visitor, author, outbox, "two@example.com")
    subscribe(visitor, author, "pending@example.com")
    other = signed_in(make_client, "other")
    confirmed_subscriber(visitor, other, outbox, "other-fan@example.com")

    article = publish(author, write_article(author)["id"])

    queued = jobs(db_session)
    assert len(queued) == 2
    assert {str(j.article_id) for j in queued} == {article["id"]}
    assert all(j.status == "pending" for j in queued)


def test_edits_and_republishing_never_queue_again(
    visitor: TestClient, author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    confirmed_subscriber(visitor, author, outbox)
    article = publish(author, write_article(author)["id"])

    author.patch(f"{API}/articles/{article['id']}", json={"title": "Revised"})
    author.post(f"{API}/articles/{article['id']}/unpublish")
    publish(author, article["id"])
    publish(author, article["id"])

    assert db_session.scalar(select(func.count()).select_from(EmailJob)) == 1


def test_publishing_without_subscribers_queues_nothing(
    author: TestClient, db_session: Session
) -> None:
    publish(author, write_article(author)["id"])

    assert jobs(db_session) == []
