"""The email worker: sending, retries, cancellation, cleanup (MAIL-03, MAIL-04)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import unsubscribe_token
from app.models import EmailJob, EmailSubscription
from app.services.mailer import PermanentEmailError, TemporaryEmailError, build_message
from app.services.newsletter import unsubscribe
from app.worker.email_jobs import clean_up, process_one, retry_delay, run_batch
from tests.conftest import Outbox, link_token, me, publish, signed_in, write_article

API = "/api/v1"


@pytest.fixture
def author(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "author", "Simone Weil")


@pytest.fixture
def queued(
    author: TestClient, make_client: Callable[[], TestClient], outbox: Outbox
) -> dict[str, object]:
    """One confirmed subscriber and one freshly published article (so one queued job)."""
    visitor = make_client()
    visitor.post(
        f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
        json={"email": "fan@example.com"},
    )
    visitor.post(f"{API}/newsletter/confirm", json={"token": link_token(outbox[0], "confirm")})
    outbox.clear()
    return publish(
        author,
        write_article(author, title="Gravity and Grace", summary="On attention.")["id"],
    )


def job(db: Session) -> EmailJob:
    found = db.scalar(select(EmailJob))
    assert found is not None
    db.refresh(found)
    return found


@pytest.fixture(autouse=True)
def no_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "worker_send_delay_seconds", 0)


def test_worker_sends_the_email_with_link_and_unsubscribe(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    assert run_batch(db_session) == 1

    [message] = outbox
    assert message["To"] == "fan@example.com"
    assert message["Subject"] == "New essay by Simone Weil: Gravity and Grace"
    body = message.get_content()
    assert f"/articles/{queued['slug']}" in body
    assert "On attention." in body
    token = link_token(message, "unsubscribe")
    assert message["List-Unsubscribe"].endswith(f"#token={token}>")
    sent = job(db_session)
    assert (sent.status, sent.attempts, sent.sent_at is not None) == ("sent", 1, True)


def test_running_again_sends_nothing_more(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    run_batch(db_session)
    run_batch(db_session)

    assert len(outbox) == 1


def test_temporary_failure_is_retried_later(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    outbox.failure = TemporaryEmailError("smtp_unavailable")

    process_one(db_session)

    failed = job(db_session)
    assert (failed.status, failed.attempts, failed.error_code) == (
        "pending",
        1,
        "smtp_unavailable",
    )
    assert failed.next_retry_at > datetime.now(UTC)
    assert process_one(db_session) is False  # not due yet

    outbox.failure = None
    db_session.execute(update(EmailJob).values(next_retry_at=datetime.now(UTC)))
    process_one(db_session)
    assert job(db_session).status == "sent"
    assert len(outbox) == 1


def test_gives_up_after_max_attempts(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    from app.core.config import get_settings

    outbox.failure = TemporaryEmailError("smtp_unavailable")
    for _ in range(get_settings().worker_max_attempts):
        db_session.execute(update(EmailJob).values(next_retry_at=datetime.now(UTC)))
        process_one(db_session)

    final = job(db_session)
    assert (final.status, final.attempts) == ("failed", get_settings().worker_max_attempts)


def test_permanent_failure_is_recorded_without_retry(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    outbox.failure = PermanentEmailError("smtp_550")

    process_one(db_session)

    final = job(db_session)
    assert (final.status, final.error_code) == ("failed", "smtp_550")


def test_unsubscribing_before_sending_cancels_the_job(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    subscription = db_session.scalar(select(EmailSubscription))
    assert subscription is not None
    unsubscribe(db_session, unsubscribe_token(subscription.id))
    run_batch(db_session)

    assert outbox == []
    assert job(db_session).status == "cancelled"


def test_article_taken_down_before_sending_cancels_the_job(
    queued: dict[str, object], author: TestClient, outbox: Outbox, db_session: Session
) -> None:
    author.post(f"{API}/articles/{queued['id']}/unpublish")

    run_batch(db_session)

    assert outbox == []
    assert job(db_session).status == "cancelled"


def test_publication_succeeds_even_if_smtp_is_down(
    author: TestClient, outbox: Outbox, make_client: Callable[[], TestClient]
) -> None:
    outbox.failure = TemporaryEmailError("smtp_unavailable")

    response = author.post(f"{API}/articles/{write_article(author)['id']}/publish")

    assert response.status_code == 200


def test_worker_logs_contain_no_addresses_or_tokens(
    queued: dict[str, object],
    outbox: Outbox,
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG")
    outbox.failure = TemporaryEmailError("smtp_unavailable")
    process_one(db_session)
    outbox.failure = None
    db_session.execute(update(EmailJob).values(next_retry_at=datetime.now(UTC)))
    process_one(db_session)

    assert "Email job" in caplog.text
    assert "fan@example.com" not in caplog.text
    assert link_token(outbox[0], "unsubscribe") not in caplog.text


def test_headers_cannot_be_injected_through_titles() -> None:
    message = build_message(
        to="fan@example.com", subject="Title\r\nBcc: victim@example.com", body="x"
    )

    assert message["Bcc"] is None
    assert message["Subject"] == "Title Bcc: victim@example.com"


def test_retry_delays_grow_and_are_capped() -> None:
    assert [retry_delay(n) for n in (1, 2, 3)] == [
        timedelta(minutes=1),
        timedelta(minutes=5),
        timedelta(minutes=25),
    ]
    assert retry_delay(10) == timedelta(hours=6)


def test_cleanup_removes_old_finished_jobs_and_stale_pending_subscriptions(
    queued: dict[str, object], outbox: Outbox, db_session: Session
) -> None:
    run_batch(db_session)
    long_ago = datetime.now(UTC) - timedelta(days=365)
    db_session.execute(update(EmailJob).values(updated_at=long_ago))
    db_session.add(
        EmailSubscription(
            author_id=db_session.scalar(select(EmailSubscription.author_id)),
            email_normalized="never-confirmed@example.com",
            unsubscribe_token_hash="x" * 64,
            token_expires_at=long_ago,
        )
    )
    db_session.flush()

    clean_up(db_session)

    assert db_session.scalar(select(EmailJob)) is None
    remaining = [s.email_normalized for s in db_session.scalars(select(EmailSubscription))]
    assert remaining == ["fan@example.com"]


def test_worker_healthcheck_follows_the_heartbeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    from app.core.config import get_settings
    from app.worker.healthcheck import is_healthy

    heartbeat = tmp_path / "heartbeat"
    monkeypatch.setattr(get_settings(), "worker_heartbeat_file", str(heartbeat))

    assert is_healthy() is False  # worker never ran
    heartbeat.touch()
    assert is_healthy() is True
    stale = time.time() + get_settings().worker_heartbeat_max_age_seconds + 1
    assert is_healthy(now=stale) is False
