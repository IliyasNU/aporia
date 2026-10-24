"""Request and response models for articles and tags (ART-01..03)."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.base import RequestModel
from app.schemas.users import TagOut

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
# Roughly 15 000 words: generous for an essay, small enough to bound a request.
Body = Annotated[str, Field(max_length=100_000)]
TagSlugs = Annotated[list[Annotated[str, Field(max_length=64)]], Field(max_length=5)]


class ArticleCreate(RequestModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    summary: Summary = ""
    body_markdown: Body = ""
    tags: TagSlugs = []


class ArticleUpdate(RequestModel):
    """PATCH semantics: omitted fields stay unchanged. Status changes use publish/unpublish."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    summary: Summary | None = None
    body_markdown: Body | None = None
    tags: TagSlugs | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "ArticleUpdate":
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class AuthorBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handle: str
    display_name: str


class ArticleListItem(BaseModel):
    """What article cards need: no body, so lists stay small."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    summary: str
    status: str
    author: AuthorBrief
    tags: list[TagOut]
    published_at: datetime | None
    updated_at: datetime


class ArticleOut(ArticleListItem):
    """Full article. body_markdown is raw Markdown: clients must render it safely."""

    body_markdown: str
    created_at: datetime
    # "hidden" when a moderator took it down; only its author still sees it.
    moderation_status: str


class ArticleDetail(ArticleOut):
    """An article as seen by the current visitor."""

    bookmarked_by_me: bool = False
    following_author: bool = False


class TagWithCount(TagOut):
    article_count: int
