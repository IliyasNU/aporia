"""The pure recommendation formula with fixed inputs (REC-01, REC-03).

Expected values are worked out by hand in the comments, so the order can be
checked without running anything.
"""

import math
import random
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.services.ranking import (
    WEIGHTS,
    Candidate,
    Reader,
    diversity,
    freshness,
    popularity,
    rank,
    tag_match,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
ANNA, BEA, CAL = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
ETHICS = {"ethics": "Ethics"}
LOGIC = {"logic": "Logic"}


def essay(
    name: str,
    *,
    author: uuid.UUID = CAL,
    days_old: float = 0,
    tags: dict[str, str] | None = None,
    bookmarks: int = 0,
    id_: uuid.UUID | None = None,
) -> Candidate:
    return Candidate(
        id=id_ or uuid.uuid5(uuid.NAMESPACE_URL, name),
        author_id=author,
        author_name={ANNA: "Anna", BEA: "Bea", CAL: "Cal"}[author],
        published_at=NOW - timedelta(days=days_old),
        tags=tags or {},
        bookmarks=bookmarks,
    )


def order(ranked: list) -> list[uuid.UUID]:
    return [r.candidate.id for r in ranked]


# --- Components ---------------------------------------------------------------


def test_weights_sum_to_one() -> None:
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_tag_match_is_the_share_of_matching_tags() -> None:
    reader = Reader(interests=frozenset({"ethics"}))

    assert tag_match(essay("a", tags={**ETHICS, **LOGIC}), reader) == 0.5
    assert tag_match(essay("b", tags=ETHICS), reader) == 1.0
    assert tag_match(essay("c"), reader) == 0.0
    assert tag_match(essay("d", tags=ETHICS), Reader()) == 0.0


def test_popularity_is_log_scaled_so_hits_cannot_dominate() -> None:
    assert popularity(0, 0) == 0.0
    assert popularity(1000, 1000) == 1.0
    # 10 bookmarks against a 1000-bookmark hit still keeps about a third of the signal
    # (linear scaling would give 0.01).
    assert popularity(10, 1000) == pytest.approx(math.log(11) / math.log(1001))
    assert popularity(10, 1000) > 0.34


def test_freshness_decays_over_a_month() -> None:
    assert freshness(NOW, NOW) == 1.0
    assert freshness(NOW - timedelta(days=30), NOW) == pytest.approx(math.exp(-1))
    assert freshness(NOW + timedelta(hours=1), NOW) == 1.0  # clock skew never exceeds 1


def test_diversity_rewards_tags_not_shown_yet() -> None:
    both = essay("x", tags={**ETHICS, **LOGIC})

    assert diversity(both, set()) == 1.0
    assert diversity(both, {"ethics"}) == 0.5
    assert diversity(both, {"ethics", "logic"}) == 0.0
    assert diversity(essay("untagged"), set()) == 0.0


# --- Fixed scenario -----------------------------------------------------------


def test_fixed_scenario_gives_expected_order_scores_and_reasons() -> None:
    reader = Reader(interests=frozenset({"ethics"}), following=frozenset({BEA}))
    a = essay("A", author=ANNA, days_old=1, tags=ETHICS)
    b = essay("B", author=BEA, days_old=10, tags=LOGIC, bookmarks=5)
    c = essay("C", author=CAL, days_old=60, tags=LOGIC, bookmarks=20)
    d = essay("D", author=CAL, days_old=0)

    ranked = rank([d, c, b, a], reader, NOW)

    # A = .40*1 + .15*e^(-1/30) + .05*1                          = 0.5951
    # B = .25*1 + .15*ln6/ln21 + .15*e^(-1/3) + .05*1            = 0.4958
    # C = .15*1 + .15*e^(-2)   + .05*0 (logic already shown by B) = 0.1703
    # D = .15*1 (brand new, no tags)                               = 0.1500
    assert order(ranked) == [a.id, b.id, c.id, d.id]
    assert [round(r.score, 4) for r in ranked] == [0.5951, 0.4958, 0.1703, 0.15]
    assert [r.reason for r in ranked] == [
        "You are interested in Ethics",
        "You follow Bea",
        "Popular with readers",
        "Recently published",
    ]
    assert all(0 <= value <= 1 for r in ranked for value in r.components.values())


def test_order_does_not_depend_on_input_order() -> None:
    reader = Reader(interests=frozenset({"logic"}))
    essays = [
        essay(f"e{i}", days_old=i % 4, tags=LOGIC if i % 2 else ETHICS, bookmarks=i % 3)
        for i in range(12)
    ]
    expected = order(rank(essays, reader, NOW))

    for seed in range(5):
        shuffled = essays[:]
        random.Random(seed).shuffle(shuffled)
        assert order(rank(shuffled, reader, NOW)) == expected


def test_equal_scores_break_ties_by_id() -> None:
    low, high = sorted([uuid.uuid4(), uuid.uuid4()])
    # Same age, no tags, no bookmarks: identical scores, so only the id decides.
    twins = [essay("t1", days_old=2, id_=low), essay("t2", days_old=2, id_=high)]

    assert order(rank(twins, Reader(), NOW)) == [high, low]
    assert order(rank(twins[::-1], Reader(), NOW)) == [high, low]


def test_diversity_lifts_a_different_topic_above_a_repeat() -> None:
    first = essay("ethics-1", days_old=0, tags=ETHICS)
    second = essay("ethics-2", days_old=0, tags=ETHICS)
    other = essay("logic", days_old=1, tags=LOGIC)

    ranked = rank([first, second, other], Reader(), NOW)

    # Without diversity the logic essay (one day older) would be last.
    assert ranked[1].candidate.id == other.id


# --- Cold start (REC-02) ------------------------------------------------------


def test_cold_start_mixes_fresh_and_popular_and_new_essays_get_a_chance() -> None:
    hit = essay("hit", days_old=3, tags=ETHICS, bookmarks=50)
    quiet_old = essay("quiet-old", days_old=30, tags=LOGIC, bookmarks=1)
    brand_new = essay("brand-new", days_old=0, tags={"metaphysics": "Metaphysics"})

    ranked = rank([quiet_old, brand_new, hit], Reader(), NOW)

    assert order(ranked) == [hit.id, brand_new.id, quiet_old.id]
    assert ranked[0].reason == "Popular with readers"
    assert ranked[1].reason == "Recently published"


def test_empty_input_gives_empty_output() -> None:
    assert rank([], Reader(), NOW) == []


def naive_rank(candidates: list[Candidate], reader: Reader, now: datetime) -> list[uuid.UUID]:
    """The plain O(n²) greedy definition: every step scores every remaining essay."""
    from app.services.ranking import _total

    most = max((c.bookmarks for c in candidates), default=0)
    remaining, shown, order_ = list(candidates), set[str](), []

    def key(c: Candidate) -> tuple[float, datetime, uuid.UUID]:
        components = {
            "interest": tag_match(c, reader),
            "following": 1.0 if c.author_id in reader.following else 0.0,
            "popularity": popularity(c.bookmarks, most),
            "freshness": freshness(c.published_at, now),
            "diversity": diversity(c, shown),
        }
        return (_total(components), c.published_at, c.id)

    while remaining:
        best = max(remaining, key=key)
        order_.append(best.id)
        shown |= best.tags.keys()
        remaining.remove(best)
    return order_


@pytest.mark.parametrize("seed", range(20))
def test_fast_ranking_matches_the_plain_definition(seed: int) -> None:
    rnd = random.Random(seed)
    slugs = ["ethics", "logic", "stoicism", "metaphysics", "epistemology"]
    authors = [ANNA, BEA, CAL]
    essays = [
        essay(
            f"s{seed}-{n}",
            author=rnd.choice(authors),
            days_old=rnd.choice([0, 1, 2, 5, 30, rnd.random() * 90]),
            tags={t: t.title() for t in rnd.sample(slugs, rnd.randint(0, 3))},
            bookmarks=rnd.choice([0, 0, 1, 3, 10, 40]),
        )
        for n in range(rnd.randint(1, 60))
    ]
    reader = Reader(
        interests=frozenset(rnd.sample(slugs, rnd.randint(0, 2))),
        following=frozenset(rnd.sample(authors, rnd.randint(0, 2))),
    )

    assert order(rank(essays, reader, NOW)) == naive_rank(essays, reader, NOW)
