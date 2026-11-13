"""Shared dependencies for routers: the session cookie and the current user."""

from typing import Annotated

from fastapi import Depends, Request, Response

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import DbSession
from app.models import User
from app.services.auth import find_active_session

SESSION_COOKIE = "aporia_session"


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
        httponly=True,  # not readable from JavaScript, so XSS cannot steal it
        samesite="lax",  # not sent with cross-site POSTs
        secure=settings.session_cookie_secure,  # HTTPS only in production
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


def get_optional_user(request: Request, db: DbSession) -> User | None:
    """The signed-in user, or None for guests (and for invalid sessions)."""
    token = request.cookies.get(SESSION_COOKIE)
    session = find_active_session(db, token) if token else None
    return session.user if session else None


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    """The signed-in user, or 401 for a missing, unknown, revoked or expired session."""
    if user is None:
        raise AppError(401, "not_authenticated", "Sign in to continue")
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]
