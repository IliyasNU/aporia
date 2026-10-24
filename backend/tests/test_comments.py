"""Flat comments (SOC-02)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Comment
from tests.conftest import publish, signed_in, write_article

API = "/api/v1"


@pytest.fixture
def article(make_client: Callable[[], TestClient]) -> dict[str, object]:
    author = signed_in(make_client, "author")
    return publish(author, write_article(author)["id"])


@pytest.fixture
def reader(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "reader")


def comments_url(article: dict[str, object]) -> str:
    return f"{API}/articles/{article['id']}/comments"


def test_comment_appears_for_everyone(
    reader: TestClient, article: dict[str, object], make_client: Callable[[], TestClient]
) -> None:
    response = reader.post(comments_url(article), json={"text": "  Well argued.  "})

    assert response.status_code == 201
    assert response.json()["text"] == "Well argued."
    assert response.json()["author"]["handle"] == "reader"
    listed = make_client().get(comments_url(article)).json()
    assert [c["text"] for c in listed] == ["Well argued."]


def test_comments_are_listed_oldest_first(
    reader: TestClient, article: dict[str, object], db_session: Session
) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for text in ("Third", "First", "Second"):
        comment = reader.post(comments_url(article), json={"text": text}).json()
        # Real requests run in separate transactions and get different timestamps;
        # inside one test transaction now() is constant, so set them explicitly.
        offset = {"First": 0, "Second": 1, "Third": 2}[text]
        db_session.execute(
            update(Comment)
            .where(Comment.id == comment["id"])
            .values(created_at=start + timedelta(minutes=offset))
        )

    assert [c["text"] for c in reader.get(comments_url(article)).json()] == [
        "First",
        "Second",
        "Third",
    ]


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
def test_comment_length_is_bounded(
    reader: TestClient, article: dict[str, object], text: str
) -> None:
    assert reader.post(comments_url(article), json={"text": text}).status_code == 422


def test_comment_text_is_stored_verbatim(reader: TestClient, article: dict[str, object]) -> None:
    text = "<img src=x onerror=alert(1)> **not markdown**"

    created = reader.post(comments_url(article), json={"text": text}).json()

    # Plain text: the frontend shows it as text, never as HTML or Markdown.
    assert created["text"] == text


def test_guests_cannot_comment(
    article: dict[str, object], make_client: Callable[[], TestClient]
) -> None:
    assert make_client().post(comments_url(article), json={"text": "Hi"}).status_code == 401


def test_no_comments_on_non_public_articles(
    reader: TestClient, make_client: Callable[[], TestClient]
) -> None:
    author = signed_in(make_client, "writer")
    draft = write_article(author)

    assert reader.post(comments_url(draft), json={"text": "Hi"}).status_code == 404
    assert reader.get(comments_url(draft)).status_code == 404


def test_comments_vanish_when_the_article_is_unpublished(
    reader: TestClient, make_client: Callable[[], TestClient]
) -> None:
    author = signed_in(make_client, "writer")
    article = publish(author, write_article(author)["id"])
    reader.post(comments_url(article), json={"text": "Hi"})

    author.post(f"{API}/articles/{article['id']}/unpublish")

    assert reader.get(comments_url(article)).status_code == 404


def test_author_edits_and_deletes_own_comment(
    reader: TestClient, article: dict[str, object]
) -> None:
    comment = reader.post(comments_url(article), json={"text": "Frist"}).json()

    edited = reader.patch(f"{API}/comments/{comment['id']}", json={"text": "First"})
    assert edited.status_code == 200
    assert edited.json()["text"] == "First"

    assert reader.delete(f"{API}/comments/{comment['id']}").status_code == 204
    assert reader.get(comments_url(article)).json() == []
    assert reader.delete(f"{API}/comments/{comment['id']}").status_code == 404


def test_nobody_else_can_edit_or_delete_a_comment(
    reader: TestClient, article: dict[str, object], make_client: Callable[[], TestClient]
) -> None:
    comment = reader.post(comments_url(article), json={"text": "Mine"}).json()
    other = signed_in(make_client, "other")

    assert other.patch(f"{API}/comments/{comment['id']}", json={"text": "Yours"}).status_code == 403
    assert other.delete(f"{API}/comments/{comment['id']}").status_code == 403
    assert [c["text"] for c in reader.get(comments_url(article)).json()] == ["Mine"]
