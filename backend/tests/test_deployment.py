"""What a hosting platform relies on: platform-style settings, running without an SMTP
account, and the Render Blueprint (render.yaml, deploy/)."""

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import LOCAL_ORIGINS, Settings, get_settings
from app.models import EmailJob, EmailJobStatus, EmailSubscription
from app.worker.email_jobs import run_batch
from tests.conftest import Outbox, link_token, me, publish, signed_in, write_article

API = "/api/v1"
BLUEPRINT = Path(__file__).resolve().parents[2] / "render.yaml"
# Read by deploy/start.sh or by Render itself, not by Settings.
START_SCRIPT_VARIABLES = {"PORT", "REAL_IP_HEADER", "ADMIN_EMAIL"}


# --- Settings -----------------------------------------------------------------


@pytest.mark.parametrize(
    "given",
    [
        "postgres://aporia:secret@db.internal/aporia",
        "postgresql://aporia:secret@db.internal/aporia",
        "postgresql+psycopg://aporia:secret@db.internal/aporia",
    ],
)
def test_platform_database_urls_get_the_psycopg_driver(
    given: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", given)

    url = Settings().database_url.get_secret_value()

    assert url == "postgresql+psycopg://aporia:secret@db.internal/aporia"


def test_blank_variables_fall_back_to_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SMTP_PORT", "SMTP_USERNAME", "TRUSTED_ORIGINS", "MAIL_FROM"):
        monkeypatch.setenv(name, "")

    settings = Settings()

    assert settings.smtp_port == 1025
    assert settings.smtp_username is None
    assert settings.trusted_origins == LOCAL_ORIGINS
    assert settings.mail_from == Settings.model_fields["mail_from"].default


# --- Running without an SMTP account -------------------------------------------


@pytest.fixture
def author(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "author", "Simone Weil")


def test_subscribing_answers_503_while_email_is_off(
    author: TestClient,
    make_client: Callable[[], TestClient],
    outbox: Outbox,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "email_enabled", False)

    response = make_client().post(
        f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
        json={"email": "fan@example.com"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "email_unavailable"
    assert db_session.scalar(select(EmailSubscription)) is None
    assert outbox == []


def test_worker_keeps_queued_emails_while_email_is_off(
    author: TestClient,
    make_client: Callable[[], TestClient],
    outbox: Outbox,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visitor = make_client()
    visitor.post(
        f"{API}/authors/{me(author)['id']}/newsletter-subscriptions",
        json={"email": "fan@example.com"},
    )
    visitor.post(f"{API}/newsletter/confirm", json={"token": link_token(outbox[0], "confirm")})
    outbox.clear()
    publish(author, write_article(author, title="Gravity and Grace")["id"])
    monkeypatch.setattr(get_settings(), "email_enabled", False)

    assert run_batch(db_session) == 0

    job = db_session.scalar(select(EmailJob))
    assert job is not None
    assert (job.status, job.attempts) == (EmailJobStatus.PENDING, 0)
    assert outbox == []


# --- render.yaml ------------------------------------------------------------------


def test_render_blueprint_only_sets_variables_the_app_reads() -> None:
    keys = set(re.findall(r"^\s*- key: (\w+)$", BLUEPRINT.read_text(), flags=re.MULTILINE))
    known = {name.upper() for name in Settings.model_fields} | START_SCRIPT_VARIABLES

    assert keys, "no environment variables found in render.yaml"
    assert keys <= known, f"unknown variables (typos?): {keys - known}"


def test_render_blueprint_asks_for_free_plans_only() -> None:
    # Render picks a paid plan for any service or database that does not name one.
    text = BLUEPRINT.read_text()
    resources = re.findall(r"^  - (?:type|name): ", text, flags=re.MULTILINE)
    plans = re.findall(r"^    plan: (\S+)$", text, flags=re.MULTILINE)

    assert len(resources) == 2  # the web service and its database
    assert plans == ["free"] * len(resources)
