from fastapi import APIRouter

from app.db.session import DbSession
from app.schemas.articles import TagWithCount
from app.services import tags

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagWithCount])
def list_tags(db: DbSession) -> list[TagWithCount]:
    """The whole tag catalog, with the number of published articles per tag."""
    return [
        TagWithCount(slug=tag.slug, name=tag.name, article_count=count)
        for tag, count in tags.list_tags_with_counts(db)
    ]
