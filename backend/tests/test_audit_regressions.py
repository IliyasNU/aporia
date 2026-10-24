"""Regression tests for the findings of the independent v1.0 audit.

Each test names the finding it covers; together they make sure the fixed
behaviour stays fixed.
"""

import smtplib
from collections.abc import Callable
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.cli import main as cli
from app.core.config import get_settings
from app.db.session import engine
from app.models import Article, EmailJob, EmailSubscription, Report, UserRole
from app.services import mailer
from app.services.mailer import PermanentEmailError, TemporaryEmailError, build_message
from app.services.moderation import set_role
from app.worker.email_jobs import clean_up, run_batch
from tests.conftest import Outbox, link_token, me, publish, signed_in, write_article
from tests.test_catalog import count_queries

API = "/api/v1"


# --- 1. No SQL parameters in errors or logs; NUL characters give 422 -----------


def test_database_errors_never_reach_logs_with_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fastapi import FastAPI

    from app.core.errors import register_error_handlers

    assert engine.hide_parameters is True
    app = FastAPI()
    register_error_handlers(app)

    secret = "@".join(["secret", "example.com"])  # like user input: not in any source line

    @app.get("/boom")
    def boom() -> None:
        with engine.connect() as connection:
            connection.execute(text("SELECT CAST(:v AS integer)"), {"v": secret})

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert "secret@example.com" not in response.text
    assert "Database error InvalidTextRepresentation (sqlstate 22P02" in caplog.text
    assert "secret@example.com" not in caplog.text


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        (
            "POST",
            "/auth/register",
            {
                "email": "a@example.com",
                "password": "long enough",
                "handle": "nul_user",
                "display_name": "Nul \x00 Name",
            },
        ),
        ("GET", "/articles?q=%00", None),
        ("GET", "/authors/%00", None),
        ("POST", "/auth/login", {"email": "a@example.com", "password": "x\x00"}),
    ],
)
def test_nul_characters_are_rejected_with_422(
    client: TestClient, method: str, path: str, body: object, caplog: pytest.LogCaptureFixture
) -> None:
    response = client.request(method, API + path, json=body)

    assert response.status_code == 422
    assert "Traceback" not in caplog.text


def test_nul_in_comment_text_is_rejected(make_client: Callable[[], TestClient]) -> None:
    author = signed_in(make_client, "author")
    article = publish(author, write_article(author)["id"])

    response = author.post(f"{API}/articles/{article['id']}/comments", json={"text": "a\x00b"})

    assert response.status_code == 422


# --- 2 and 14. Reports never get stuck; admins see what was reported ------------


@pytest.fixture
def admin(make_client: Callable[[], TestClient], db_session: Session) -> TestClient:
    client = signed_in(make_client, "admin")
    set_role(db_session, "admin@example.com", UserRole.ADMIN)
    return client


@pytest.fixture
def reported(make_client: Callable[[], TestClient]) -> dict[str, object]:
    author = signed_in(make_client, "author")
    article = publish(author, write_article(author, title="Reported essay")["id"])
    reader = signed_in(make_client, "reader")
    comment = reader.post(
        f"{API}/articles/{article['id']}/comments", json={"text": "A reported comment"}
    ).json()
    for target_type, target_id in (("article", article["id"]), ("comment", comment["id"])):
        reader.post(
            f"{API}/reports",
            json={"target_type": target_type, "target_id": target_id, "reason": "Spam"},
        )
    return {"article": article, "comment": comment}


def test_admin_report_list_shows_the_reported_content(
    admin: TestClient, reported: dict[str, object]
) -> None:
    reports = admin.get(f"{API}/admin/reports").json()

    targets = {r["target_type"]: r["target"] for r in reports}
    assert targets["article"]["title"] == "Reported essay"
    assert targets["article"]["url"] == "/articles/reported-essay"
    assert targets["comment"]["excerpt"] == "A reported comment"
    assert targets["comment"]["url"] == "/articles/reported-essay"
    assert admin.get(f"{API}/admin/reports", params={"page": 2}).json() == []


