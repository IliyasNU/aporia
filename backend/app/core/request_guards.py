"""Cheap checks on every request before any route code runs (SEC-03)."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.errors import error_response

Next = Callable[[Request], Awaitable[Response]]


async def limit_body_size(request: Request, call_next: Next) -> Response:
    """Refuse oversized requests early; nginx enforces the same limit for every body."""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > get_settings().max_body_bytes:
        return error_response(413, "Request body is too large", code="payload_too_large")
    return await call_next(request)


async def reject_nul_characters(request: Request, call_next: Next) -> Response:
    """NUL characters in the path or query string (e.g. %00) would only end in a
    database error; answer 422 right away. Bodies are checked by RequestModel."""
    if "\x00" in request.scope["path"] or b"%00" in request.scope["query_string"].lower():
        return error_response(422, "Request contains a NUL character", code="validation_error")
    return await call_next(request)
