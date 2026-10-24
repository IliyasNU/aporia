import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import DbSession
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database is unreachable"}},
)
def health(response: Response, db: DbSession) -> HealthResponse:
    """Liveness check used by Docker Compose and CI: the API runs and reaches PostgreSQL."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Health check failed: database is unreachable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="unavailable")
    return HealthResponse(status="ok", database="ok")