@pytest.mark.usefixtures("reported")
def test_permanent_deletion_closes_its_reports(
    admin: TestClient,
    reported: dict[str, object],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.cli.SessionLocal", lambda: nullcontext(db_session))

    assert cli(["delete-article", reported["article"]["id"]]) == 0  # type: ignore[index]

    # The comment went with the article, so both reports are closed.
    assert admin.get(f"{API}/admin/reports").json() == []
    assert db_session.scalar(select(func.count()).select_from(Report)) == 2


def test_moderating_a_vanished_target_still_closes_its_reports(
    admin: TestClient, reported: dict[str, object], db_session: Session
) -> None:
    article_id = reported["article"]["id"]  # type: ignore[index]
    db_session.execute(text("DELETE FROM articles WHERE id = :id"), {"id": article_id})

    response = admin.post(
        f"{API}/admin/moderate",
        json={"target_type": "article", "target_id": article_id, "action": "hide"},
    )

    assert response.status_code == 404
    assert [r["target_type"] for r in admin.get(f"{API}/admin/reports").json()] == ["comment"]


# --- 3. Account-level SMTP errors are temporary; the worker stops the batch -----


class FailingSMTP:
    """Stands in for smtplib.SMTP and fails at a chosen step."""

    error: Exception

    def __init__(self, *args: object, **kwargs: object) -> None: ...
    def __enter__(self) -> "FailingSMTP":
        return self

    def __exit__(self, *args: object) -> None: ...
    def starttls(self) -> None: ...
    def login(self, *args: object) -> None: ...
    def send_message(self, message: object) -> None:
        raise self.error


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), TemporaryEmailError),
        (smtplib.SMTPSenderRefused(550, b"daily quota exceeded", "a@b"), TemporaryEmailError),
        (smtplib.SMTPRecipientsRefused({"x@y": (550, b"no such user")}), PermanentEmailError),
        (smtplib.SMTPDataError(554, b"message rejected"), PermanentEmailError),
        (smtplib.SMTPDataError(451, b"try later"), TemporaryEmailError),
        (ConnectionRefusedError(), TemporaryEmailError),
    ],
)
def test_smtp_errors_are_classified(
    monkeypatch: pytest.MonkeyPatch, error: Exception, expected: type[Exception]
) -> None:
    FailingSMTP.error = error
    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)

    with pytest.raises(expected):
        mailer.send(build_message(to="a@example.com", subject="s", body="b"))


@pytest.fixture
def three_queued_jobs(make_client: Callable[[], TestClient], outbox: Outbox) -> None:
    author = signed_in(make_client, "author")
    for n in range(3):
        visitor = make_client()
        visitor.post(
            f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
            json={"email": f"fan{n}@example.com"},
        )
        visitor.post(f"{API}/newsletter/confirm", json={"token": link_token(outbox[-1], "confirm")})
    outbox.clear()
    publish(author, write_article(author)["id"])


@pytest.mark.usefixtures("three_queued_jobs")
def test_an_smtp_outage_costs_one_attempt_not_every_job(
    outbox: Outbox, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "worker_send_delay_seconds", 0)
    outbox.failure = TemporaryEmailError("smtp_535")

    assert run_batch(db_session) == 1

    attempts = sorted(db_session.scalars(select(EmailJob.attempts)))
    assert attempts == [0, 0, 1]


@pytest.mark.usefixtures("three_queued_jobs")
def test_failed_emails_can_be_requeued(
    outbox: Outbox, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "worker_send_delay_seconds", 0)
    monkeypatch.setattr("app.cli.SessionLocal", lambda: nullcontext(db_session))
    db_session.execute(update(EmailJob).values(status="failed", attempts=5, error_code="smtp_535"))

    assert cli(["requeue-failed-emails"]) == 0
    run_batch(db_session)

    assert len(outbox) == 3
    assert set(db_session.scalars(select(EmailJob.status))) == {"sent"}


