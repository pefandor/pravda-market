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
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = "test_token_for_development"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./pravda_market.db"
    TEST_DATABASE_URL: str = "sqlite:///./test_pravda_market.db"
    
    # CORS Settings
    ALLOWED_ORIGINS: str = "*"
    
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


# Validation: Print warning if using default values in production
if settings.is_production:
    if settings.TELEGRAM_BOT_TOKEN == "test_token_for_development":
        print("⚠️  WARNING: Using default TELEGRAM_BOT_TOKEN in production!")
    
    if settings.DATABASE_URL.startswith("sqlite"):
        print("⚠️  WARNING: Using SQLite in production! Use PostgreSQL instead.")
    
    if settings.ALLOWED_ORIGINS == "*":
        print("⚠️  WARNING: CORS allows all origins (*) in production! Security risk!")
