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

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
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
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
