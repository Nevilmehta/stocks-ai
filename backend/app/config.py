from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    database_url: str = (
        "postgresql+psycopg2://stockai:stockai@localhost:5432/stockai"
    )

    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    allow_registration: bool = False

    market_data_provider: str = "mock"
    market_data_api_url: str | None = None
    market_data_api_key: str | None = None

    ai_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    groq_api_key: str | None = None
    groq_model: str | None = None
    custom_ai_url: str | None = None
    custom_ai_api_key: str | None = None
    custom_ai_model: str | None = None

    # SMTP is optional - if smtp_host is unset, emails are skipped (logged
    # only) rather than failing the request that triggered them.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@example.com"
    smtp_from_name: str = "StockAI"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
