"""
TON Blockchain Integration

Модуль для интеграции с TON блокчейном:
- Отслеживание депозитов в Escrow контракт
- Автоматическое зачисление балансов
- Управление выводами (в будущем)
"""

from .config import ton_settings
from .client import TonCenterClient
from .indexer import DepositIndexer

__all__ = ["ton_settings", "TonCenterClient", "DepositIndexer"]
