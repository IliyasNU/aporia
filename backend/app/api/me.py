import uuid

from fastapi import APIRouter

from app.api.articles import PageNumber, PageSize
from app.api.deps import CurrentUser
from app.db.session import DbSession
from app.schemas.articles import ArticleListItem, ArticleOut
from app.schemas.common import Page
from app.schemas.errors import error_responses
from app.schemas.users import InterestsOut, InterestsUpdate, MeOut, ProfileUpdate, TagOut
from app.services import articles, users

router = APIRouter(prefix="/me", tags=["me"])


@router.patch("/profile", response_model=MeOut, responses=error_responses(401, 403, 422))
def update_profile(changes: ProfileUpdate, user: CurrentUser, db: DbSession) -> MeOut:
    """Edit your own display name, bio and website. Only the fields sent are changed."""
    return MeOut.model_validate(users.update_profile(db, user, changes))


@router.put("/interests", response_model=InterestsOut, responses=error_responses(401, 403, 422))
def replace_interests(data: InterestsUpdate, user: CurrentUser, db: DbSession) -> InterestsOut:
    """Replace your list of topic interests (tag slugs, e.g. "ethics")."""
    tags = users.set_interests(db, user, data.tags)
    return InterestsOut(interests=[TagOut.model_validate(tag) for tag in tags])


@router.get("/articles", response_model=Page[ArticleListItem], responses=error_responses(401))
def my_articles(
    user: CurrentUser, db: DbSession, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[ArticleListItem]:
    """Your articles in every status (draft, published, unpublished), recently edited first."""
    items, total = articles.list_own_articles(db, user, page=page, page_size=page_size)
    return Page(
        items=[ArticleListItem.model_validate(a) for a in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/articles/{article_id}", response_model=ArticleOut, responses=error_responses(401, 403, 404)
)
def my_article(article_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ArticleOut:
    """One of your articles by id, in any status: what the editor loads."""
    return ArticleOut.model_validate(articles.get_own_article(db, article_id, user))
