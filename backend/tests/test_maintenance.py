"""Manual admin procedures (SEC-06, SEC-07), demo data and session cleanup."""

from collections.abc import Callable, Iterator
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.cli import main as cli
from app.models import (
    Article,
    Comment,
    EmailJob,
    EmailSubscription,
    User,
    UserSession,
)
from app.worker.email_jobs import clean_up, run_batch
from tests.conftest import Outbox, link_token, me, publish, signed_in, write_article

API = "/api/v1"


@pytest.fixture(autouse=True)
def cli_uses_test_db(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr("app.cli.SessionLocal", lambda: nullcontext(db_session))
    yield


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_delete_user_removes_everything_and_sends_no_emails(
    make_client: Callable[[], TestClient], outbox: Outbox, db_session: Session
) -> None:
    author = signed_in(make_client, "author")
    fan = make_client()
    fan.post(
        f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
        json={"email": "fan@example.com"},
    )
    fan.post(f"{API}/newsletter/confirm", json={"token": link_token(outbox[0], "confirm")})
    article = publish(author, write_article(author)["id"])  # queues an email job
    reader = signed_in(make_client, "reader")
    reader.post(f"{API}/articles/{article['id']}/comments", json={"text": "Hi"})
    outbox.clear()

    assert cli(["delete-user", "author@example.com"]) == 0

    assert db_session.scalar(select(User).where(User.handle == "author")) is None
    assert count(db_session, Article) == 0
    assert count(db_session, Comment) == 0
    assert count(db_session, EmailSubscription) == 0
    assert count(db_session, EmailJob) == 0
    run_batch(db_session)
    assert outbox == []  # nobody is emailed about a deleted author
    assert reader.get(f"{API}/auth/me").status_code == 200  # other accounts untouched


def test_delete_article_and_comment(
    make_client: Callable[[], TestClient], db_session: Session
) -> None:
    author = signed_in(make_client, "author")
    article = publish(author, write_article(author)["id"])
    comment = author.post(f"{API}/articles/{article['id']}/comments", json={"text": "First"}).json()

    assert cli(["delete-comment", comment["id"]]) == 0
    assert count(db_session, Comment) == 0
    assert cli(["delete-article", article["id"]]) == 0
    assert count(db_session, Article) == 0
    assert cli(["delete-article", article["id"]]) == 1  # already gone


def test_delete_subscriber_forgets_the_address_everywhere(
    make_client: Callable[[], TestClient], outbox: Outbox, db_session: Session
) -> None:
    for handle in ("one", "two"):
        author = signed_in(make_client, handle)
        make_client().post(
            f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
            json={"email": "fan@example.com"},
        )

    assert cli(["delete-subscriber", "FAN@example.com"]) == 0

    assert count(db_session, EmailSubscription) == 0


def test_seed_demo_creates_labelled_data_once(
    db_session: Session, capsys: pytest.CaptureFixture[str], make_client: Callable[[], TestClient]
) -> None:
    assert cli(["seed-demo"]) == 0
    assert cli(["seed-demo"]) == 0

    out = capsys.readouterr().out
    assert "Demo data already exists" in out
    users = list(db_session.scalars(select(User)))
    assert all(u.handle.startswith("demo_") and u.display_name.startswith("Demo") for u in users)
    articles = list(db_session.scalars(select(Article)))
    assert len(articles) == 6
    assert all(a.title.startswith("Demo: ") and "Demo content" in a.body_markdown for a in articles)
    feed = make_client().get(f"{API}/feed/recommended").json()
    assert feed["total"] == 6


def test_seed_demo_refuses_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "app_env", "production")

    assert cli(["seed-demo"]) == 1


def test_cleanup_removes_ended_sessions(
    make_client: Callable[[], TestClient], db_session: Session
) -> None:
    active = signed_in(make_client, "active")
    gone = signed_in(make_client, "gone")
    gone.post(f"{API}/auth/logout")
    db_session.execute(
        update(UserSession)
        .where(UserSession.revoked_at.is_not(None))
        .values(revoked_at=datetime.now(UTC) - timedelta(days=2))
    )

    clean_up(db_session)

    assert count(db_session, UserSession) == 1
    assert active.get(f"{API}/auth/me").status_code == 200
