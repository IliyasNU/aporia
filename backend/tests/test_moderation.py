"""Reports and admin moderation (MOD-01)."""

from collections.abc import Callable
from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cli import main as cli
from app.models import UserRole
from app.services.moderation import set_role
from tests.conftest import publish, signed_in, write_article

API = "/api/v1"


@pytest.fixture
def author(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "author")


@pytest.fixture
def reader(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "reader")


@pytest.fixture
def admin(make_client: Callable[[], TestClient], db_session: Session) -> TestClient:
    client = signed_in(make_client, "admin")
    set_role(db_session, "admin@example.com", UserRole.ADMIN)
    return client


@pytest.fixture
def article(author: TestClient) -> dict[str, object]:
    return publish(author, write_article(author, tags=["ethics"])["id"])


def report(client: TestClient, target_type: str, target_id: object, reason: str = "Spam"):
    return client.post(
        f"{API}/reports",
        json={"target_type": target_type, "target_id": target_id, "reason": reason},
    )


def hide(client: TestClient, target_type: str, target_id: object, action: str = "hide"):
    return client.post(
        f"{API}/admin/moderate",
        json={"target_type": target_type, "target_id": target_id, "action": action},
    )


# --- Reports ------------------------------------------------------------------


def test_user_reports_an_article_once(reader: TestClient, article: dict[str, object]) -> None:
    first = report(reader, "article", article["id"])
    second = report(reader, "article", article["id"])

    assert first.status_code == 201
    assert first.json()["status"] == "open"
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_reported"


def test_reports_need_sign_in_and_an_existing_public_target(
    reader: TestClient, author: TestClient, make_client: Callable[[], TestClient]
) -> None:
    draft = write_article(author)

    assert report(make_client(), "article", draft["id"]).status_code == 401
    assert report(reader, "article", draft["id"]).status_code == 404
    assert report(reader, "comment", draft["id"]).status_code == 404
    assert report(reader, "user", draft["id"]).status_code == 422
    assert reader.post(f"{API}/reports", json={"target_type": "article"}).status_code == 422


# --- Admin only ---------------------------------------------------------------


def test_regular_users_cannot_use_admin_endpoints(
    reader: TestClient, article: dict[str, object], make_client: Callable[[], TestClient]
) -> None:
    assert reader.get(f"{API}/admin/reports").status_code == 403
    assert hide(reader, "article", article["id"]).status_code == 403
    assert make_client().get(f"{API}/admin/reports").status_code == 401
    assert reader.get(f"{API}/articles/{article['slug']}").status_code == 200


def test_admin_sees_open_reports(
    admin: TestClient, reader: TestClient, article: dict[str, object]
) -> None:
    report(reader, "article", article["id"], reason="Plagiarism")

    reports = admin.get(f"{API}/admin/reports").json()

    assert [(r["target_type"], r["reason"]) for r in reports] == [("article", "Plagiarism")]


def test_hidden_article_disappears_from_every_public_view(
    admin: TestClient,
    reader: TestClient,
    author: TestClient,
    article: dict[str, object],
    make_client: Callable[[], TestClient],
) -> None:
    reader.post(f"{API}/articles/{article['id']}/bookmark")
    reader.post(f"{API}/authors/{article['author']['id']}/follow")  # type: ignore[index]
    report(reader, "article", article["id"])

    response = hide(admin, "article", article["id"])

    assert response.status_code == 200
    assert response.json()["moderation_status"] == "hidden"
    guest = make_client()
    assert guest.get(f"{API}/articles/{article['slug']}").status_code == 404
    assert guest.get(f"{API}/articles").json()["total"] == 0
    assert guest.get(f"{API}/articles", params={"q": "doubt"}).json()["total"] == 0
    counts = {t["slug"]: t["article_count"] for t in guest.get(f"{API}/tags").json()}
    assert counts["ethics"] == 0
    assert reader.get(f"{API}/me/bookmarks").json()["total"] == 0
    assert reader.get(f"{API}/feed/following").json()["total"] == 0
    assert reader.get(f"{API}/articles/{article['id']}/comments").status_code == 404
    # The author still sees it, marked as hidden, and republishing does not unhide it.
    own = author.get(f"{API}/articles/{article['slug']}").json()
    assert own["moderation_status"] == "hidden"
    author.post(f"{API}/articles/{article['id']}/unpublish")
    author.post(f"{API}/articles/{article['id']}/publish")
    assert guest.get(f"{API}/articles/{article['slug']}").status_code == 404
    # Its reports are closed.
    assert admin.get(f"{API}/admin/reports").json() == []
    assert len(admin.get(f"{API}/admin/reports", params={"status": "resolved"}).json()) == 1


def test_unhide_restores_the_article(
    admin: TestClient, article: dict[str, object], make_client: Callable[[], TestClient]
) -> None:
    hide(admin, "article", article["id"])

    assert hide(admin, "article", article["id"], action="unhide").status_code == 200
    assert make_client().get(f"{API}/articles/{article['slug']}").status_code == 200


def test_hidden_comment_disappears_for_readers(
    admin: TestClient, reader: TestClient, article: dict[str, object]
) -> None:
    comment = reader.post(
        f"{API}/articles/{article['id']}/comments", json={"text": "Rude remark"}
    ).json()
    report(admin, "comment", comment["id"], reason="Insult")

    assert hide(admin, "comment", comment["id"]).status_code == 200

    assert reader.get(f"{API}/articles/{article['id']}/comments").json() == []
    assert reader.patch(f"{API}/comments/{comment['id']}", json={"text": "x"}).status_code == 404


def test_moderating_unknown_target_is_404(admin: TestClient) -> None:
    response = hide(admin, "comment", "00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


# --- Admin assignment command -------------------------------------------------


@pytest.fixture
def cli_uses_test_db(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    # The command opens its own session; give it the test's transaction instead.
    monkeypatch.setattr("app.cli.SessionLocal", lambda: nullcontext(db_session))


@pytest.mark.usefixtures("cli_uses_test_db")
def test_cli_sets_role(reader: TestClient, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli(["set-role", "READER@example.com", "admin"]) == 0
    assert "@reader is now admin" in capsys.readouterr().out
    assert reader.get(f"{API}/admin/reports").status_code == 200

    assert cli(["set-role", "reader@example.com", "user"]) == 0
    assert reader.get(f"{API}/admin/reports").status_code == 403


@pytest.mark.usefixtures("cli_uses_test_db")
def test_cli_reports_unknown_email(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli(["set-role", "nobody@example.com", "admin"]) == 1
    assert "No user with email" in capsys.readouterr().err
