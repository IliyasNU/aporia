"""Registration, login, logout and sessions (AUTH-01, AUTH-02)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from argon2 import PasswordHasher
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, set_session_cookie
from app.core.config import Settings
from app.core.security import hash_session_token
from app.models import User, UserSession
from tests.conftest import DEFAULT_PASSWORD, register

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def login(client: TestClient, email: str = "reader@example.com", password: str = DEFAULT_PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


# --- Registration -----------------------------------------------------------


def test_register_creates_account_and_signs_in(client: TestClient) -> None:
    response = client.post(
        REGISTER,
        json={
            "email": "Reader@Example.COM",
            "password": DEFAULT_PASSWORD,
            "handle": "Socrates_Fan",
            "display_name": "  Socrates Fan ",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "reader@example.com"
    assert body["handle"] == "socrates_fan"
    assert body["display_name"] == "Socrates Fan"
    assert body["role"] == "user"
    assert body["interests"] == []
    assert "password" not in response.text
    assert "password_hash" not in body

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert client.get(ME).json()["handle"] == "socrates_fan"


def test_password_is_stored_as_argon2id_hash(client: TestClient, db_session: Session) -> None:
    register(client)

    stored = db_session.scalar(select(User.password_hash))
    assert stored is not None
    assert stored.startswith("$argon2id$")
    assert DEFAULT_PASSWORD not in stored


def test_register_rejects_duplicate_email_case_insensitively(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="reader@example.com", handle="first")

    response = make_client().post(
        REGISTER,
        json={
            "email": "READER@example.com",
            "password": DEFAULT_PASSWORD,
            "handle": "second",
            "display_name": "Second",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_register_rejects_duplicate_handle_case_insensitively(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="first@example.com", handle="kant")

    response = make_client().post(
        REGISTER,
        json={
            "email": "second@example.com",
            "password": DEFAULT_PASSWORD,
            "handle": "KANT",
            "display_name": "Second",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "handle_taken"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("email", "a" * 250 + "@example.com"),
        ("password", "short"),
        ("password", "x" * 129),
        ("handle", "ab"),
        ("handle", "has space"),
        ("handle", "dash-not-allowed"),
        ("handle", "a" * 31),
        ("display_name", "   "),
        ("display_name", "x" * 81),
    ],
)
def test_register_validates_input(client: TestClient, field: str, value: str) -> None:
    payload = {
        "email": "reader@example.com",
        "password": DEFAULT_PASSWORD,
        "handle": "reader",
        "display_name": "Reader",
        field: value,
    }

    response = client.post(REGISTER, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["loc"] == ["body", field]
    assert "set-cookie" not in response.headers


def test_validation_error_does_not_echo_password(client: TestClient) -> None:
    response = client.post(
        REGISTER,
        json={"email": "bad", "password": "secret1", "handle": "x", "display_name": "X"},
    )

    assert response.status_code == 422
    assert "secret1" not in response.text


# --- Login ------------------------------------------------------------------


def test_login_with_valid_credentials_starts_session(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client)
    browser = make_client()

    response = login(browser, email="READER@example.com")

    assert response.status_code == 200
    assert response.json()["handle"] == "reader"
    assert browser.get(ME).status_code == 200


def test_wrong_password_and_unknown_email_get_identical_answers(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client)

    wrong_password = login(make_client(), password="wrong password!")
    unknown_email = login(make_client(), email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "invalid_credentials"
    assert "set-cookie" not in wrong_password.headers


def test_login_replaces_previous_session_of_the_same_browser(
    client: TestClient, db_session: Session
) -> None:
    register(client)
    first_token = client.cookies[SESSION_COOKIE]

    login(client)

    assert client.cookies[SESSION_COOKIE] != first_token
    first = db_session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_session_token(first_token))
    )
    assert first is not None
    assert first.revoked_at is not None


def test_registering_while_signed_in_ends_the_previous_session(
    client: TestClient, db_session: Session
) -> None:
    register(client, email="first@example.com", handle="first")
    first_token = client.cookies[SESSION_COOKIE]

    register(client, email="second@example.com", handle="second")

    assert client.get(ME).json()["handle"] == "second"
    first = db_session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_session_token(first_token))
    )
    assert first is not None
    assert first.revoked_at is not None


def test_login_upgrades_outdated_password_hash(client: TestClient, db_session: Session) -> None:
    register(client)
    weak_hash = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(DEFAULT_PASSWORD)
    db_session.execute(update(User).values(password_hash=weak_hash))

    assert login(client).status_code == 200

    assert db_session.scalar(select(User.password_hash)) != weak_hash


# --- Sessions and logout ----------------------------------------------------


def test_session_token_is_stored_only_as_hash(client: TestClient, db_session: Session) -> None:
    register(client)
    token = client.cookies[SESSION_COOKIE]

    stored = db_session.scalar(select(UserSession.token_hash))

    assert stored == hash_session_token(token)
    assert stored != token


def test_me_requires_a_session(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_tampered_cookie_is_rejected(client: TestClient) -> None:
    register(client)
    token = client.cookies[SESSION_COOKIE]
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, token[:-1] + ("A" if token[-1] != "A" else "B"))

    assert client.get(ME).status_code == 401


def test_expired_session_is_rejected(client: TestClient, db_session: Session) -> None:
    register(client)
    db_session.execute(
        update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )

    assert client.get(ME).status_code == 401


def test_logout_revokes_session_and_old_cookie_cannot_be_reused(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client)
    stolen_token = client.cookies[SESSION_COOKIE]

    response = client.post(LOGOUT)

    assert response.status_code == 204
    assert f'{SESSION_COOKIE}=""' in response.headers["set-cookie"]
    assert client.get(ME).status_code == 401

    replay = make_client()
    replay.cookies.set(SESSION_COOKIE, stolen_token)
    assert replay.get(ME).status_code == 401


def test_logout_only_ends_the_current_session(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client)
    laptop = make_client()
    login(laptop)

    client.post(LOGOUT)

    assert laptop.get(ME).status_code == 200


def test_logout_without_session_is_harmless(client: TestClient) -> None:
    assert client.post(LOGOUT).status_code == 204


# --- Cookie flags and logging -----------------------------------------------


def test_session_cookie_is_secure_only_in_production() -> None:
    production, development = Response(), Response()

    set_session_cookie(production, "token", Settings(app_env="production"))
    set_session_cookie(development, "token", Settings(app_env="development"))

    assert "Secure" in production.headers["set-cookie"]
    assert "Secure" not in development.headers["set-cookie"]


def test_session_cookie_lifetime_follows_settings() -> None:
    response = Response()

    set_session_cookie(response, "token", Settings(session_ttl_days=3))

    assert "Max-Age=259200" in response.headers["set-cookie"]


def test_auth_flow_never_logs_passwords_tokens_or_emails(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")

    register(client, email="private@example.com")
    token = client.cookies[SESSION_COOKIE]
    login(client, email="private@example.com")
    login(client, email="private@example.com", password="wrong password!")
    client.post(LOGOUT)

    assert caplog.records, "expected at least one log record"
    for secret in (DEFAULT_PASSWORD, token, "private@example.com"):
        assert secret not in caplog.text
