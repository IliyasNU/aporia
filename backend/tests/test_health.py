from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


def test_health_reports_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class UnreachableDatabase:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_returns_503_when_database_is_unreachable() -> None:
    def broken_db() -> Iterator[UnreachableDatabase]:
        yield UnreachableDatabase()

    app.dependency_overrides[get_db] = broken_db
    try:
        response = TestClient(app).get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert "connection refused" not in response.text


def test_openapi_schema_is_served_under_api_prefix(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
