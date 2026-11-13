"""GET /feed/recommended: personalisation, cold start and exclusions (REC-01..03)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import UserRole
from app.services.moderation import set_role
from tests.conftest import me, publish, signed_in, write_article
from tests.test_catalog import count_queries

FEED = "/api/v1/feed/recommended"


@pytest.fixture
def writers(make_client: Callable[[], TestClient]) -> dict[str, TestClient]:
    return {
        "kant": signed_in(make_client, "kant", "Immanuel Kant"),
        "hume": signed_in(make_client, "hume", "David Hume"),
    }


def titles(feed: dict[str, object]) -> list[str]:
    return [item["article"]["title"] for item in feed["items"]]  # type: ignore[index, union-attr]


def reasons(feed: dict[str, object]) -> dict[str, str]:
    return {item["article"]["title"]: item["reason"] for item in feed["items"]}  # type: ignore[index, union-attr]


def test_guest_gets_a_cold_start_feed_of_public_essays(
    writers: dict[str, TestClient], make_client: Callable[[], TestClient]
) -> None:
    kant = writers["kant"]
    publish(kant, write_article(kant, title="Critique", tags=["metaphysics"])["id"])
    write_article(kant, title="Draft")

    feed = make_client().get(FEED).json()

    assert feed["cold_start"] is True
    assert titles(feed) == ["Critique"]
    assert feed["items"][0]["reason"] == "Recently published"
    assert 0 <= feed["items"][0]["score"] <= 1


def test_feed_is_never_empty_without_interests(
    writers: dict[str, TestClient], make_client: Callable[[], TestClient]
) -> None:
    hume = writers["hume"]
    publish(hume, write_article(hume, title="Enquiry", tags=["epistemology"])["id"])
    newcomer = signed_in(make_client, "newcomer")

    feed = newcomer.get(FEED).json()

    assert feed["cold_start"] is True
    assert titles(feed) == ["Enquiry"]


def test_interests_and_follows_come_first_with_reasons(
    writers: dict[str, TestClient], make_client: Callable[[], TestClient]
) -> None:
    kant, hume = writers["kant"], writers["hume"]
    publish(hume, write_article(hume, title="Enquiry", tags=["epistemology"])["id"])
    publish(kant, write_article(kant, title="Groundwork", tags=["ethics"])["id"])
    publish(kant, write_article(kant, title="Logic lectures", tags=["logic"])["id"])
    reader = signed_in(make_client, "reader")
    reader.put("/api/v1/me/interests", json={"tags": ["epistemology"]})
    reader.post(f"/api/v1/authors/{me(kant)['id']}/follow")

    feed = reader.get(FEED).json()

    assert feed["cold_start"] is False
    assert titles(feed)[0] == "Enquiry"  # 0.40 interest beats 0.25 follow
    assert reasons(feed) == {
        "Enquiry": "You are interested in Epistemology",
        "Groundwork": "You follow Immanuel Kant",
        "Logic lectures": "You follow Immanuel Kant",
    }


def test_own_saved_and_non_public_essays_are_left_out(
    writers: dict[str, TestClient], db_session: Session, make_client: Callable[[], TestClient]
) -> None:
    kant, hume = writers["kant"], writers["hume"]
    publish(kant, write_article(kant, title="Own essay")["id"])
    saved = publish(hume, write_article(hume, title="Saved")["id"])
    unpublished = publish(hume, write_article(hume, title="Unpublished")["id"])
    deleted = publish(hume, write_article(hume, title="Deleted")["id"])
    hidden = publish(hume, write_article(hume, title="Hidden")["id"])
    publish(hume, write_article(hume, title="Visible")["id"])
    write_article(hume, title="Draft")
    kant.post(f"/api/v1/articles/{saved['id']}/bookmark")
    hume.post(f"/api/v1/articles/{unpublished['id']}/unpublish")
    hume.delete(f"/api/v1/articles/{deleted['id']}")
    admin = signed_in(make_client, "admin")
    set_role(db_session, "admin@example.com", UserRole.ADMIN)
    admin.post(
        "/api/v1/admin/moderate",
        json={"target_type": "article", "target_id": hidden["id"], "action": "hide"},
    )

    assert titles(kant.get(FEED).json()) == ["Visible"]


def test_bookmarks_make_essays_popular_for_everyone_else(
    writers: dict[str, TestClient], make_client: Callable[[], TestClient]
) -> None:
    hume = writers["hume"]
    publish(hume, write_article(hume, title="Quiet", tags=["logic"])["id"])
    loved = publish(hume, write_article(hume, title="Loved", tags=["logic"])["id"])
    for name in ("reader1", "reader2", "reader3"):
        signed_in(make_client, name).post(f"/api/v1/articles/{loved['id']}/bookmark")

    feed = make_client().get(FEED).json()

    assert titles(feed) == ["Loved", "Quiet"]
    assert reasons(feed)["Loved"] == "Popular with readers"


def test_pagination_and_stable_order(
    writers: dict[str, TestClient], make_client: Callable[[], TestClient]
) -> None:
    hume = writers["hume"]
    for number in range(5):
        publish(hume, write_article(hume, title=f"Essay {number}")["id"])
    guest = make_client()

    full = titles(guest.get(FEED).json())
    pages = [guest.get(FEED, params={"page_size": 2, "page": n}).json() for n in (1, 2, 3)]

    assert pages[0]["total"] == 5
    assert [title for page in pages for title in titles(page)] == full
    assert titles(guest.get(FEED).json()) == full


def test_feed_uses_a_fixed_number_of_queries(
    writers: dict[str, TestClient], make_client: Callable[[], TestClient]
) -> None:
    hume = writers["hume"]
    reader = signed_in(make_client, "reader")
    reader.put("/api/v1/me/interests", json={"tags": ["logic"]})
    publish(hume, write_article(hume, title="One", tags=["logic"])["id"])
    with count_queries() as few:
        reader.get(FEED)

    for number in range(10):
        publish(hume, write_article(hume, title=f"More {number}", tags=["ethics"])["id"])
    with count_queries() as many:
        reader.get(FEED)

    assert len(many) == len(few)
