from fastapi import APIRouter, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    SESSION_COOKIE,
    AppSettings,
    CurrentUser,
    clear_session_cookie,
    set_session_cookie,
)
from app.core.config import Settings
from app.db.session import DbSession
from app.models import User
from app.schemas.errors import error_responses
from app.schemas.users import LoginRequest, MeOut, RegisterRequest
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def start_session(
    db: Session, user: User, request: Request, response: Response, settings: Settings
) -> None:
    """Issue a fresh session cookie, ending this browser's previous session if any."""
    if old_token := request.cookies.get(SESSION_COOKIE):
        auth.revoke_session(db, old_token)
    set_session_cookie(response, auth.create_session(db, user), settings)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=MeOut,
    responses=error_responses(403, 409, 422),
)
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
) -> MeOut:
    """Create an account and sign in (sets the session cookie)."""
    user = auth.register_user(db, data)
    start_session(db, user, request, response, settings)
    return MeOut.model_validate(user)


@router.post("/login", response_model=MeOut, responses=error_responses(401, 403, 422))
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
) -> MeOut:
    """Sign in with email and password (sets the session cookie)."""
    user = auth.authenticate(db, data)
    start_session(db, user, request, response, settings)
    return MeOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(403))
def logout(request: Request, response: Response, db: DbSession, settings: AppSettings) -> None:
    """End the current session. Safe to call when already signed out."""
    if token := request.cookies.get(SESSION_COOKIE):
        auth.revoke_session(db, token)
    clear_session_cookie(response, settings)


@router.get("/me", response_model=MeOut, responses=error_responses(401))
def me(user: CurrentUser) -> MeOut:
    """The signed-in user's account, including email and interests."""
    return MeOut.model_validate(user)
