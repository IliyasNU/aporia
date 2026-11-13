"""Bookmarks, comments, the following feed and the user's own lists."""

import uuid

from fastapi import APIRouter, status

from app.api.articles import PageNumber, PageSize
from app.api.deps import CurrentUser
from app.core import rate_limit
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.schemas.articles import ArticleListItem
from app.schemas.common import Page
from app.schemas.errors import error_responses
from app.schemas.social import CommentIn, CommentOut, FollowedAuthor
from app.services import comments, social

router = APIRouter(tags=["social"])


def _page(items: list, total: int, page: int, page_size: int) -> Page[ArticleListItem]:
    return Page(
        items=[ArticleListItem.model_validate(a) for a in items],
        page=page,
        page_size=page_size,
        total=total,
    )


# --- Following ------------------------------------------------------------------


@router.get("/me/following", response_model=list[FollowedAuthor], responses=error_responses(401))
def my_following(user: CurrentUser, db: DbSession) -> list[FollowedAuthor]:
    """Authors you follow, by name."""
    return [FollowedAuthor.model_validate(f) for f in social.list_following(db, user)]


@router.get("/feed/following", response_model=Page[ArticleListItem], responses=error_responses(401))
def following_feed(
    user: CurrentUser, db: DbSession, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[ArticleListItem]:
    """New essays by the authors you follow, newest first."""
    items, total = social.following_feed(db, user, page=page, page_size=page_size)
    return _page(items, total, page, page_size)


# --- Bookmarks ------------------------------------------------------------------


@router.post(
    "/articles/{article_id}/bookmark",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def add_bookmark(article_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Save a published article. Saving again changes nothing."""
    social.bookmark(db, user, article_id)


@router.delete(
    "/articles/{article_id}/bookmark",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403),
)
def remove_bookmark(article_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Remove a saved article. Safe to repeat."""
    social.unbookmark(db, user, article_id)


@router.get("/me/bookmarks", response_model=Page[ArticleListItem], responses=error_responses(401))
def my_bookmarks(
    user: CurrentUser, db: DbSession, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[ArticleListItem]:
    """Your saved articles that are still public, most recently saved first."""
    items, total = social.list_bookmarks(db, user, page=page, page_size=page_size)
    return _page(items, total, page, page_size)


# --- Comments -------------------------------------------------------------------


@router.get(
    "/articles/{article_id}/comments",
    response_model=list[CommentOut],
    responses=error_responses(404),
)
def list_comments(article_id: uuid.UUID, db: DbSession) -> list[CommentOut]:
    """Comments on a published article, oldest first."""
    return [CommentOut.model_validate(c) for c in comments.list_comments(db, article_id)]


@router.post(
    "/articles/{article_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentOut,
    responses=error_responses(401, 403, 404, 422, 429),
)
def add_comment(
    article_id: uuid.UUID, data: CommentIn, user: CurrentUser, db: DbSession
) -> CommentOut:
    """Comment on a published article (plain text, up to 2000 characters)."""
    limiter.hit(rate_limit.COMMENT, str(user.id))
    return CommentOut.model_validate(comments.add_comment(db, user, article_id, data.text))


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentOut,
    responses=error_responses(401, 403, 404, 422),
)
def edit_comment(
    comment_id: uuid.UUID, data: CommentIn, user: CurrentUser, db: DbSession
) -> CommentOut:
    """Edit your own comment."""
    comment = comments.get_own_comment(db, comment_id, user)
    return CommentOut.model_validate(comments.edit_comment(db, comment, data.text))


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_comment(comment_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Delete your own comment."""
    comments.delete_comment(db, comments.get_own_comment(db, comment_id, user))
