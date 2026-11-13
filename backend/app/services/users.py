"""Profiles and topic interests (USER-01)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Tag, User
from app.schemas.users import ProfileUpdate
from app.services.tags import resolve_tags


def get_author_by_handle(db: Session, handle: str) -> User:
    user = db.scalar(select(User).where(User.handle == handle.lower()))
    if user is None:
        raise AppError(404, "not_found", "Author not found")
    return user


def update_profile(db: Session, user: User, changes: ProfileUpdate) -> User:
    for field, value in changes.model_dump(mode="json", exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    return user


def set_interests(db: Session, user: User, slugs: list[str]) -> list[Tag]:
    tags = resolve_tags(db, slugs)
    user.interests = tags
    db.commit()
    return tags
