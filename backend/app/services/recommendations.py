"""Loads the signals for the recommendation formula (REC-01, REC-02).

Four queries in total, whatever the number of candidates: candidates (with
authors and tags), bookmark counts, the reader's interests and follows.
No embeddings, no external services, no click tracking.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Article, Bookmark, Follow, Tag, User, user_interest_tags
from app.services.ranking import Candidate, Ranked, Reader, rank
from app.services.visibility import publicly_visible

# Only the newest public essays are considered; plenty for an MVP and it keeps
# the greedy diversity step cheap.
CANDIDATE_LIMIT = 300


def _reader(db: Session, user: User | None) -> Reader:
    if user is None:
        return Reader()
    interests = db.scalars(
        select(Tag.slug)
        .join(user_interest_tags, user_interest_tags.c.tag_id == Tag.id)
        .where(user_interest_tags.c.user_id == user.id)
    )
    following = db.scalars(select(Follow.author_id).where(Follow.follower_id == user.id))
    return Reader(interests=frozenset(interests), following=frozenset(following))


@dataclass
class Recommendations:
    ranked: list[Ranked]
    articles: dict[uuid.UUID, Article]
    cold_start: bool  # guest, or a reader without interests and follows (REC-02)


def recommend(db: Session, user: User | None) -> Recommendations:
    """All candidates, ranked. Excludes the reader's own essays and essays they saved."""
    query = select(Article).where(publicly_visible())
    if user is not None:
        saved = select(Bookmark.article_id).where(Bookmark.user_id == user.id)
        query = query.where(Article.author_id != user.id, Article.id.not_in(saved))
    articles = list(
        db.scalars(
            query.options(joinedload(Article.author), selectinload(Article.tags))
            .order_by(Article.published_at.desc(), Article.id.desc())
            .limit(CANDIDATE_LIMIT)
        )
    )
    counts: dict[uuid.UUID, int] = {}
    if articles:
        rows = db.execute(
            select(Bookmark.article_id, func.count())
            .where(Bookmark.article_id.in_([a.id for a in articles]))
            .group_by(Bookmark.article_id)
        )
        counts = {article_id: count for article_id, count in rows}

    reader = _reader(db, user)
    candidates = [
        Candidate(
            id=a.id,
            author_id=a.author_id,
            author_name=a.author.display_name,
            published_at=a.published_at or a.created_at,
            tags={t.slug: t.name for t in a.tags},
            bookmarks=counts.get(a.id, 0),
        )
        for a in articles
    ]
    return Recommendations(
        ranked=rank(candidates, reader, datetime.now(UTC)),
        articles={a.id: a for a in articles},
        cold_start=not reader.interests and not reader.following,
    )
