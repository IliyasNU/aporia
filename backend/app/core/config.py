"""Application settings, read from environment variables (and an optional .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # SecretStr keeps the password out of reprs and logs.
    # The default matches the local docker-compose database.
    database_url: SecretStr = SecretStr("postgresql+psycopg://aporia:aporia@localhost:5432/aporia")


@lru_cache
def get_settings() -> Settings:
    return Settings()
