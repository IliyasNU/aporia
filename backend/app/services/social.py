"""Follows and bookmarks (SOC-01, SOC-02). Both are idempotent: repeating is harmless."""

import uuid

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Article, Bookmark, Follow, User
from app.services.articles import paginate
from app.services.visibility import publicly_visible

# --- Follows ------------------------------------------------------------------


def follow(db: Session, follower: User, author_id: uuid.UUID) -> None:
    if author_id == follower.id:
        raise AppError(400, "cannot_follow_self", "You cannot follow yourself")
    if db.get(User, author_id) is None:
        raise AppError(404, "not_found", "Author not found")
    # ON CONFLICT DO NOTHING: following twice (even concurrently) keeps one row.
    db.execute(
        insert(Follow).values(follower_id=follower.id, author_id=author_id).on_conflict_do_nothing()
    )
    db.commit()


def unfollow(db: Session, follower: User, author_id: uuid.UUID) -> None:
    db.execute(
        delete(Follow).where(Follow.follower_id == follower.id, Follow.author_id == author_id)
    )
    db.commit()


def is_following(db: Session, follower: User | None, author_id: uuid.UUID) -> bool:
    if follower is None:
        return False
    return bool(
        db.scalar(
            select(exists().where(Follow.follower_id == follower.id, Follow.author_id == author_id))
        )
    )


def list_following(db: Session, follower: User) -> list[Follow]:
    return list(
        db.scalars(
            select(Follow)
            .join(Follow.author)
            .where(Follow.follower_id == follower.id)
            .order_by(User.display_name, User.id)
        )
    )


def following_feed(
    db: Session, reader: User, *, page: int, page_size: int
) -> tuple[list[Article], int]:
    """Published articles by followed authors, newest publication first."""
    query = (
        select(Article)
        .join(Follow, Follow.author_id == Article.author_id)
        .where(Follow.follower_id == reader.id, publicly_visible())
        .order_by(Article.published_at.desc(), Article.id.desc())
    )
    return paginate(db, query, page, page_size)


# --- Bookmarks ----------------------------------------------------------------


def _visible_article(db: Session, article_id: uuid.UUID) -> Article:
    article = db.scalar(select(Article).where(Article.id == article_id, publicly_visible()))
    if article is None:
        raise AppError(404, "not_found", "Article not found")
    return article


def bookmark(db: Session, user: User, article_id: uuid.UUID) -> None:
    _visible_article(db, article_id)
    db.execute(
        insert(Bookmark).values(user_id=user.id, article_id=article_id).on_conflict_do_nothing()
    )
    db.commit()


def unbookmark(db: Session, user: User, article_id: uuid.UUID) -> None:
    db.execute(
        delete(Bookmark).where(Bookmark.user_id == user.id, Bookmark.article_id == article_id)
    )
    db.commit()


def is_bookmarked(db: Session, user: User | None, article_id: uuid.UUID) -> bool:
    if user is None:
        return False
    return bool(
        db.scalar(
            select(exists().where(Bookmark.user_id == user.id, Bookmark.article_id == article_id))
        )
    )


def list_bookmarks(
    db: Session, user: User, *, page: int, page_size: int
) -> tuple[list[Article], int]:
    """Saved articles that are still public, most recently saved first."""
    query = (
        select(Article)
        .join(Bookmark, Bookmark.article_id == Article.id)
        .where(Bookmark.user_id == user.id, publicly_visible())
        .order_by(Bookmark.created_at.desc(), Article.id.desc())
    )
    return paginate(db, query, page, page_size)
