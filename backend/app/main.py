from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.api.router import API_PREFIX, api_router
from app.core.config import get_settings
from app.core.csrf import csrf_middleware
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.request_guards import limit_body_size, reject_nul_characters

VERSION = "1.0.0"
# Swagger UI comes from a CDN; an exact version means the page cannot change
# underneath us. Set API_DOCS_ENABLED=false to switch the page off.
SWAGGER_UI = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.1"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Aporia API",
        version=VERSION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=None,
        redoc_url=None,
    )
    register_error_handlers(app)
    app.middleware("http")(csrf_middleware)
    app.middleware("http")(limit_body_size)
    app.middleware("http")(reject_nul_characters)
    app.include_router(api_router)

    if settings.api_docs_enabled:

        @app.get(f"{API_PREFIX}/docs", include_in_schema=False)
        def swagger_ui() -> HTMLResponse:
            return get_swagger_ui_html(
                openapi_url=f"{API_PREFIX}/openapi.json",
                title="Aporia API",
                swagger_js_url=f"{SWAGGER_UI}/swagger-ui-bundle.js",
                swagger_css_url=f"{SWAGGER_UI}/swagger-ui.css",
            )

    return app


app = create_app()
