from fastapi import APIRouter

from app.api.articles import PageNumber, PageSize
from app.api.deps import OptionalUser
from app.db.session import DbSession
from app.schemas.articles import ArticleListItem
from app.schemas.errors import error_responses
from app.schemas.recommendations import Recommendation, RecommendationPage
from app.services.recommendations import recommend

router = APIRouter(tags=["feed"])


@router.get("/feed/recommended", response_model=RecommendationPage, responses=error_responses(422))
def recommended(
    db: DbSession, viewer: OptionalUser, page: PageNumber = 1, page_size: PageSize = 20
) -> RecommendationPage:
    """Essays picked for you, each with the reason it was picked.

    Signed-in readers get interest, follow, popularity, freshness and diversity
    signals; guests and readers without interests or follows get fresh and
    popular essays (cold start). Your own and already saved essays are left out.
    """
    result = recommend(db, viewer)
    window = result.ranked[(page - 1) * page_size : page * page_size]
    return RecommendationPage(
        items=[
            Recommendation(
                article=ArticleListItem.model_validate(result.articles[r.candidate.id]),
                reason=r.reason,
                score=round(r.score, 4),
            )
            for r in window
        ],
        page=page,
        page_size=page_size,
        total=len(result.ranked),
        cold_start=result.cold_start,
    )
