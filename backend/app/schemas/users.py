"""Request and response models for accounts, profiles and interests.

Length limits here are the server-side input limits (SEC-03); they match the
column sizes in app/models/user.py.
"""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    UrlConstraints,
    model_validator,
)

Email = Annotated[EmailStr, Field(max_length=254), AfterValidator(str.lower)]
# Long passphrases are welcome; the upper bound only stops absurd payloads.
Password = Annotated[str, Field(min_length=8, max_length=128)]
Handle = Annotated[
    str,
    # Pydantic checks the pattern before lower-casing, hence A-Z in the pattern.
    StringConstraints(strip_whitespace=True, to_lower=True, pattern=r"^[A-Za-z0-9_]{3,30}$"),
    Field(description="3-30 letters, digits or underscores; stored in lowercase."),
]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Bio = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
# HttpUrl only accepts http(s), so "javascript:" links cannot be stored.
Website = Annotated[HttpUrl, UrlConstraints(max_length=200)]


class RegisterRequest(BaseModel):
    email: Email
    password: Password
    handle: Handle
    display_name: DisplayName


class LoginRequest(BaseModel):
    email: Email
    # No minimum here: a wrong password must get the same 401 as any other.
    password: Annotated[str, Field(max_length=128)]


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str


class AuthorOut(BaseModel):
    """Public profile: never includes email, role or interests."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handle: str
    display_name: str
    bio: str
    website: str | None
    created_at: datetime


class MeOut(AuthorOut):
    """The signed-in user's own account."""

    email: str
    role: str
    interests: list[TagOut]


class ProfileUpdate(BaseModel):
    """PATCH semantics: omitted fields stay unchanged; website=null removes it."""

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    bio: Bio | None = None
    website: Website | None = None

    @model_validator(mode="after")
    def only_website_can_be_null(self) -> "ProfileUpdate":
        for field in ("display_name", "bio"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class InterestsUpdate(BaseModel):
    tags: Annotated[list[Annotated[str, Field(max_length=64)]], Field(max_length=50)] = Field(
        description="Tag slugs. Replaces the whole list; an empty list clears it."
    )


class InterestsOut(BaseModel):
    interests: list[TagOut]
