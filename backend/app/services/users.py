"""Profiles and topic interests (USER-01)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Tag, User
from app.schemas.users import ProfileUpdate


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
    wanted = {slug.strip().lower() for slug in slugs}
    tags = list(db.scalars(select(Tag).where(Tag.slug.in_(wanted)).order_by(Tag.slug)))

    unknown = wanted - {tag.slug for tag in tags}
    if unknown:
        raise AppError(422, "unknown_tags", f"Unknown tags: {', '.join(sorted(unknown))}")

    user.interests = tags
    db.commit()
    return tags
