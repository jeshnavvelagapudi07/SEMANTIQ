"""
Application Configuration and Environment Variables
Supports local SQLite, PostgreSQL, configurable CORS, and server-side authentication.
"""
import os
from typing import Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


def parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env == "production":
        return [
            "https://semantiq.vercel.app",
            "https://semantiq.onrender.com"
        ]
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]


class Settings(BaseModel):
    PROJECT_NAME: str = "SemantiQ"
    TAGLINE: str = "Permission-aware reasoning over connected organizational knowledge."
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Environment & Secrets
    APP_ENV: str = Field(default_factory=lambda: os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    AUTH_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("AUTH_SECRET_KEY", "semantiq_dev_secret_key_8923479182374"))
    
    # Google Gemini API
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"))
    
    # Database Configuration (Supports SQLite and PostgreSQL)
    DATABASE_URL: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./semantiq.db"))
    DATABASE_PATH: str = Field(default_factory=lambda: os.getenv("DATABASE_PATH", "./semantiq.db"))
    
    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=parse_cors_origins)
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY and len(self.GEMINI_API_KEY.strip()) > 5)


settings = Settings()
