import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, OptionalUser
from app.db.session import DbSession
from app.schemas.articles import (
    ArticleCreate,
    ArticleDetail,
    ArticleListItem,
    ArticleOut,
    ArticleUpdate,
)
from app.schemas.common import Page
from app.schemas.errors import error_responses
from app.services import articles, social
from app.services.articles import ArticleSort

router = APIRouter(prefix="/articles", tags=["articles"])

PageNumber = Annotated[int, Query(ge=1, le=10_000)]
PageSize = Annotated[int, Query(ge=1, le=50)]


@router.get("", response_model=Page[ArticleListItem], responses=error_responses(422))
def list_articles(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100, description="Search title and summary")] = None,
    tag: Annotated[str | None, Query(max_length=64, description="Tag slug")] = None,
    author: Annotated[str | None, Query(max_length=30, description="Author handle")] = None,
    sort: ArticleSort = "latest",
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> Page[ArticleListItem]:
    """Public catalog: newest first, or most bookmarked first with sort=popular."""
    items, total = articles.list_public_articles(
        db, q=q, tag=tag, author=author, sort=sort, page=page, page_size=page_size
    )
    return Page(
        items=[ArticleListItem.model_validate(a) for a in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{slug}", response_model=ArticleDetail, responses=error_responses(404))
def get_article(slug: str, db: DbSession, viewer: OptionalUser) -> ArticleDetail:
    """A published article. Its author can also open it while it is a draft, unpublished
    or hidden by a moderator."""
    article = articles.get_article_by_slug(db, slug, viewer)
    return ArticleDetail(
        **ArticleOut.model_validate(article).model_dump(),
        bookmarked_by_me=social.is_bookmarked(db, viewer, article.id),
        following_author=social.is_following(db, viewer, article.author_id),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ArticleOut,
    responses=error_responses(401, 403, 422),
)
def create_article(data: ArticleCreate, user: CurrentUser, db: DbSession) -> ArticleOut:
    """Create a draft. Nobody else sees it until it is published."""
    return ArticleOut.model_validate(articles.create_article(db, user, data))


@router.patch(
    "/{article_id}", response_model=ArticleOut, responses=error_responses(401, 403, 404, 422)
)
def update_article(
    article_id: uuid.UUID, changes: ArticleUpdate, user: CurrentUser, db: DbSession
) -> ArticleOut:
    """Edit your own article. After the first publication the slug no longer changes."""
    article = articles.get_own_article(db, article_id, user)
    return ArticleOut.model_validate(articles.update_article(db, article, changes))


@router.post(
    "/{article_id}/publish",
    response_model=ArticleOut,
    responses=error_responses(401, 403, 404, 422),
)
def publish_article(article_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ArticleOut:
    """Make your article public. Publishing an already published article changes nothing."""
    article = articles.get_own_article(db, article_id, user)
    articles.publish_article(db, article)
    return ArticleOut.model_validate(article)


@router.post(
    "/{article_id}/unpublish",
    response_model=ArticleOut,
    responses=error_responses(400, 401, 403, 404),
)
def unpublish_article(article_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ArticleOut:
    """Take your article down. It disappears from lists and search; you can republish it."""
    article = articles.get_own_article(db, article_id, user)
    articles.unpublish_article(db, article)
    return ArticleOut.model_validate(article)


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_article(article_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Delete your article (soft delete: it disappears for everyone, including you)."""
    articles.delete_article(db, articles.get_own_article(db, article_id, user))
