from fastapi import APIRouter

from app.db.session import DbSession
from app.schemas.errors import error_responses
from app.schemas.users import AuthorOut
from app.services import users

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/{handle}", response_model=AuthorOut, responses=error_responses(404))
def get_author(handle: str, db: DbSession) -> AuthorOut:
    """Public author profile. Visible without signing in."""
    return AuthorOut.model_validate(users.get_author_by_handle(db, handle))