# --- 4. A published essay cannot be emptied ------------------------------------


def test_published_essay_cannot_be_emptied_but_a_draft_can(
    make_client: Callable[[], TestClient],
) -> None:
    author = signed_in(make_client, "author")
    published = publish(author, write_article(author)["id"])
    draft = write_article(author, title="Draft")

    emptied = author.patch(f"{API}/articles/{published['id']}", json={"body_markdown": "  "})

    assert emptied.status_code == 422
    assert emptied.json()["error"]["code"] == "empty_body"
    assert (
        author.patch(f"{API}/articles/{draft['id']}", json={"body_markdown": ""}).status_code == 200
    )


# --- 5. Website length is checked after normalisation --------------------------


def test_website_that_grows_when_normalised_gets_422(make_client: Callable[[], TestClient]) -> None:
    user = signed_in(make_client, "user")

    response = user.patch(f"{API}/me/profile", json={"website": "http://ex.com/" + "é" * 90})

    assert response.status_code == 422


# --- 6. List-Unsubscribe stays readable on the wire -------------------------------


def test_list_unsubscribe_header_is_not_encoded() -> None:
    url = "http://localhost:8080/newsletter/unsubscribe#token=" + "a" * 64
    message = build_message(
        to="a@example.com", subject="Ünïcode subject", body="b", unsubscribe_url=url
    )

    raw = bytes(message).decode()

    assert f"List-Unsubscribe: <{url}>" in raw
    assert "=?utf-8?q?=3Chttp" not in raw


# --- 9. Followed authors load without N+1 --------------------------------------


def test_following_list_uses_a_fixed_number_of_queries(
    make_client: Callable[[], TestClient],
) -> None:
    reader = signed_in(make_client, "reader")
    first = signed_in(make_client, "first")
    reader.post(f"{API}/authors/{me(first)['id']}/follow")
    with count_queries() as few:
        reader.get(f"{API}/me/following")

    for name in ("second", "third", "fourth", "fifth"):
        reader.post(f"{API}/authors/{me(signed_in(make_client, name))['id']}/follow")
    with count_queries() as many:
        assert len(reader.get(f"{API}/me/following").json()) == 5

    assert len(many) == len(few)


# --- 11. Swagger UI can be switched off ----------------------------------------


def test_api_docs_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.main import create_app

    monkeypatch.setattr(get_settings(), "api_docs_enabled", False)
    without_docs = TestClient(create_app())
    monkeypatch.setattr(get_settings(), "api_docs_enabled", True)
    with_docs = TestClient(create_app())

    assert without_docs.get(f"{API}/docs").status_code == 404
    page = with_docs.get(f"{API}/docs")
    assert page.status_code == 200
    assert "swagger-ui-dist@5.33.1" in page.text  # an exact, pinned version
    assert without_docs.get(f"{API}/openapi.json").status_code == 200


# --- 16. Deleted content is purged after the retention period ------------------


def test_cleanup_purges_old_deleted_content(
    make_client: Callable[[], TestClient], db_session: Session, outbox: Outbox
) -> None:
    author = signed_in(make_client, "author")
    old = publish(author, write_article(author, title="Old")["id"])
    recent = publish(author, write_article(author, title="Recent")["id"])
    author.delete(f"{API}/articles/{old['id']}")
    author.delete(f"{API}/articles/{recent['id']}")
    long_ago = datetime.now(UTC) - timedelta(days=31)
    db_session.execute(update(Article).where(Article.title == "Old").values(deleted_at=long_ago))
    visitor = make_client()
    visitor.post(
        f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
        json={"email": "gone@example.com"},
    )
    db_session.execute(update(EmailSubscription).values(status="unsubscribed", updated_at=long_ago))

    clean_up(db_session)

    assert [a.title for a in db_session.scalars(select(Article))] == ["Recent"]
    assert db_session.scalar(select(func.count()).select_from(EmailSubscription)) == 0
