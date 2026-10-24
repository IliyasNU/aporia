from typing import Any

from pydantic import BaseModel, field_validator


def _has_nul(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, list):
        return any(_has_nul(item) for item in value)
    return False


class RequestModel(BaseModel):
    """Base for every request body.

    PostgreSQL text cannot store NUL characters, so they are refused up front
    with a 422 instead of failing later as a database error.
    """

    @field_validator("*", mode="before")
    @classmethod
    def no_nul_characters(cls, value: Any) -> Any:
        if _has_nul(value):
            raise ValueError("must not contain NUL characters")
        return value
