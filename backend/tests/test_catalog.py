"""Public catalog: search, tag and author filters, pagination, tag counts (ART-03)."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import Article
from tests.conftest import publish, register, write_article

ARTICLES = "/api/v1/articles"


@pytest.fixture
def author(client: TestClient) -> TestClient:
    register(client, email="author@example.com", handle="author", display_name="Author")
    return client


@pytest.fixture
def guest(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()


def titles(response_json: dict[str, object]) -> list[str]:
    return [item["title"] for item in response_json["items"]]  # type: ignore[index, union-attr]


def test_empty_catalog_is_a_normal_empty_page(guest: TestClient) -> None:
    response = guest.get(ARTICLES)

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}


def test_list_items_carry_card_data_but_no_body(author: TestClient, guest: TestClient) -> None:
    publish(author, write_article(author, tags=["ethics"])["id"])

    item = guest.get(ARTICLES).json()["items"][0]

    assert item["title"] == "On Doubt"
    assert item["author"] == {
        "id": item["author"]["id"],
        "handle": "author",
        "display_name": "Author",
    }
    assert item["tags"] == [{"slug": "ethics", "name": "Ethics"}]
    assert "body_markdown" not in item


def test_newest_first_with_stable_tie_breaker(
    author: TestClient, guest: TestClient, db_session: Session
) -> None:
    for title in ("First", "Second", "Third"):
        publish(author, write_article(author, title=title)["id"])
    same_moment = datetime(2026, 1, 1, tzinfo=UTC)
    db_session.execute(update(Article).values(published_at=same_moment))

    first = titles(guest.get(ARTICLES).json())
    second = titles(guest.get(ARTICLES).json())

    assert sorted(first) == ["First", "Second", "Third"]
    assert first == second  # equal timestamps still give the same order every time


def test_search_is_case_insensitive_on_title_and_summary(
    author: TestClient, guest: TestClient
) -> None:
    publish(author, write_article(author, title="On Stoic Calm", summary="Marcus")["id"])
    publish(author, write_article(author, title="Being", summary="Notes on HEIDEGGER")["id"])
    publish(author, write_article(author, title="Unrelated", summary="Nothing here")["id"])

    assert titles(guest.get(ARTICLES, params={"q": "stoic"}).json()) == ["On Stoic Calm"]
    assert titles(guest.get(ARTICLES, params={"q": "heidegger"}).json()) == ["Being"]
    assert guest.get(ARTICLES, params={"q": "kierkegaard"}).json()["total"] == 0


def test_search_handles_unicode(author: TestClient, guest: TestClient) -> None:
    publish(author, write_article(author, title="Миф о Сизифе", summary="Камю")["id"])

    assert titles(guest.get(ARTICLES, params={"q": "СИЗИФ"}).json()) == ["Миф о Сизифе"]
    assert titles(guest.get(ARTICLES, params={"q": "камю"}).json()) == ["Миф о Сизифе"]


@pytest.mark.parametrize("q", ["%", "_", "\\"])
def test_search_treats_wildcards_as_plain_text(
    author: TestClient, guest: TestClient, q: str
) -> None:
    publish(author, write_article(author, title="Plain title")["id"])

    assert guest.get(ARTICLES, params={"q": q}).json()["total"] == 0


def test_filter_by_tag_and_author(
    author: TestClient, guest: TestClient, make_client: Callable[[], TestClient]
) -> None:
    publish(author, write_article(author, title="Ethics piece", tags=["ethics"])["id"])
    publish(author, write_article(author, title="Logic piece", tags=["logic"])["id"])
    other = make_client()
    register(other, email="other@example.com", handle="other", display_name="Other")
    publish(other, write_article(other, title="Other ethics", tags=["ethics"])["id"])

    by_tag = guest.get(ARTICLES, params={"tag": "ethics"}).json()
    by_author = guest.get(ARTICLES, params={"author": "AUTHOR"}).json()
    both = guest.get(ARTICLES, params={"tag": "ethics", "author": "author"}).json()

    assert sorted(titles(by_tag)) == ["Ethics piece", "Other ethics"]
    assert sorted(titles(by_author)) == ["Ethics piece", "Logic piece"]
    assert titles(both) == ["Ethics piece"]
    assert guest.get(ARTICLES, params={"tag": "astrology"}).json()["total"] == 0


def test_drafts_unpublished_and_deleted_never_appear(author: TestClient, guest: TestClient) -> None:
    write_article(author, title="Draft")
    unpublished = publish(author, write_article(author, title="Unpublished")["id"])
    author.post(f"{ARTICLES}/{unpublished['id']}/unpublish")
    deleted = publish(author, write_article(author, title="Deleted")["id"])
    author.delete(f"{ARTICLES}/{deleted['id']}")
    publish(author, write_article(author, title="Visible", tags=["logic"])["id"])

    assert titles(guest.get(ARTICLES).json()) == ["Visible"]
    assert titles(guest.get(ARTICLES, params={"q": "e"}).json()) == ["Visible"]
    counts = {t["slug"]: t["article_count"] for t in guest.get("/api/v1/tags").json()}
    assert counts["logic"] == 1


def test_pagination(author: TestClient, guest: TestClient) -> None:
    for number in range(5):
        publish(author, write_article(author, title=f"Essay {number}")["id"])

    page1 = guest.get(ARTICLES, params={"page_size": 2}).json()
    page3 = guest.get(ARTICLES, params={"page_size": 2, "page": 3}).json()
    beyond = guest.get(ARTICLES, params={"page_size": 2, "page": 9}).json()

    assert (len(page1["items"]), page1["total"]) == (2, 5)
    assert len(page3["items"]) == 1
    assert beyond["items"] == []
    assert beyond["total"] == 5


@pytest.mark.parametrize(
    "params",
    [
        {"sort": "random"},
        {"page": 0},
        {"page_size": 0},
        {"page_size": 51},
        {"q": "x" * 101},
    ],
)
def test_invalid_list_parameters_return_422(guest: TestClient, params: dict[str, object]) -> None:
    response = guest.get(ARTICLES, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_tag_catalog_lists_all_seeded_tags(guest: TestClient) -> None:
    tags = guest.get("/api/v1/tags").json()

    assert [t["slug"] for t in tags] == [
        "consciousness",
        "epistemology",
        "ethics",
        "existentialism",
        "logic",
        "metaphysics",
        "stoicism",
    ]
    assert all(t["article_count"] == 0 for t in tags)


@contextmanager
def count_queries() -> Iterator[list[str]]:
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_listing_uses_a_fixed_number_of_queries(author: TestClient, guest: TestClient) -> None:
    publish(author, write_article(author, title="One", tags=["ethics"])["id"])
    with count_queries() as few:
        guest.get(ARTICLES)

    for number in range(10):
        publish(author, write_article(author, title=f"More {number}", tags=["logic"])["id"])
    with count_queries() as many:
        guest.get(ARTICLES)

    assert len(many) == len(few)  # no N+1: authors and tags are loaded in bulk
