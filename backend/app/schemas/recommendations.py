from pydantic import BaseModel

from app.schemas.articles import ArticleListItem


class Recommendation(BaseModel):
    article: ArticleListItem
    # Why this essay is here, e.g. "You follow Simone Weil" (REC-03).
    reason: str
    # The formula's result in [0, 1]; shown for transparency, clients may ignore it.
    score: float


class RecommendationPage(BaseModel):
    items: list[Recommendation]
    page: int
    page_size: int
    total: int
    # True for guests and readers without interests or follows: fresh and popular essays.
    cold_start: bool
