"""
Application Configuration and Environment Variables
Supports local SQLite, PostgreSQL, configurable CORS, and server-side authentication.
"""
import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

DEV_SECRET_FALLBACK = "semantiq_dev_secret_key_8923479182374"


def parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        # Split by comma and strip whitespace; strictly exclude wildcard '*' with credentials
        origins = [origin.strip() for origin in raw.split(",") if origin.strip() and origin.strip() != "*"]
        if origins:
            return origins

    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env == "production":
        # In production, require explicit CORS_ORIGINS or FRONTEND_URL
        fe = os.getenv("FRONTEND_URL", "").strip()
        if fe and fe != "*":
            return [fe]
        return []

    # Development defaults
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]


def get_auth_secret_key() -> str:
    key = os.getenv("AUTH_SECRET_KEY", "").strip()
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env == "production":
        if not key or key == DEV_SECRET_FALLBACK or len(key) < 32:
            raise RuntimeError(
                "CRITICAL PRODUCTION SECURITY ERROR: AUTH_SECRET_KEY must be configured in production with "
                "a high-entropy secret string (at least 32 characters). Known development fallback keys are forbidden."
            )
        return key
    return key or DEV_SECRET_FALLBACK


class Settings(BaseModel):
    PROJECT_NAME: str = "SemantiQ"
    TAGLINE: str = "Permission-aware reasoning over connected organizational knowledge."
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Environment & Secrets
    APP_ENV: str = Field(default_factory=lambda: os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower())
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    AUTH_SECRET_KEY: str = Field(default_factory=get_auth_secret_key)

    # Google Gemini API
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"))

    # Database Configuration (Supports SQLite and PostgreSQL)
    DATABASE_URL: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./semantiq.db"))
    DATABASE_PATH: str = Field(default_factory=lambda: os.getenv("DATABASE_PATH", "./semantiq.db"))
    POSTGRES_SCHEMA: str = Field(default_factory=lambda: os.getenv("POSTGRES_SCHEMA", "semantiq"))

    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=parse_cors_origins)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_postgres(self) -> bool:
        url = self.DATABASE_URL.lower().strip()
        return url.startswith("postgresql://") or url.startswith("postgres://")

    @property
    def is_gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY and len(self.GEMINI_API_KEY.strip()) > 5)


settings = Settings()
