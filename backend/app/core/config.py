"""
Application Configuration and Environment Variables
PostgreSQL-only architecture. Fails loudly on startup if DATABASE_URL is missing.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

DEV_SECRET_FALLBACK = "semantiq_dev_secret_key_8923479182374"


def parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        origins = [origin.strip() for origin in raw.split(",") if origin.strip() and origin.strip() != "*"]
        if origins:
            return origins

    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env == "production":
        fe = os.getenv("FRONTEND_URL", "").strip()
        if fe and fe != "*":
            return [fe]
        return []

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


def get_database_url() -> str:
    """
    Returns the PostgreSQL DATABASE_URL.
    Fails immediately with a clear error if it is missing or still points to SQLite.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: DATABASE_URL is not set. "
            "SEMANTIQ requires PostgreSQL in all environments. "
            "Set DATABASE_URL to a postgresql:// connection string."
        )
    url_lower = url.lower()
    if url_lower.startswith("sqlite"):
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: DATABASE_URL is set to a SQLite path. "
            "SEMANTIQ no longer supports SQLite. "
            "Set DATABASE_URL to a postgresql:// connection string."
        )
    if not (url_lower.startswith("postgresql://") or url_lower.startswith("postgres://")):
        raise RuntimeError(
            f"CRITICAL CONFIGURATION ERROR: DATABASE_URL does not appear to be a valid PostgreSQL URL. "
            f"Expected postgresql:// or postgres:// prefix. Got: {url[:30]}..."
        )
    return url


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

    # Database Configuration — PostgreSQL only
    DATABASE_URL: str = Field(default_factory=get_database_url)
    POSTGRES_SCHEMA: str = Field(default_factory=lambda: os.getenv("POSTGRES_SCHEMA", "semantiq"))

    # Seed passwords for initial benchmark account creation (used ONCE on fresh database)
    # Never stored in plaintext; hashed via PBKDF2-HMAC-SHA256 before persistence.
    SEED_ADMIN_PASSWORD: Optional[str] = Field(
        default_factory=lambda: os.getenv("SEED_ADMIN_PASSWORD", "").strip() or None,
        repr=False,
        exclude=True
    )
    SEED_OPERATIONS_PASSWORD: Optional[str] = Field(
        default_factory=lambda: os.getenv("SEED_OPERATIONS_PASSWORD", "").strip() or None,
        repr=False,
        exclude=True
    )
    SEED_PROJECT_MANAGER_PASSWORD: Optional[str] = Field(
        default_factory=lambda: os.getenv("SEED_PROJECT_MANAGER_PASSWORD", "").strip() or None,
        repr=False,
        exclude=True
    )
    SEED_VIEWER_PASSWORD: Optional[str] = Field(
        default_factory=lambda: os.getenv("SEED_VIEWER_PASSWORD", "").strip() or None,
        repr=False,
        exclude=True
    )

    # Benchmark password migration — one-time only, database-marker-gated.
    # Default is False. Set to True in Render env vars only when performing the
    # intentional migration of the four benchmark account passwords.
    # Once the migration completes it records BENCHMARK_PASSWORD_RESET_COMPLETED
    # in system_metadata and subsequent startups will skip this regardless of the
    # env var value. Never put a password value here — use SEED_*_PASSWORD vars.
    RESET_BENCHMARK_PASSWORDS: bool = Field(
        default_factory=lambda: os.getenv("RESET_BENCHMARK_PASSWORDS", "false").strip().lower() == "true"
    )

    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=parse_cors_origins)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY and len(self.GEMINI_API_KEY.strip()) > 5)


settings = Settings()
