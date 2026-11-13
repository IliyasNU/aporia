"""Shared fixtures. Tests run against a real PostgreSQL database, never SQLite.

The database comes from TEST_DATABASE_URL (default: "aporia_test" on the local
docker-compose server). It is created if missing and wiped at the start of the
test session, so never point it at a database whose data you want to keep.
"""

import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://aporia:aporia@localhost:5432/aporia_test"
)
# Must happen before any "app" import: settings and the engine read it at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"

from collections.abc import Callable, Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, get_db
from app.main import app

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def alembic_config() -> Config:
    return Config(os.path.join(BACKEND_DIR, "alembic.ini"))


def ensure_test_database_exists() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Start every test session from an empty schema migrated to the latest revision."""
    if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
        pytest.exit("TEST_DATABASE_URL must name a database ending in '_test': tests wipe it.")
    ensure_test_database_exists()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")


@pytest.fixture
def db_session() -> Iterator[Session]:
    """A session whose changes are rolled back after the test, even if the code commits."""
    connection = engine.connect()
    transaction = connection.begin()
    # Same session settings as the app (SessionLocal), bound to the test transaction.
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def make_client(db_session: Session) -> Iterator[Callable[[], TestClient]]:
    """Factory for extra clients: each has its own cookie jar, i.e. its own browser."""
    app.dependency_overrides[get_db] = lambda: db_session
    clients: list[TestClient] = []

    def factory() -> TestClient:
        test_client = TestClient(app)
        clients.append(test_client)
        return test_client

    yield factory
    for test_client in clients:
        test_client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()


DEFAULT_PASSWORD = "correct horse battery staple"


def register(
    client: TestClient,
    *,
    email: str = "reader@example.com",
    handle: str = "reader",
    display_name: str = "Reader",
    password: str = DEFAULT_PASSWORD,
) -> dict[str, object]:
    """Register through the API; the client is signed in afterwards."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "handle": handle, "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def write_article(
    client: TestClient,
    *,
    title: str = "On Doubt",
    summary: str = "Why certainty is overrated.",
    body: str = "Doubt is the beginning of wisdom.",
    tags: list[str] | None = None,
) -> dict[str, object]:
    """Create a draft through the API as the client's signed-in user."""
    response = client.post(
        "/api/v1/articles",
        json={"title": title, "summary": summary, "body_markdown": body, "tags": tags or []},
    )
    assert response.status_code == 201, response.text
    return response.json()


def publish(client: TestClient, article_id: object) -> dict[str, object]:
    response = client.post(f"/api/v1/articles/{article_id}/publish")
    assert response.status_code == 200, response.text
    return response.json()


def signed_in(
    make_client: Callable[[], TestClient], handle: str, display_name: str | None = None
) -> TestClient:
    """A new browser session for a freshly registered user named after the handle."""
    client = make_client()
    register(
        client,
        email=f"{handle}@example.com",
        handle=handle,
        display_name=display_name or handle.capitalize(),
    )
    return client


def me(client: TestClient) -> dict[str, object]:
    return client.get("/api/v1/auth/me").json()
