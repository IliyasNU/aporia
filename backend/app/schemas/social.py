"""Request and response models for follows, comments and moderation."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models import ReportTarget
from app.schemas.articles import AuthorBrief

CommentText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class FollowedAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    author: AuthorBrief
    created_at: datetime


class CommentIn(BaseModel):
    text: CommentText


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    author: AuthorBrief
    text: str
    created_at: datetime
    updated_at: datetime


class ReportIn(BaseModel):
    target_type: ReportTarget
    target_id: uuid.UUID
    reason: Reason


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    reason: str
    status: str
    created_at: datetime


class ModerationIn(BaseModel):
    target_type: ReportTarget
    target_id: uuid.UUID
    action: Literal["hide", "unhide"]


class ModerationOut(BaseModel):
    target_type: str
    target_id: uuid.UUID
    moderation_status: str
