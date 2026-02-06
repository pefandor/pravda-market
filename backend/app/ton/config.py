"""
TON Integration Configuration

Настройки для работы с TON блокчейном.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class TonSettings(BaseSettings):
    """TON blockchain configuration"""

    # Escrow contract address (testnet)
    ESCROW_ADDRESS: str = "kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy"

    # TonCenter API
    TONCENTER_API_URL: str = "https://testnet.toncenter.com/api/v2"
    TONCENTER_API_KEY: str | None = None  # Optional API key for higher rate limits

    # Deposit settings
    MIN_DEPOSIT_NANOTON: int = 100_000_000  # 0.1 TON in nanoTON
    MIN_DEPOSIT_TON: float = 0.1

    # Indexer settings
    POLLING_INTERVAL_SECONDS: int = 10
    MAX_TRANSACTIONS_PER_POLL: int = 50
    CONFIRMATIONS_REQUIRED: int = 1  # TON is fast, 1 confirmation is usually enough

    # Rate limiting
    API_RETRY_ATTEMPTS: int = 3
    API_RETRY_DELAY_SECONDS: float = 2.0
    API_REQUEST_DELAY_SECONDS: float = 1.5  # Delay between requests to avoid rate limits

    # Conversion rate (for display, actual conversion happens on withdrawal)
    # 1 TON = X kopecks (will be updated from oracle/API in production)
    TON_TO_KOPECKS_RATE: int = 50000  # 1 TON = 500 RUB = 50000 kopecks (example rate)

    # Deposit opcode (must match contract)
    DEPOSIT_OPCODE: int = 0x00000001

    model_config = SettingsConfigDict(
        env_prefix="TON_",
        case_sensitive=True,
    )


@lru_cache
def get_ton_settings() -> TonSettings:
    """Get cached TON settings instance"""
    settings = TonSettings()

    # Fall back to main settings TONCENTER_API_KEY if TON-specific not set
    if settings.TONCENTER_API_KEY is None:
        try:
            from ..core.config import settings as main_settings
            if main_settings.TONCENTER_API_KEY:
                settings.TONCENTER_API_KEY = main_settings.TONCENTER_API_KEY
        except Exception:
            pass  # Ignore if main settings not available

    return settings


# Convenience export
ton_settings = get_ton_settings()
