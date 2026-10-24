from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.api.router import API_PREFIX, api_router
from app.core.config import get_settings
from app.core.csrf import csrf_middleware
from app.core.errors import error_response, register_error_handlers
from app.core.logging import configure_logging


async def limit_body_size(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Refuse oversized requests early (SEC-03); nginx enforces the same limit."""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > get_settings().max_body_bytes:
        return error_response(413, "Request body is too large", code="payload_too_large")
    return await call_next(request)


def create_app() -> FastAPI:
    configure_logging(get_settings())

    app = FastAPI(
        title="Aporia API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    register_error_handlers(app)
    app.middleware("http")(csrf_middleware)
    app.middleware("http")(limit_body_size)
    app.include_router(api_router)
    return app


app = create_app()
