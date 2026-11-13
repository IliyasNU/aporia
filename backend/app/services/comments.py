"""Flat comments on published articles (SOC-02)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import Article, Comment, User
from app.services.visibility import comment_visible, publicly_visible


def _visible_article(db: Session, article_id: uuid.UUID) -> Article:
    article = db.scalar(select(Article).where(Article.id == article_id, publicly_visible()))
    if article is None:
        raise AppError(404, "not_found", "Article not found")
    return article


def list_comments(db: Session, article_id: uuid.UUID) -> list[Comment]:
    """Visible comments, oldest first. Comments of a non-public article are not shown."""
    _visible_article(db, article_id)
    return list(
        db.scalars(
            select(Comment)
            .options(joinedload(Comment.author))
            .where(Comment.article_id == article_id, comment_visible())
            .order_by(Comment.created_at, Comment.id)
        )
    )


def add_comment(db: Session, author: User, article_id: uuid.UUID, text: str) -> Comment:
    _visible_article(db, article_id)
    comment = Comment(user_id=author.id, article_id=article_id, text=text)
    db.add(comment)
    db.commit()
    return get_own_comment(db, comment.id, author)


def get_own_comment(db: Session, comment_id: uuid.UUID, user: User) -> Comment:
    comment = db.scalar(
        select(Comment)
        .options(joinedload(Comment.author))
        .where(Comment.id == comment_id, comment_visible())
    )
    if comment is None:
        raise AppError(404, "not_found", "Comment not found")
    if comment.user_id != user.id:
        raise AppError(403, "forbidden", "You can only change your own comments")
    return comment


def edit_comment(db: Session, comment: Comment, text: str) -> Comment:
    comment.text = text
    db.commit()
    return comment


def delete_comment(db: Session, comment: Comment) -> None:
    comment.deleted_at = datetime.now(UTC)
    db.commit()
