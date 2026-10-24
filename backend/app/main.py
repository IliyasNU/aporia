from fastapi import FastAPI

from app.api.router import API_PREFIX, api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


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
    app.include_router(api_router)
    return app


app = create_app()
