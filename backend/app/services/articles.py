"""Writing, publishing and reading articles (ART-01, ART-02, ART-03)."""

import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import AppError
from app.models import Article, ArticleStatus, Bookmark, ModerationStatus, Tag, User
from app.schemas.articles import ArticleCreate, ArticleUpdate
from app.services.tags import resolve_tags
from app.services.visibility import publicly_visible

ArticleSort = Literal["latest", "popular"]

# --- Slugs ------------------------------------------------------------------


def slugify(title: str) -> str:
    """'The Myth of Sisyphus!' -> 'the-myth-of-sisyphus'. Keeps non-Latin letters."""
    slug = re.sub(r"[\W_]+", "-", title.lower()).strip("-")
    return slug[:80].rstrip("-") or "article"


def _unique_slug(db: Session, title: str, article_id: uuid.UUID | None = None) -> str:
    base = slugify(title)
    candidate = base
    while db.scalar(select(Article.id).where(Article.slug == candidate, Article.id != article_id)):
        candidate = f"{base}-{secrets.token_hex(3)}"
    return candidate


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        # Only possible if two requests picked the same new slug at the same moment.
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_articles_slug":
            raise AppError(409, "slug_conflict", "Please try again") from None
        raise


# --- Loading with permission checks ------------------------------------------


def _with_relations[T: Select](query: T) -> T:
    # Author and tags in a fixed number of queries, however many articles (no N+1).
    return query.options(joinedload(Article.author), selectinload(Article.tags))


def get_own_article(db: Session, article_id: uuid.UUID, user: User) -> Article:
    """An article the user may edit: 404 if missing or deleted, 403 if someone else's."""
    article = db.scalar(_with_relations(select(Article).where(Article.id == article_id)))
    if article is None or article.deleted_at is not None:
        raise AppError(404, "not_found", "Article not found")
    if article.author_id != user.id:
        raise AppError(403, "forbidden", "You can only change your own articles")
    return article


def get_article_by_slug(db: Session, slug: str, viewer: User | None) -> Article:
    """Published articles for everyone; drafts, unpublished and hidden ones only for their author.

    Anyone else gets 404, so the existence of a draft is not revealed.
    """
    article = db.scalar(
        _with_relations(select(Article).where(Article.slug == slug, Article.deleted_at.is_(None)))
    )
    if article is None:
        raise AppError(404, "not_found", "Article not found")
    is_author = viewer is not None and viewer.id == article.author_id
    is_public = (
        article.status == ArticleStatus.PUBLISHED
        and article.moderation_status == ModerationStatus.VISIBLE
    )
    if not is_public and not is_author:
        raise AppError(404, "not_found", "Article not found")
    return article


# --- Writing ------------------------------------------------------------------


def create_article(db: Session, author: User, data: ArticleCreate) -> Article:
    article = Article(
        author_id=author.id,
        title=data.title,
        slug=_unique_slug(db, data.title),
        summary=data.summary,
        body_markdown=data.body_markdown,
        status=ArticleStatus.DRAFT,
        tags=resolve_tags(db, data.tags),
    )
    db.add(article)
    _commit(db)
    return get_own_article(db, article.id, author)


def update_article(db: Session, article: Article, changes: ArticleUpdate) -> Article:
    """Edit any field; editing never re-sends notifications (US-07)."""
    data = changes.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in data.items():
        setattr(article, field, value)
    if "title" in data and article.published_at is None:
        article.slug = _unique_slug(db, article.title, article.id)
    if changes.tags is not None:
        article.tags = resolve_tags(db, changes.tags)
    _commit(db)
    return article


def publish_article(db: Session, article: Article) -> bool:
    """Make the article public. Returns True only for its very first publication."""
    if not article.body_markdown.strip():
        raise AppError(422, "empty_body", "Write something before publishing")
    if article.status == ArticleStatus.PUBLISHED:
        return False
    first_publication = article.published_at is None
    article.status = ArticleStatus.PUBLISHED
    if first_publication:
        article.published_at = datetime.now(UTC)
    _commit(db)
    return first_publication


def unpublish_article(db: Session, article: Article) -> None:
    if article.status != ArticleStatus.PUBLISHED:
        raise AppError(400, "invalid_state", "Only a published article can be unpublished")
    article.status = ArticleStatus.UNPUBLISHED
    _commit(db)


def delete_article(db: Session, article: Article) -> None:
    """Soft delete: hidden from everyone, including the author, but kept in the database."""
    article.deleted_at = datetime.now(UTC)
    _commit(db)


# --- Lists ----------------------------------------------------------------------


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def paginate(
    db: Session, query: Select[tuple[Article]], page: int, page_size: int
) -> tuple[list[Article], int]:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    items = db.scalars(_with_relations(query).limit(page_size).offset((page - 1) * page_size)).all()
    return list(items), total


def list_public_articles(
    db: Session,
    *,
    q: str | None,
    tag: str | None,
    author: str | None,
    sort: ArticleSort,
    page: int,
    page_size: int,
) -> tuple[list[Article], int]:
    query = select(Article).where(publicly_visible())
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        query = query.where(
            or_(
                Article.title.ilike(pattern, escape="\\"),
                Article.summary.ilike(pattern, escape="\\"),
            )
        )
    if tag:
        query = query.where(Article.tags.any(Tag.slug == tag.strip().lower()))
    if author:
        query = query.join(Article.author).where(User.handle == author.strip().lower())
    if sort == "popular":
        # Most bookmarked first; ties fall back to the newest.
        bookmarks = (
            select(func.count())
            .where(Bookmark.article_id == Article.id)
            .correlate(Article)
            .scalar_subquery()
        )
        query = query.order_by(bookmarks.desc())
    # The id makes the order stable for equal timestamps.
    query = query.order_by(Article.published_at.desc(), Article.id.desc())
    return paginate(db, query, page, page_size)


def list_own_articles(
    db: Session, user: User, *, page: int, page_size: int
) -> tuple[list[Article], int]:
    query = (
        select(Article)
        .where(Article.author_id == user.id, Article.deleted_at.is_(None))
        .order_by(Article.updated_at.desc(), Article.id.desc())
    )
    return paginate(db, query, page, page_size)
