"""
Application Configuration using Pydantic Settings

Type-safe environment variable loading with validation
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    
    Automatically loads from:
    1. Environment variables
    2. .env file (if present)
    3. Default values (specified below)
    
    Usage:
        from app.core.config import settings
        
        database_url = settings.DATABASE_URL
        is_production = settings.ENVIRONMENT == "production"
    """
    
    # Application Settings
    ENVIRONMENT: str = "development"
    
    # Telegram Bot Settings (REQUIRED — no default, must be set in .env or environment)
    TELEGRAM_BOT_TOKEN: str

    # Admin Authentication (REQUIRED — no default)
    ADMIN_TOKEN: str
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./pravda_market.db"
    TEST_DATABASE_URL: str = "sqlite:///./test_pravda_market.db"
    
    # CORS Settings (default: localhost dev server; set explicit domains in production)
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # "text" or "json"
    
    # Rate Limiting
    REDIS_URL: str | None = None
    
    # Payment Integration (Future: SLICE #6)
    YOOKASSA_SHOP_ID: str | None = None
    YOOKASSA_SECRET_KEY: str | None = None
    
    # Monitoring (Optional)
    SENTRY_DSN: str | None = None

    # TON Blockchain Integration
    TON_INDEXER_ENABLED: bool = True  # Set to False to disable in dev
    TONCENTER_API_KEY: str | None = None  # Optional API key for higher rate limits

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra env vars not defined here
    )
    
    # Properties for easier access
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT == "development"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def use_json_logs(self) -> bool:
        """Check if JSON logging is enabled"""
        return self.LOG_FORMAT == "json"


# Global settings instance
settings = Settings()


# Validation: Fail fast if unsafe values in production
if settings.is_production:
    if settings.DATABASE_URL.startswith("sqlite"):
        raise ValueError("SQLite is not allowed in production. Set DATABASE_URL to PostgreSQL.")

    if settings.ALLOWED_ORIGINS == "*":
        raise ValueError("CORS wildcard '*' is not allowed in production. Set ALLOWED_ORIGINS to specific domains.")
