"""
Balance Service

Ledger-based balance management для пользователей
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import LedgerEntry
from app.core.logging_config import get_logger

logger = get_logger()


def get_user_balance(user_id: int, db: Session, for_update: bool = False) -> int:
    """
    Получить баланс пользователя в копейках

    Args:
        user_id: ID пользователя
        db: Database session
        for_update: If True, lock ledger rows (prevents concurrent balance reads)

    Returns:
        int: Баланс в копейках (может быть отрицательным если есть locked orders)
    """
    if for_update:
        # SECURITY: Lock all user's ledger entries to prevent concurrent double-spend.
        # PostgreSQL: SELECT FOR UPDATE blocks other transactions reading same rows.
        # SQLite: silently ignored (single-writer lock provides safety).
        db.query(LedgerEntry).filter(
            LedgerEntry.user_id == user_id
        ).with_for_update().all()

    balance = db.query(func.sum(LedgerEntry.amount_kopecks)).filter(
        LedgerEntry.user_id == user_id
    ).scalar()

    return balance or 0


def get_available_balance(user_id: int, db: Session, for_update: bool = False) -> int:
    """
    Получить доступный баланс (за вычетом locked средств)

    Args:
        user_id: ID пользователя
        db: Database session
        for_update: If True, lock ledger rows (prevents concurrent balance reads)

    Returns:
        int: Доступный баланс в копейках

    Note: get_user_balance already includes order_lock entries (negative),
    so available_balance is just the total balance.
    """
    total = get_user_balance(user_id, db, for_update=for_update)

    return max(0, total)  # Never return negative


def has_sufficient_balance(user_id: int, required_kopecks: int, db: Session, for_update: bool = False) -> bool:
    """
    Проверить достаточно ли средств для операции

    Args:
        user_id: ID пользователя
        required_kopecks: Требуемая сумма в копейках
        db: Database session
        for_update: If True, lock ledger rows (prevents concurrent balance reads)

    Returns:
        bool: True если баланс достаточен
    """
    available = get_available_balance(user_id, db, for_update=for_update)
    return available >= required_kopecks
