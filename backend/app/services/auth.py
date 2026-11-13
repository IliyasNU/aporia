"""Registration, login and server-side sessions (AUTH-01, AUTH-02)."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    burn_password_check_time,
    hash_password,
    hash_token,
    new_token,
    password_needs_rehash,
    verify_password,
)
from app.models import User, UserSession
from app.schemas.users import LoginRequest, RegisterRequest

logger = logging.getLogger(__name__)

# Which unique constraint failed → (error code, message) for the client.
_DUPLICATE_ERRORS = {
    "uq_users_email": ("email_taken", "An account with this email already exists"),
    "uq_users_handle": ("handle_taken", "This handle is already taken"),
}


def register_user(db: Session, data: RegisterRequest) -> User:
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        handle=data.handle,
        display_name=data.display_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        # The unique constraints are the source of truth, which also covers
        # two registrations with the same email arriving at the same time.
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint in _DUPLICATE_ERRORS:
            code, message = _DUPLICATE_ERRORS[constraint]
            raise AppError(409, code, message) from None
        raise
    logger.info("Registered user %s", user.id)
    return user


def authenticate(db: Session, data: LoginRequest) -> User:
    """Return the user for valid credentials, otherwise raise a 401.

    Unknown email and wrong password give the same answer, in about the same
    time, so the endpoint does not reveal which emails have accounts.
    """
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None:
        burn_password_check_time(data.password)
        raise AppError(401, "invalid_credentials", "Invalid email or password")
    if not verify_password(user.password_hash, data.password):
        raise AppError(401, "invalid_credentials", "Invalid email or password")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
        db.commit()
    return user


def create_session(db: Session, user: User) -> str:
    """Store a new session and return the raw token for the cookie (never stored)."""
    token = new_token()
    expires_at = datetime.now(UTC) + timedelta(days=get_settings().session_ttl_days)
    db.add(UserSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
    db.commit()
    return token


def find_active_session(db: Session, token: str) -> UserSession | None:
    """The session for this cookie token, unless it is unknown, revoked or expired."""
    return db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
    )


def revoke_session(db: Session, token: str) -> None:
    session = find_active_session(db, token)
    if session is not None:
        session.revoked_at = datetime.now(UTC)
        db.commit()
