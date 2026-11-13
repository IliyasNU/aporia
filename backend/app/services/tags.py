"""The curated tag catalog (ART-03). Tags are seeded by migrations, never created by users."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Article, Tag, article_tags
from app.services.visibility import publicly_visible


def resolve_tags(db: Session, slugs: list[str]) -> list[Tag]:
    """Turn slugs into Tag rows; 422 if any slug is not in the catalog."""
    wanted = {slug.strip().lower() for slug in slugs}
    tags = list(db.scalars(select(Tag).where(Tag.slug.in_(wanted)).order_by(Tag.slug)))
    unknown = wanted - {tag.slug for tag in tags}
    if unknown:
        raise AppError(422, "unknown_tags", f"Unknown tags: {', '.join(sorted(unknown))}")
    return tags


def list_tags_with_counts(db: Session) -> list[tuple[Tag, int]]:
    """Every tag with the number of publicly visible articles using it."""
    counts = (
        select(article_tags.c.tag_id, func.count().label("article_count"))
        .join(Article, Article.id == article_tags.c.article_id)
        .where(publicly_visible())
        .group_by(article_tags.c.tag_id)
        .subquery()
    )
    rows = db.execute(
        select(Tag, func.coalesce(counts.c.article_count, 0))
        .outerjoin(counts, counts.c.tag_id == Tag.id)
        .order_by(Tag.name)
    )
    return [(tag, count) for tag, count in rows]
