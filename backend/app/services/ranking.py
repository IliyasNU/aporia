"""The recommendation formula (REC-01, REC-03). Pure Python: no database, no clock.

    score = 0.40 * tag_match    # share of the essay's tags the reader is interested in
          + 0.25 * following    # 1 if the reader follows the author
          + 0.15 * popularity   # log1p(bookmarks), divided by the best candidate's value
          + 0.15 * freshness    # exp(-age_days / 30)
          + 0.05 * diversity    # share of the essay's tags not already shown above it

Order: score DESC, published_at DESC, id DESC, so equal scores always come out in
the same order. Every input arrives as plain data, which makes the function easy
to test with fixed examples.
"""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime

WEIGHTS = {
    "interest": 0.40,
    "following": 0.25,
    "popularity": 0.15,
    "freshness": 0.15,
    "diversity": 0.05,
}
FRESHNESS_DAYS = 30


@dataclass(frozen=True)
class Candidate:
    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    published_at: datetime
    tags: dict[str, str]  # slug -> display name
    bookmarks: int


@dataclass(frozen=True)
class Reader:
    """What we know about the reader. Empty for guests (cold start)."""

    interests: frozenset[str] = frozenset()  # tag slugs
    following: frozenset[uuid.UUID] = frozenset()  # author ids


@dataclass(frozen=True)
class Ranked:
    candidate: Candidate
    score: float
    components: dict[str, float]  # each in [0, 1], before weighting
    reason: str


def tag_match(candidate: Candidate, reader: Reader) -> float:
    if not candidate.tags or not reader.interests:
        return 0.0
    return len(candidate.tags.keys() & reader.interests) / len(candidate.tags)


def popularity(bookmarks: int, most_bookmarks: int) -> float:
    # log1p dampens runaway hits: 1000 bookmarks is not 100x better than 10.
    if most_bookmarks <= 0:
        return 0.0
    return math.log1p(bookmarks) / math.log1p(most_bookmarks)


def freshness(published_at: datetime, now: datetime) -> float:
    age_days = max((now - published_at).total_seconds() / 86_400, 0.0)
    return math.exp(-age_days / FRESHNESS_DAYS)


def diversity(candidate: Candidate, shown_tags: set[str]) -> float:
    if not candidate.tags:
        return 0.0
    return len(candidate.tags.keys() - shown_tags) / len(candidate.tags)


def explain(candidate: Candidate, components: dict[str, float], reader: Reader) -> str:
    """The single biggest weighted reason, phrased for people."""
    contributions = [
        (WEIGHTS["following"] * components["following"], "following"),
        (WEIGHTS["interest"] * components["interest"], "interest"),
        (WEIGHTS["popularity"] * components["popularity"], "popularity"),
        (WEIGHTS["freshness"] * components["freshness"], "freshness"),
    ]
    # max() keeps the first of equal values, so the list order is the tie-breaker.
    value, kind = max(contributions, key=lambda item: item[0])
    if kind == "following" and value > 0:
        return f"You follow {candidate.author_name}"
    if kind == "interest" and value > 0:
        names = sorted(name for slug, name in candidate.tags.items() if slug in reader.interests)
        return f"You are interested in {', '.join(names)}"
    if kind == "popularity" and value > 0:
        return "Popular with readers"
    return "Recently published"


def rank(candidates: list[Candidate], reader: Reader, now: datetime) -> list[Ranked]:
    """Score and order all candidates.

    Diversity depends on what is already above an essay, so the list is built
    greedily: at each step the candidate with the best total score (including
    its diversity against the essays chosen so far) goes next.
    """
    most_bookmarks = max((c.bookmarks for c in candidates), default=0)
    base: dict[uuid.UUID, dict[str, float]] = {
        c.id: {
            "interest": tag_match(c, reader),
            "following": 1.0 if c.author_id in reader.following else 0.0,
            "popularity": popularity(c.bookmarks, most_bookmarks),
            "freshness": freshness(c.published_at, now),
        }
        for c in candidates
    }

    def total(components: dict[str, float]) -> float:
        return round(sum(WEIGHTS[name] * value for name, value in components.items()), 9)

    remaining = list(candidates)
    shown_tags: set[str] = set()
    ranked: list[Ranked] = []
    while remaining:
        scored = [(c, {**base[c.id], "diversity": diversity(c, shown_tags)}) for c in remaining]
        best, components = max(
            scored, key=lambda item: (total(item[1]), item[0].published_at, item[0].id)
        )
        ranked.append(
            Ranked(best, total(components), components, explain(best, components, reader))
        )
        shown_tags |= best.tags.keys()
        remaining.remove(best)
    return ranked
