"""
TON Blockchain Integration

Модуль для интеграции с TON блокчейном:
- Отслеживание депозитов в Escrow контракт
- Автоматическое зачисление балансов
- Управление выводами (в будущем)
"""

from .config import ton_settings

# Lazy imports - TonCenterClient and DepositIndexer require httpx
# Import them directly when needed:
#   from app.ton.client import TonCenterClient
#   from app.ton.indexer import DepositIndexer

__all__ = ["ton_settings"]
