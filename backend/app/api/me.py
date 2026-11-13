from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.db.session import DbSession
from app.schemas.errors import error_responses
from app.schemas.users import InterestsOut, InterestsUpdate, MeOut, ProfileUpdate, TagOut
from app.services import users

router = APIRouter(prefix="/me", tags=["me"])


@router.patch("/profile", response_model=MeOut, responses=error_responses(401, 403, 422))
def update_profile(changes: ProfileUpdate, user: CurrentUser, db: DbSession) -> MeOut:
    """Edit your own display name, bio and website. Only the fields sent are changed."""
    return MeOut.model_validate(users.update_profile(db, user, changes))


@router.put("/interests", response_model=InterestsOut, responses=error_responses(401, 403, 422))
def replace_interests(data: InterestsUpdate, user: CurrentUser, db: DbSession) -> InterestsOut:
    """Replace your list of topic interests (tag slugs, e.g. "ethics")."""
    tags = users.set_interests(db, user, data.tags)
    return InterestsOut(interests=[TagOut.model_validate(tag) for tag in tags])
