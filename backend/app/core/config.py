"""Application settings, read from environment variables (and an optional .env file)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LOCAL_ORIGINS = [
    "http://localhost:8080",  # docker compose web
    "http://127.0.0.1:8080",
    "http://localhost:5173",  # vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:8000",  # Swagger UI served by the API itself
    "http://127.0.0.1:8000",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # SecretStr keeps the password out of reprs and logs.
    # The default matches the local docker-compose database.
    database_url: SecretStr = SecretStr("postgresql+psycopg://aporia:aporia@localhost:5432/aporia")

    # Browser origins allowed to send state-changing requests (CSRF protection).
    # Set as a comma-separated list, e.g. TRUSTED_ORIGINS=https://aporia.example.
    trusted_origins: Annotated[list[str], NoDecode] = LOCAL_ORIGINS

    session_ttl_days: int = Field(default=14, ge=1, le=90)

    @field_validator("trusted_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @property
    def session_cookie_secure(self) -> bool:
        """Session cookies are HTTPS-only in production (SEC-04)."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
