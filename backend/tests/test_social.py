"""Follows, the following feed, bookmarks and popularity (SOC-01, SOC-02)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bookmark, Follow
from tests.conftest import me, publish, signed_in, write_article

API = "/api/v1"


@pytest.fixture
def reader(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "reader")


@pytest.fixture
def author(make_client: Callable[[], TestClient]) -> TestClient:
    return signed_in(make_client, "author")


@pytest.fixture
def guest(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()


# --- Follows ------------------------------------------------------------------


def test_follow_shows_on_profile_and_in_following_list(
    reader: TestClient, author: TestClient
) -> None:
    author_id = me(author)["id"]

    assert reader.post(f"{API}/authors/{author_id}/follow").status_code == 204

    assert reader.get(f"{API}/authors/author").json()["followed_by_me"] is True
    article = publish(author, write_article(author)["id"])
    assert reader.get(f"{API}/articles/{article['slug']}").json()["following_author"] is True
    following = reader.get(f"{API}/me/following").json()
    assert [f["author"]["handle"] for f in following] == ["author"]


def test_follow_is_idempotent_and_unique(
    reader: TestClient, author: TestClient, db_session: Session
) -> None:
    author_id = me(author)["id"]

    reader.post(f"{API}/authors/{author_id}/follow")
    second = reader.post(f"{API}/authors/{author_id}/follow")

    assert second.status_code == 204
    assert db_session.scalar(select(func.count()).select_from(Follow)) == 1


def test_unfollow_is_idempotent(reader: TestClient, author: TestClient) -> None:
    author_id = me(author)["id"]
    reader.post(f"{API}/authors/{author_id}/follow")

    assert reader.delete(f"{API}/authors/{author_id}/follow").status_code == 204
    assert reader.delete(f"{API}/authors/{author_id}/follow").status_code == 204
    assert reader.get(f"{API}/authors/author").json()["followed_by_me"] is False
    assert reader.get(f"{API}/me/following").json() == []


def test_cannot_follow_yourself(reader: TestClient) -> None:
    response = reader.post(f"{API}/authors/{me(reader)['id']}/follow")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cannot_follow_self"


def test_follow_unknown_author_is_404(reader: TestClient) -> None:
    response = reader.post(f"{API}/authors/00000000-0000-0000-0000-000000000000/follow")

    assert response.status_code == 404


def test_follow_requires_sign_in(guest: TestClient, author: TestClient) -> None:
    assert guest.post(f"{API}/authors/{me(author)['id']}/follow").status_code == 401
    assert guest.get(f"{API}/authors/author").json()["followed_by_me"] is False


def test_following_feed_shows_only_followed_public_articles_newest_first(
    reader: TestClient, author: TestClient, make_client: Callable[[], TestClient]
) -> None:
    stranger = signed_in(make_client, "stranger")
    publish(author, write_article(author, title="Older")["id"])
    publish(author, write_article(author, title="Newer")["id"])
    write_article(author, title="Draft")
    publish(stranger, write_article(stranger, title="Not followed")["id"])
    reader.post(f"{API}/authors/{me(author)['id']}/follow")

    feed = reader.get(f"{API}/feed/following").json()

    assert {i["title"] for i in feed["items"]} == {"Older", "Newer"}
    assert feed["total"] == 2
    times = [i["published_at"] for i in feed["items"]]
    assert times == sorted(times, reverse=True)


def test_following_feed_requires_sign_in(guest: TestClient) -> None:
    assert guest.get(f"{API}/feed/following").status_code == 401


# --- Bookmarks ----------------------------------------------------------------


def test_bookmark_flow(reader: TestClient, author: TestClient, db_session: Session) -> None:
    article = publish(author, write_article(author)["id"])
    url = f"{API}/articles/{article['id']}/bookmark"

    assert reader.post(url).status_code == 204
    assert reader.post(url).status_code == 204  # idempotent
    assert db_session.scalar(select(func.count()).select_from(Bookmark)) == 1
    assert reader.get(f"{API}/articles/{article['slug']}").json()["bookmarked_by_me"] is True
    assert [i["title"] for i in reader.get(f"{API}/me/bookmarks").json()["items"]] == ["On Doubt"]

    assert reader.delete(url).status_code == 204
    assert reader.delete(url).status_code == 204
    assert reader.get(f"{API}/me/bookmarks").json()["total"] == 0


def test_cannot_bookmark_non_public_articles(reader: TestClient, author: TestClient) -> None:
    draft = write_article(author)

    response = reader.post(f"{API}/articles/{draft['id']}/bookmark")

    assert response.status_code == 404


def test_bookmarks_of_articles_that_became_private_disappear(
    reader: TestClient, author: TestClient
) -> None:
    article = publish(author, write_article(author)["id"])
    reader.post(f"{API}/articles/{article['id']}/bookmark")

    author.post(f"{API}/articles/{article['id']}/unpublish")

    assert reader.get(f"{API}/me/bookmarks").json()["items"] == []


def test_guest_sees_no_bookmark_state(guest: TestClient, author: TestClient) -> None:
    article = publish(author, write_article(author)["id"])

    assert guest.get(f"{API}/articles/{article['slug']}").json()["bookmarked_by_me"] is False
    assert guest.post(f"{API}/articles/{article['id']}/bookmark").status_code == 401


def test_popular_sort_orders_by_bookmarks(
    author: TestClient, guest: TestClient, make_client: Callable[[], TestClient]
) -> None:
    quiet = publish(author, write_article(author, title="Quiet")["id"])
    loved = publish(author, write_article(author, title="Loved")["id"])
    liked = publish(author, write_article(author, title="Liked")["id"])
    for name in ("one", "two"):
        signed_in(make_client, name).post(f"{API}/articles/{loved['id']}/bookmark")
    signed_in(make_client, "three").post(f"{API}/articles/{liked['id']}/bookmark")

    popular = guest.get(f"{API}/articles", params={"sort": "popular"}).json()

    assert [i["title"] for i in popular["items"]] == ["Loved", "Liked", "Quiet"]
    assert quiet["id"] in {i["id"] for i in popular["items"]}
