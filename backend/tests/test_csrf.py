"""State-changing requests from untrusted origins are blocked (AUTH-02)."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import LOCAL_ORIGINS, Settings
from tests.conftest import register

LOGOUT = "/api/v1/auth/logout"


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Origin": "null"},  # sandboxed iframes and some redirects
        {"Origin": "http://localhost:8080.evil.example"},
        {"Referer": "https://evil.example/attack.html"},
    ],
)
def test_untrusted_origin_cannot_change_state(client: TestClient, headers: dict[str, str]) -> None:
    register(client)

    response = client.post(LOGOUT, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert client.get("/api/v1/auth/me").status_code == 200  # still signed in


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "http://localhost:8080"},
        {"Origin": "http://localhost:5173/"},
        {"Referer": "http://localhost:8080/settings"},
        {},  # no Origin and no Referer: not a browser, cannot carry a victim's cookie
    ],
)
def test_trusted_or_non_browser_requests_pass(client: TestClient, headers: dict[str, str]) -> None:
    register(client)

    response = client.post(LOGOUT, headers=headers)

    assert response.status_code == 204


def test_safe_methods_are_not_checked(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200


def test_check_runs_before_any_endpoint_logic(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example"},
        json={"email": "reader@example.com", "password": "whatever"},
    )

    assert response.status_code == 403


def test_trusted_origins_are_read_from_a_comma_separated_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://aporia.example/, https://www.aporia.example")

    assert Settings().trusted_origins == ["https://aporia.example", "https://www.aporia.example"]


def test_local_origins_are_the_default() -> None:
    assert Settings().trusted_origins == LOCAL_ORIGINS
