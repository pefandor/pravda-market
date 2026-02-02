"""
Bet Routes

Endpoints для размещения ставок и управления ордерами
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import User, Order, LedgerEntry, Market, Trade
from app.api.deps import get_current_user
from app.services.balance import get_available_balance, has_sufficient_balance, get_user_balance
from app.services.matching import match_order
from app.services.validation import validate_order_size
from app.core.logging_config import get_logger
from app.core.rate_limit import limiter

logger = get_logger()
router = APIRouter(prefix="/bets", tags=["bets"])


class BetRequest(BaseModel):
    """Запрос на создание ставки"""
    market_id: int = Field(..., gt=0, description="ID рынка")
    side: str = Field(..., pattern="^(yes|no)$", description="Сторона ставки (yes/no)")
    price: float = Field(..., ge=0.01, le=0.99, description="Цена 1% to 99%")
    amount: float = Field(..., gt=0, description="Сумма в рублях")


class OrderResponse(BaseModel):
    """Ответ с информацией об ордере"""
    id: int
    market_id: int
    side: str
    price: float
    amount: float
    filled: float
    status: str
    created_at: str


@router.post("/", response_model=Dict[str, Any])
@limiter.limit("10/minute")
def place_bet(
    request: Request,
    bet: BetRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Создать новый ордер (ставку)

    Note: В этой версии матчинг НЕ выполняется.
    Ордер просто создаётся и ждёт (SLICE #4 добавит matching)

    Returns:
        Dict с order_id и status
    """
    # Store user for rate limiter
    request.state.user = user

    # 1. Validate market exists
    market = db.query(Market).filter(Market.id == bet.market_id).first()
    if not market:
        logger.warning("Bet attempt for non-existent market", extra={
            "user_id": user.id,
            "market_id": bet.market_id
        })
        raise HTTPException(404, "Market not found")

    if market.resolved:
        raise HTTPException(400, "Market already resolved")

    # 2. Convert to kopecks and basis points
    amount_kopecks = int(bet.amount * 100)
    price_bp = int(bet.price * 10000)

    # 3. SECURITY: Validate order size (DOS protection)
    try:
        validate_order_size(amount_kopecks)
    except ValueError as e:
        logger.warning("Order size validation failed", extra={
            "user_id": user.id,
            "amount_kopecks": amount_kopecks,
            "error": str(e)
        })
        raise HTTPException(400, str(e))

    # 4. Check balance
    if not has_sufficient_balance(user.id, amount_kopecks, db):
        available = get_available_balance(user.id, db)
        logger.warning("Insufficient balance", extra={
            "user_id": user.id,
            "required": amount_kopecks,
            "available": available
        })
        raise HTTPException(400, f"Insufficient funds. Available: {available/100:.2f}₽")

    # 4. Create order (with error handling for atomic transaction)
    try:
        order = Order(
            user_id=user.id,
            market_id=bet.market_id,
            side=bet.side,
            price_bp=price_bp,
            amount_kopecks=amount_kopecks,
            status='open'
        )
        db.add(order)
        db.flush()  # Get order.id

        # 5. Lock funds
        lock_entry = LedgerEntry(
            user_id=user.id,
            amount_kopecks=-amount_kopecks,  # Negative = lock
            type='order_lock',
            reference_id=order.id
        )
        db.add(lock_entry)
        db.flush()

        # 6. NEW: Attempt matching (SLICE #4)
        trades = match_order(order, db)

        # 7. CRITICAL: Commit ALL changes atomically
        db.commit()
        db.refresh(order)

        logger.info("Order created and matched", extra={
            "order_id": order.id,
            "user_id": user.id,
            "market_id": bet.market_id,
            "side": bet.side,
            "price": bet.price,
            "amount": bet.amount,
            "status": order.status,
            "filled": order.filled_kopecks / 100,
            "trades_count": len(trades)
        })

        return {
            "success": True,
            "order_id": order.id,
            "status": order.status,
            "filled": order.filled_kopecks / 100,  # Return in rubles
            "trades": [
                {
                    "trade_id": t.id,
                    "amount": t.amount_kopecks / 100,
                    "price": t.price_bp / 10000
                }
                for t in trades
            ]
        }

    except Exception as e:
        db.rollback()
        logger.error("Order creation failed", extra={
            "error": str(e),
            "user_id": user.id,
            "market_id": bet.market_id
        })
        raise HTTPException(500, "Failed to create order. Please try again.")


