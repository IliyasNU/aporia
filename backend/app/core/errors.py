"""Uniform JSON error responses: {"error": {"code": ..., "message": ...}}.

Clients get a stable machine-readable code and a human-readable message,
never stack traces or other internal details.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorBody, ErrorResponse, ValidationIssue

logger = logging.getLogger(__name__)

ERROR_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


def error_response(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: list[ValidationIssue] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code or ERROR_CODES.get(status_code, "error"),
            message=message,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers=headers,
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return error_response(exc.status_code, message, headers=exc.headers)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Only location, message and type are returned: Pydantic's "input" field
    # would echo submitted values (e.g. passwords) back to the client.
    details = [
        ValidationIssue(
            loc=[str(part) for part in error.get("loc", ())],
            msg=error.get("msg", ""),
            type=error.get("type", ""),
        )
        for error in exc.errors()
    ]
    return error_response(422, "Request validation failed", details=details)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "Internal server error")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
