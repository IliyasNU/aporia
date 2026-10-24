import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, OptionalUser
from app.db.session import DbSession
from app.schemas.errors import error_responses
from app.schemas.users import AuthorOut, AuthorProfile
from app.services import social, users

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/{handle}", response_model=AuthorProfile, responses=error_responses(404))
def get_author(handle: str, db: DbSession, viewer: OptionalUser) -> AuthorProfile:
    """Public author profile. Visible without signing in."""
    author = users.get_author_by_handle(db, handle)
    return AuthorProfile(
        **AuthorOut.model_validate(author).model_dump(),
        followed_by_me=social.is_following(db, viewer, author.id),
    )


@router.post(
    "/{author_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(400, 401, 403, 404),
)
def follow_author(author_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Follow an author. Following again changes nothing."""
    social.follow(db, user, author_id)


@router.delete(
    "/{author_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403),
)
def unfollow_author(author_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    """Stop following an author. Safe to repeat."""
    social.unfollow(db, user, author_id)
