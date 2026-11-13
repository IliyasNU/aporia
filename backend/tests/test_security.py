"""Release hardening checks (SEC-01, SEC-03)."""

import re
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.core import rate_limit
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter, limiter
from app.main import app
from tests.conftest import DEFAULT_PASSWORD, me, publish, register, signed_in, write_article

# Mutating endpoints that are public on purpose; everything else must demand a session.
PUBLIC_MUTATIONS = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),  # safe to call when signed out
    ("POST", "/api/v1/authors/{author_id}/newsletter-subscriptions"),  # no account by design
    ("POST", "/api/v1/newsletter/confirm"),  # authorised by the emailed token
    ("POST", "/api/v1/newsletter/unsubscribe"),  # authorised by the emailed token
}


def mutating_routes() -> list[tuple[str, str]]:
    """Every POST/PUT/PATCH/DELETE operation, read from the OpenAPI schema."""
    return sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"post", "put", "patch", "delete"}
    )


@pytest.mark.parametrize("method_path", mutating_routes(), ids=lambda mp: " ".join(mp))
def test_every_mutation_requires_sign_in_unless_public_by_design(
    client: TestClient, method_path: tuple[str, str]
) -> None:
    method, path = method_path
    if method_path in PUBLIC_MUTATIONS:
        pytest.skip("public by design")
    url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)

    response = client.request(method, url, json={})

    assert response.status_code == 401, response.text


def test_the_public_list_is_not_stale() -> None:
    assert len(mutating_routes()) > 20  # the schema really lists the API
    assert set(mutating_routes()) >= PUBLIC_MUTATIONS


# --- Rate limits (SEC-03) -----------------------------------------------------


@pytest.fixture
def limits_on(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(get_settings(), "rate_limits_enabled", True)
    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.usefixtures("limits_on")
def test_login_is_limited_per_email_with_retry_after(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client)
    attacker = make_client()
    for _ in range(rate_limit.LOGIN_PER_EMAIL.max_requests):
        attacker.post("/api/v1/auth/login", json={"email": "reader@example.com", "password": "x"})

    blocked = attacker.post(
        "/api/v1/auth/login", json={"email": "reader@example.com", "password": DEFAULT_PASSWORD}
    )

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert 0 < int(blocked.headers["Retry-After"]) <= rate_limit.LOGIN_PER_EMAIL.window_seconds
    # Another account is not affected by that email's limit.
    other = attacker.post(
        "/api/v1/auth/login", json={"email": "other@example.com", "password": "x"}
    )
    assert other.status_code == 401


@pytest.mark.usefixtures("limits_on")
def test_registration_is_limited_per_ip(make_client: Callable[[], TestClient]) -> None:
    client = make_client()
    statuses = [
        client.post(
            "/api/v1/auth/register",
            json={
                "email": f"user{n}@example.com",
                "password": DEFAULT_PASSWORD,
                "handle": f"user{n}",
                "display_name": "User",
            },
        ).status_code
        for n in range(rate_limit.REGISTER.max_requests + 1)
    ]

    assert statuses[:-1] == [201] * rate_limit.REGISTER.max_requests
    assert statuses[-1] == 429


@pytest.mark.usefixtures("limits_on")
def test_comments_reports_and_subscriptions_are_limited(
    make_client: Callable[[], TestClient], outbox: list[object]
) -> None:
    author = signed_in(make_client, "author")
    article = publish(author, write_article(author)["id"])
    reader = signed_in(make_client, "reader")
    comments = f"/api/v1/articles/{article['id']}/comments"

    codes = [reader.post(comments, json={"text": "Hi"}).status_code for _ in range(21)]
    assert codes.count(201) == rate_limit.COMMENT.max_requests
    assert codes[-1] == 429

    subscribe = f"/api/v1/authors/{me(author)['id']}/newsletter-subscriptions"
    codes = [
        make_client().post(subscribe, json={"email": f"fan{n}@example.com"}).status_code
        for n in range(rate_limit.SUBSCRIBE.max_requests + 1)
    ]
    assert codes[-1] == 429


def test_limiter_forgets_idle_counters() -> None:
    small = RateLimiter()
    small._hits["old"].append(0.0)
    small._hits["recent"].append(10_000.0)

    small._forget_idle(now=10_000.0)

    assert set(small._hits) == {"recent"}


# --- Request size -------------------------------------------------------------


def test_oversized_bodies_are_refused_before_parsing(client: TestClient) -> None:
    register(client)
    huge = "x" * (get_settings().max_body_bytes + 1)

    response = client.post("/api/v1/articles", json={"title": huge})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
