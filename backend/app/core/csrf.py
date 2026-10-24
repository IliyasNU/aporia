"""CSRF protection: state-changing requests must come from a trusted origin (AUTH-02).

Browsers attach the session cookie to cross-site requests, so a malicious page
could otherwise submit a form to our API on the user's behalf. Browsers also
send an Origin header (or at least a Referer) with such requests, which a page
cannot forge. We reject unsafe methods whose Origin/Referer is not trusted.

Requests without either header do not come from a browser form or fetch
(e.g. curl or tests), so they cannot carry a victim's cookie and are allowed.
SameSite=Lax on the session cookie is a second, independent layer.
"""

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.errors import error_response

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def request_origin(request: Request) -> str | None:
    """The browser-reported origin of the request, or None for non-browser clients."""
    origin = request.headers.get("origin")
    if origin is not None:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer is not None:
        return _origin_of(referer)
    return None


async def csrf_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if request.method not in SAFE_METHODS:
        origin = request_origin(request)
        if origin is not None and origin not in get_settings().trusted_origins:
            return error_response(403, "Cross-site request blocked", code="csrf_failed")
    return await call_next(request)