@router.get("/orders", response_model=List[OrderResponse])
def get_orders(
    market_id: Optional[int] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[OrderResponse]:
    """
    Получить ордера пользователя

    Query params:
        - market_id: фильтр по рынку
        - status: фильтр по статусу (open, cancelled, filled)

    Returns:
        List ордеров пользователя
    """
    query = db.query(Order).filter(Order.user_id == user.id)

    if market_id:
        query = query.filter(Order.market_id == market_id)
    if status:
        query = query.filter(Order.status == status)

    orders = query.order_by(Order.created_at.desc()).all()

    return [
        OrderResponse(
            id=o.id,
            market_id=o.market_id,
            side=o.side,
            price=o.price_decimal,
            amount=o.amount_rubles,
            filled=o.filled_kopecks / 100,
            status=o.status,
            created_at=o.created_at.isoformat()
        )
        for o in orders
    ]


@router.get("/balance")
def get_balance(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, float]:
    """
    Получить баланс пользователя

    Returns:
        Dict с total, available и locked балансами
    """
    from sqlalchemy import func

    # Total balance (includes locked funds as negative entries)
    total = get_user_balance(user.id, db)
    available = get_available_balance(user.id, db)  # Same as total in current implementation

    # Calculate locked separately for display
    # Sum all lock/unlock entries (order_lock, order_unlock, trade_lock)
    # Locked = |negative sum| (locks are negative, unlocks are positive)
    locked = db.query(func.sum(LedgerEntry.amount_kopecks)).filter(
        LedgerEntry.user_id == user.id,
        LedgerEntry.type.in_(['order_lock', 'order_unlock', 'trade_lock'])
    ).scalar()
    # locked is negative (e.g., -6500), so abs() gives locked amount
    locked_amount = abs(locked) if locked else 0

    return {
        "total_kopecks": total,
        "total_rubles": total / 100,
        "available_kopecks": available,
        "available_rubles": available / 100,
        "locked_rubles": locked_amount / 100
    }


@router.delete("/{order_id}", response_model=Dict[str, Any])
@limiter.limit("20/minute")
def cancel_order(
    order_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Отменить ордер и разблокировать средства

    Only 'open' orders can be cancelled

    Args:
        order_id: ID ордера для отмены

    Returns:
        Dict с информацией об отменённом ордере
    """
    # Store user for rate limiter
    request.state.user = user

    # 1. Get order
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user.id  # Security: только свои ордера
    ).first()

    if not order:
        raise HTTPException(404, "Order not found")

    if order.status != 'open':
        raise HTTPException(400, f"Cannot cancel order with status '{order.status}'")

    # 2. Update order status
    try:
        order.status = 'cancelled'
        order.updated_at = datetime.now(timezone.utc)

        # 3. Unlock funds (positive ledger entry)
        unlock_entry = LedgerEntry(
            user_id=user.id,
            amount_kopecks=order.amount_kopecks,  # Positive = unlock
            type='order_unlock',
            reference_id=order.id
        )
        db.add(unlock_entry)

        db.commit()
        db.refresh(order)

        logger.info("Order cancelled", extra={
            "order_id": order.id,
            "user_id": user.id,
            "unlocked_amount": order.amount_rubles
        })

        return {
            "success": True,
            "order_id": order.id,
            "unlocked_amount": order.amount_rubles,
            "status": order.status
        }

    except Exception as e:
        db.rollback()
        logger.error("Order cancellation failed", extra={
            "error": str(e),
            "order_id": order_id
        })
        raise HTTPException(500, "Failed to cancel order")


@router.get("/trades")
@limiter.limit("30/minute")
def get_trades(
    request: Request,
    market_id: Optional[int] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get user's trade history (PRIVACY enforced)

    Returns only trades where the user participated (as YES or NO buyer).
    This ensures users cannot see other users' trades.

    Args:
        market_id: Optional filter by specific market
        limit: Number of trades to return (default 50, max 100)

    Returns:
        List of trades with details

    Security:
        - User sees ONLY their own trades
        - No information about counterparty revealed
    """
    # Validate limit
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100

    # CRITICAL: Query trades where user participated
    # User must be owner of either YES or NO order
    query = db.query(Trade).join(
        Order,
        (Order.id == Trade.yes_order_id) | (Order.id == Trade.no_order_id)
    ).filter(
        Order.user_id == user.id  # PRIVACY: Only user's trades
    )

    # Optional market filter
    if market_id is not None:
        query = query.filter(Trade.market_id == market_id)

    # Get trades ordered by newest first
    trades = query.order_by(Trade.created_at.desc()).limit(limit).all()

    # Format response
    result = []
    for trade in trades:
        # Determine user's side (YES or NO)
        yes_order = db.query(Order).filter(Order.id == trade.yes_order_id).first()
        no_order = db.query(Order).filter(Order.id == trade.no_order_id).first()

        user_side = "yes" if yes_order.user_id == user.id else "no"
        user_cost = trade.yes_cost_kopecks if user_side == "yes" else trade.no_cost_kopecks

        result.append({
            "trade_id": trade.id,
            "market_id": trade.market_id,
            "side": user_side,  # User's side in this trade
            "price": trade.price_decimal,  # YES price (0.0 - 1.0)
            "amount": trade.amount_rubles,  # Total amount matched (₽)
            "cost": user_cost / 100,  # User's cost for this trade (₽)
            "created_at": trade.created_at.isoformat()
        })

    logger.info("Trades retrieved", extra={
        "user_id": user.id,
        "market_id": market_id,
        "count": len(result)
    })

    return result
