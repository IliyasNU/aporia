"""Profiles, public author pages and interests (USER-01)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register

PROFILE = "/api/v1/me/profile"
INTERESTS = "/api/v1/me/interests"
ME = "/api/v1/auth/me"


# --- Own profile ------------------------------------------------------------


def test_profile_endpoints_require_sign_in(client: TestClient) -> None:
    assert client.patch(PROFILE, json={"bio": "Hi"}).status_code == 401
    assert client.put(INTERESTS, json={"tags": ["ethics"]}).status_code == 401


def test_update_profile_changes_only_sent_fields(client: TestClient) -> None:
    register(client, display_name="Reader")

    response = client.patch(
        PROFILE, json={"bio": "  Thinking about thinking.  ", "website": "https://example.com/me"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Reader"
    assert body["bio"] == "Thinking about thinking."
    assert body["website"] == "https://example.com/me"


def test_website_can_be_removed_with_null(client: TestClient) -> None:
    register(client)
    client.patch(PROFILE, json={"website": "https://example.com"})

    response = client.patch(PROFILE, json={"website": None})

    assert response.json()["website"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"display_name": ""},
        {"display_name": None},
        {"display_name": "x" * 81},
        {"bio": "x" * 501},
        {"bio": None},
        {"website": "javascript:alert(1)"},
        {"website": "ftp://example.com"},
        {"website": "https://example.com/" + "x" * 200},
    ],
)
def test_update_profile_validates_input(client: TestClient, changes: dict[str, object]) -> None:
    register(client)

    response = client.patch(PROFILE, json=changes)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [{"role": "admin"}, {"email": "other@example.com"}, {"handle": "new_handle"}],
)
def test_profile_update_cannot_touch_protected_fields(
    client: TestClient, changes: dict[str, str]
) -> None:
    register(client)

    response = client.patch(PROFILE, json=changes)

    assert response.status_code == 422
    me = client.get(ME).json()
    assert me["role"] == "user"
    assert me["email"] == "reader@example.com"
    assert me["handle"] == "reader"


def test_users_only_edit_their_own_profile(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="alice@example.com", handle="alice", display_name="Alice")
    bob = make_client()
    register(bob, email="bob@example.com", handle="bob", display_name="Bob")

    bob.patch(PROFILE, json={"display_name": "Bob the Stoic"})

    assert client.get("/api/v1/authors/alice").json()["display_name"] == "Alice"
    assert client.get("/api/v1/authors/bob").json()["display_name"] == "Bob the Stoic"


def test_text_is_stored_as_given_and_returned_as_json(client: TestClient) -> None:
    register(client)
    bio = '<script>alert("x")</script> & friends'

    response = client.patch(PROFILE, json={"bio": bio})

    # The API stores plain text; the frontend escapes it when rendering.
    assert response.headers["content-type"] == "application/json"
    assert response.json()["bio"] == bio


# --- Public author profile --------------------------------------------------


def test_author_profile_is_public_and_hides_private_fields(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="alice@example.com", handle="alice", display_name="Alice")
    client.put(INTERESTS, json={"tags": ["ethics"]})

    response = make_client().get("/api/v1/authors/Alice")

    assert response.status_code == 200
    body = response.json()
    assert body["handle"] == "alice"
    assert body["display_name"] == "Alice"
    for private in ("email", "role", "interests", "password_hash"):
        assert private not in body
    assert "alice@example.com" not in response.text


def test_unknown_author_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/authors/nobody")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --- Interests --------------------------------------------------------------


def test_interests_replace_the_whole_list(client: TestClient) -> None:
    register(client)

    first = client.put(INTERESTS, json={"tags": ["logic", "Ethics", "ethics"]})
    second = client.put(INTERESTS, json={"tags": ["stoicism"]})

    assert first.status_code == 200
    assert [tag["slug"] for tag in first.json()["interests"]] == ["ethics", "logic"]
    assert second.json() == {"interests": [{"slug": "stoicism", "name": "Stoicism"}]}
    assert client.get(ME).json()["interests"] == [{"slug": "stoicism", "name": "Stoicism"}]


def test_empty_list_clears_interests(client: TestClient) -> None:
    register(client)
    client.put(INTERESTS, json={"tags": ["logic"]})

    response = client.put(INTERESTS, json={"tags": []})

    assert response.json() == {"interests": []}


def test_unknown_tag_is_rejected_and_nothing_changes(client: TestClient) -> None:
    register(client)
    client.put(INTERESTS, json={"tags": ["logic"]})

    response = client.put(INTERESTS, json={"tags": ["ethics", "astrology"]})

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "unknown_tags",
        "message": "Unknown tags: astrology",
    }
    assert [tag["slug"] for tag in client.get(ME).json()["interests"]] == ["logic"]


def test_interests_input_is_bounded(client: TestClient) -> None:
    register(client)

    too_many = client.put(INTERESTS, json={"tags": ["ethics"] * 51})
    too_long = client.put(INTERESTS, json={"tags": ["x" * 65]})

    assert too_many.status_code == 422
    assert too_long.status_code == 422
