"""
Ledger Routes

Endpoints для просмотра истории транзакций
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, LedgerEntry
from app.api.deps import get_current_user
from app.core.logging_config import get_logger

logger = get_logger()
router = APIRouter(prefix="/ledger", tags=["ledger"])


class TransactionResponse(BaseModel):
    """Ответ с информацией о транзакции"""
    id: int
    amount: int  # in kopecks (frontend expects kopecks)
    entry_type: str  # frontend uses entry_type, not type
    reference_id: Optional[int]
    created_at: str
    description: str  # Human-readable description


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[TransactionResponse]:
    """
    Получить историю транзакций пользователя

    Query params:
        - limit: максимальное количество записей (max 100)
        - offset: смещение для pagination

    Returns:
        List транзакций пользователя
    """
    # Validate pagination
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 50

    # Get transactions
    entries = db.query(LedgerEntry).filter(
        LedgerEntry.user_id == user.id
    ).order_by(
        LedgerEntry.created_at.desc()
    ).limit(limit).offset(offset).all()

    # Format response
    def get_description(entry: LedgerEntry) -> str:
        """Generate human-readable description"""
        if entry.type == 'deposit':
            return f"Пополнение: +{entry.amount_kopecks/100:.2f}₽"
        elif entry.type == 'order_lock':
            return f"Заблокировано для ордера #{entry.reference_id}"
        elif entry.type == 'order_unlock':
            return f"Разблокировано от ордера #{entry.reference_id}"
        elif entry.type == 'trade':
            return f"Исполнение сделки #{entry.reference_id}"
        elif entry.type == 'trade_lock':
            return f"Заблокировано в сделке #{entry.reference_id}"
        elif entry.type == 'payout':
            return f"Выигрыш: +{entry.amount_kopecks/100:.2f}₽"
        elif entry.type == 'fee':
            return f"Комиссия платформы (2%)"
        else:
            return f"{entry.type.title()}"

    return [
        TransactionResponse(
            id=e.id,
            amount=e.amount_kopecks,  # in kopecks, frontend will format
            entry_type=e.type,  # frontend expects entry_type
            reference_id=e.reference_id,
            created_at=e.created_at.isoformat(),
            description=get_description(e)
        )
        for e in entries
    ]
