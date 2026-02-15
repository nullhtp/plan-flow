from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/planflow"

    # Application
    app_name: str = "PlanFlow"
    debug: bool = False

    # Auth / JWT
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Cookies
    cookie_secure: bool = False  # Set True in production (HTTPS)

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
