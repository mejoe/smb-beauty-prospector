from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BeautyProspector"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-random-256-bit-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/beautyprospector"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/beautyprospector"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Encryption (AES-256 for IG session cookies)
    ENCRYPTION_KEY: Optional[str] = None  # 32-byte hex key; generate with: python -c "import secrets; print(secrets.token_hex(32))"

    # External APIs (STUBBED - add real keys to use actual APIs)
    # TODO: Add real key for Google Places API
    GOOGLE_PLACES_API_KEY: Optional[str] = None
    # TODO: Add real key for Yelp Fusion API
    YELP_API_KEY: Optional[str] = None
    # TODO: Add real key for SerpAPI
    SERP_API_KEY: Optional[str] = None
    # TODO: Add real key for Apify (LinkedIn + fallback IG scraping)
    APIFY_API_KEY: Optional[str] = None

    # Anthropic AI
    ANTHROPIC_API_KEY: Optional[str] = None

    # Google Sheets
    # TODO: Add Google OAuth credentials for Sheets export
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
