"""Every error response has the same JSON shape and leaks no internals."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import register_error_handlers


class Credentials(BaseModel):
    email: str
    password: str


def make_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/echo")
    def echo(payload: Credentials) -> dict[str, str]:
        return {"email": payload.email}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    return app


def test_unknown_route_returns_not_found_error(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_wrong_method_returns_method_not_allowed_error(client: TestClient) -> None:
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_validation_error_lists_fields_without_echoing_input() -> None:
    client = TestClient(make_app())

    response = client.post("/echo", json={"email": "reader@example.com", "password": 12345})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"] == [
        {
            "loc": ["body", "password"],
            "msg": "Input should be a valid string",
            "type": "string_type",
        }
    ]
    assert "12345" not in response.text


def test_unexpected_exception_returns_generic_500() -> None:
    client = TestClient(make_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }
    assert "secret internal detail" not in response.text
