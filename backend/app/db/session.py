from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

# hide_parameters: error messages and logs never include query values
# (emails, password hashes, tokens), only the SQL text (SEC-05).
engine = create_engine(
    get_settings().database_url.get_secret_value(), pool_pre_ping=True, hide_parameters=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]
