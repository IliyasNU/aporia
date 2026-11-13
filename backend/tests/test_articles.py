"""Writing, publishing, editing and deleting articles (ART-01, ART-02)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article
from app.services.articles import slugify
from tests.conftest import publish, register, write_article

ARTICLES = "/api/v1/articles"


@pytest.fixture
def author(client: TestClient) -> TestClient:
    register(client, email="author@example.com", handle="author", display_name="Author")
    return client


@pytest.fixture
def stranger(make_client: Callable[[], TestClient]) -> TestClient:
    other = make_client()
    register(other, email="stranger@example.com", handle="stranger", display_name="Stranger")
    return other


@pytest.fixture
def guest(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()


# --- Creating drafts --------------------------------------------------------


def test_writing_requires_sign_in(guest: TestClient) -> None:
    response = guest.post(ARTICLES, json={"title": "Hello"})

    assert response.status_code == 401


def test_new_article_is_a_draft_with_a_slug_from_its_title(author: TestClient) -> None:
    article = write_article(author, title="The Myth of Sisyphus!", tags=["existentialism"])

    assert article["status"] == "draft"
    assert article["slug"] == "the-myth-of-sisyphus"
    assert article["published_at"] is None
    assert article["author"]["handle"] == "author"
    assert article["tags"] == [{"slug": "existentialism", "name": "Existentialism"}]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "Ok", "summary": "x" * 301},
        {"title": "Ok", "body_markdown": "x" * 100_001},
        {
            "title": "Ok",
            "tags": ["ethics", "logic", "stoicism", "metaphysics", "epistemology", "consciousness"],
        },
        {"title": "Ok", "status": "published"},  # status only changes through publish
    ],
)
def test_create_validates_input(author: TestClient, payload: dict[str, object]) -> None:
    assert author.post(ARTICLES, json=payload).status_code == 422


def test_unknown_tags_are_rejected(author: TestClient) -> None:
    response = author.post(ARTICLES, json={"title": "Ok", "tags": ["astrology"]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_tags"


def test_same_title_gets_a_different_slug(author: TestClient) -> None:
    first = write_article(author, title="On Doubt")
    second = write_article(author, title="On Doubt")

    assert first["slug"] == "on-doubt"
    assert second["slug"] != "on-doubt"
    assert second["slug"].startswith("on-doubt-")


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Hello, World", "hello-world"),
        ("  Being and   Time  ", "being-and-time"),
        ("snake_case title", "snake-case-title"),
        ("Миф о Сизифе", "миф-о-сизифе"),
        ("?!…", "article"),
        ("word " * 40, ("word-" * 16).rstrip("-")),
    ],
)
def test_slugify(title: str, slug: str) -> None:
    assert slugify(title) == slug


# --- Who can see what -------------------------------------------------------


def test_draft_is_visible_only_to_its_author(
    author: TestClient, stranger: TestClient, guest: TestClient
) -> None:
    draft = write_article(author)
    url = f"{ARTICLES}/{draft['slug']}"

    assert author.get(url).status_code == 200
    assert stranger.get(url).status_code == 404
    assert guest.get(url).status_code == 404
    assert guest.get(ARTICLES).json()["total"] == 0
    assert stranger.get(f"/api/v1/me/articles/{draft['id']}").status_code == 403
    assert guest.get(f"/api/v1/me/articles/{draft['id']}").status_code == 401


def test_published_article_is_public(author: TestClient, guest: TestClient) -> None:
    draft = write_article(author)

    published = publish(author, draft["id"])

    assert published["status"] == "published"
    assert published["published_at"] is not None
    response = guest.get(f"{ARTICLES}/{draft['slug']}")
    assert response.status_code == 200
    assert response.json()["body_markdown"] == "Doubt is the beginning of wisdom."
    assert guest.get(ARTICLES).json()["total"] == 1


def test_markdown_is_returned_raw_not_rendered(author: TestClient, guest: TestClient) -> None:
    body = 'Hi <script>alert("x")</script> [link](javascript:alert(1))'
    publish(author, write_article(author, body=body)["id"])

    article = guest.get(f"{ARTICLES}/on-doubt").json()

    # The API never produces HTML; the frontend renders Markdown with raw HTML disabled.
    assert article["body_markdown"] == body


@pytest.mark.parametrize("body", ["", "   \n\t "])
def test_empty_article_cannot_be_published(author: TestClient, body: str) -> None:
    draft = write_article(author, body=body)

    response = author.post(f"{ARTICLES}/{draft['id']}/publish")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_body"


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("patch", "", {"title": "Hijacked"}),
        ("post", "/publish", None),
        ("post", "/unpublish", None),
        ("delete", "", None),
    ],
)
def test_stranger_cannot_change_someone_elses_article(
    author: TestClient, stranger: TestClient, method: str, suffix: str, payload: object
) -> None:
    article = publish(author, write_article(author)["id"])

    response = stranger.request(method, f"{ARTICLES}/{article['id']}{suffix}", json=payload)

    assert response.status_code == 403
    assert author.get(f"{ARTICLES}/{article['slug']}").json()["title"] == "On Doubt"


def test_unknown_article_id_returns_404(author: TestClient) -> None:
    response = author.patch(f"{ARTICLES}/00000000-0000-0000-0000-000000000000", json={})

    assert response.status_code == 404


# --- Editing and stable URLs ------------------------------------------------


def test_renaming_a_draft_updates_its_slug(author: TestClient) -> None:
    draft = write_article(author, title="Working title")

    renamed = author.patch(f"{ARTICLES}/{draft['id']}", json={"title": "Final Title"}).json()

    assert renamed["slug"] == "final-title"


def test_slug_is_frozen_after_first_publication(author: TestClient, guest: TestClient) -> None:
    article = publish(author, write_article(author, title="On Doubt")["id"])

    renamed = author.patch(f"{ARTICLES}/{article['id']}", json={"title": "On Certainty"}).json()

    assert renamed["title"] == "On Certainty"
    assert renamed["slug"] == "on-doubt"
    assert guest.get(f"{ARTICLES}/on-doubt").json()["title"] == "On Certainty"


def test_editing_a_published_article_keeps_it_published(
    author: TestClient, guest: TestClient
) -> None:
    article = publish(author, write_article(author)["id"])

    author.patch(
        f"{ARTICLES}/{article['id']}", json={"body_markdown": "Revised.", "tags": ["logic"]}
    )

    public = guest.get(f"{ARTICLES}/{article['slug']}").json()
    assert public["status"] == "published"
    assert public["body_markdown"] == "Revised."
    assert public["tags"] == [{"slug": "logic", "name": "Logic"}]
    assert public["published_at"] == article["published_at"]


def test_patch_rejects_null_and_status_changes(author: TestClient) -> None:
    draft = write_article(author)

    assert author.patch(f"{ARTICLES}/{draft['id']}", json={"title": None}).status_code == 422
    assert (
        author.patch(f"{ARTICLES}/{draft['id']}", json={"status": "published"}).status_code == 422
    )


# --- Unpublish, republish, delete -------------------------------------------


def test_unpublished_article_disappears_for_the_public(
    author: TestClient, guest: TestClient
) -> None:
    article = publish(author, write_article(author)["id"])

    response = author.post(f"{ARTICLES}/{article['id']}/unpublish")

    assert response.status_code == 200
    assert response.json()["status"] == "unpublished"
    assert guest.get(f"{ARTICLES}/{article['slug']}").status_code == 404
    assert guest.get(ARTICLES).json()["total"] == 0
    assert author.get(f"{ARTICLES}/{article['slug']}").status_code == 200


def test_republishing_keeps_first_publication_date_and_slug(author: TestClient) -> None:
    article = publish(author, write_article(author)["id"])
    author.post(f"{ARTICLES}/{article['id']}/unpublish")

    again = publish(author, article["id"])

    assert again["published_at"] == article["published_at"]
    assert again["slug"] == article["slug"]


def test_publishing_twice_changes_nothing(author: TestClient) -> None:
    article = publish(author, write_article(author)["id"])

    again = publish(author, article["id"])

    assert again["published_at"] == article["published_at"]


def test_only_published_articles_can_be_unpublished(author: TestClient) -> None:
    draft = write_article(author)

    response = author.post(f"{ARTICLES}/{draft['id']}/unpublish")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_state"


def test_soft_delete_hides_article_from_everyone_but_keeps_the_row(
    author: TestClient, guest: TestClient, db_session: Session
) -> None:
    article = publish(author, write_article(author)["id"])

    assert author.delete(f"{ARTICLES}/{article['id']}").status_code == 204

    assert guest.get(f"{ARTICLES}/{article['slug']}").status_code == 404
    assert author.get(f"{ARTICLES}/{article['slug']}").status_code == 404
    assert author.get(f"/api/v1/me/articles/{article['id']}").status_code == 404
    assert author.get("/api/v1/me/articles").json()["total"] == 0
    assert author.patch(f"{ARTICLES}/{article['id']}", json={"title": "X"}).status_code == 404
    row = db_session.scalar(select(Article))
    assert row is not None
    assert row.deleted_at is not None


def test_my_articles_lists_every_status(author: TestClient) -> None:
    draft = write_article(author, title="Draft")
    published = publish(author, write_article(author, title="Published")["id"])
    taken_down = publish(author, write_article(author, title="Taken down")["id"])
    author.post(f"{ARTICLES}/{taken_down['id']}/unpublish")

    items = author.get("/api/v1/me/articles").json()["items"]

    assert {(i["title"], i["status"]) for i in items} == {
        ("Draft", "draft"),
        ("Published", "published"),
        ("Taken down", "unpublished"),
    }
    assert draft["id"] in {i["id"] for i in items}
    assert published["id"] in {i["id"] for i in items}
