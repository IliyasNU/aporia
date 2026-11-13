"""Password hashing and session tokens."""

import hashlib
import hmac
import secrets
import uuid
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

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


def new_token() -> str:
    """256 bits of randomness, URL-safe: session cookies and confirmation links."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 is enough here: tokens are random, not human-chosen passwords.

    Only hashes are stored, so a leaked database does not leak usable tokens.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def unsubscribe_token(subscription_id: uuid.UUID) -> str:
    """The unsubscribe token for a newsletter subscription.

    Every email must carry a working unsubscribe link, but the database keeps
    only token hashes. So this token is derived from the subscription id with
    HMAC and SECRET_KEY: the worker can recreate it for each email, nobody
    without the key can forge it, and the database stores just its hash.
    """
    key = get_settings().secret_key.get_secret_value().encode()
    message = f"unsubscribe:{subscription_id}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()
