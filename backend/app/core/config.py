"""Application settings, read from environment variables (and an optional .env file)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_SECRET_KEY = "dev-only-secret-change-me"  # noqa: S105 (a known placeholder, refused in production)

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

    # Signs unsubscribe links (see app/core/security.py). Must be a long random
    # value in production, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
    secret_key: SecretStr = SecretStr(DEV_SECRET_KEY)

    # Links in emails point here (the web app's public address).
    public_base_url: str = "http://localhost:8080"

    # Outgoing email. The defaults match Mailpit from docker-compose.yml.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = False
    smtp_timeout_seconds: float = 10
    mail_from: str = "Aporia <no-reply@aporia.localhost>"

    newsletter_confirm_ttl_hours: int = Field(default=48, ge=1, le=168)
    # How long a pending subscription waits before another confirmation email may be sent.
    newsletter_resend_minutes: int = Field(default=10, ge=0)

    # Email worker
    worker_poll_seconds: float = Field(default=5, gt=0)
    worker_batch_size: int = Field(default=20, ge=1, le=500)
    worker_max_attempts: int = Field(default=5, ge=1, le=20)
    worker_send_delay_seconds: float = Field(default=0.2, ge=0)  # simple rate limit
    email_job_retention_days: int = Field(default=90, ge=1)
    # Touched after every worker loop; the container healthcheck reads its age.
    worker_heartbeat_file: str = "/tmp/aporia-worker-heartbeat"  # noqa: S108
    worker_heartbeat_max_age_seconds: int = Field(default=300, ge=10)

    @field_validator("trusted_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def production_needs_real_secret(self) -> "Settings":
        secret = self.secret_key.get_secret_value()
        if self.app_env == "production" and (secret == DEV_SECRET_KEY or len(secret) < 32):
            raise ValueError("SECRET_KEY must be a random value of 32+ characters in production")
        return self

    @property
    def session_cookie_secure(self) -> bool:
        """Session cookies are HTTPS-only in production (SEC-04)."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
