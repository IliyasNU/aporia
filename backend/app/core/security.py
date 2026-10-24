"""Password hashing and session tokens."""

import hashlib
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id with the library's recommended parameters (RFC 9106, low-memory profile).
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with older parameters than the current ones."""
    return _hasher.check_needs_rehash(password_hash)


@lru_cache
def _dummy_hash() -> str:
    return _hasher.hash("not-a-real-password")


def burn_password_check_time(password: str) -> None:
    """Spend as long as a real verification would, when no user matched the email.

    Without this, "unknown email" answers faster than "wrong password",
    which would let an attacker find out which emails have accounts.
    """
    verify_password(_dummy_hash(), password)


def new_session_token() -> str:
    """256 bits of randomness, URL-safe, for the session cookie."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """SHA-256 is enough here: the token is random, not a human-chosen password.

    Storing only the hash means a leaked database does not leak usable sessions.
    """
    return hashlib.sha256(token.encode()).hexdigest()
