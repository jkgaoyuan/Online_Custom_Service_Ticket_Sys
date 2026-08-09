from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Ticket System API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ticket_user:ticket_pass@postgres:5432/ticket_db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Webhook
    WEBHOOK_SECRET: str = "webhook-secret-change-me"

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:5173"

    # Inbound
    EMAIL_DEFAULT_CATEGORY_CODE: str = "email"
    EMAIL_ALLOWED_DOMAINS: list[str] = []

    # Outbound — SMTP
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True
    EMAIL_FROM: str | None = None

    # Outbound — HTTP API (reserved, not implemented in MVP)
    EMAIL_API_PROVIDER: str | None = None
    EMAIL_API_KEY: str | None = None
    EMAIL_API_URL: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
