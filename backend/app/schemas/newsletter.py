from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.articles import AuthorBrief
from app.schemas.base import RequestModel
from app.schemas.users import Email


class SubscribeIn(RequestModel):
    email: Email


class SubscribeOut(BaseModel):
    message: str


class TokenIn(RequestModel):
    token: Annotated[str, Field(min_length=1, max_length=200)]


class ConfirmOut(BaseModel):
    author: AuthorBrief
