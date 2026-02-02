"""
Matching Engine with Security

CRITICAL Security Features:
- Row-level locking (SELECT FOR UPDATE SKIP LOCKED) - prevents race conditions
- DOS protection (MAX_TRADES_PER_ORDER limit)
- Atomic transactions (all changes or none)
- Settlement invariant enforcement

Matching Algorithm:
- Price-Time Priority (best price first, then FIFO)
- YES @ P% matches NO @ (100-P)%
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Order, Trade, LedgerEntry
from app.services.validation import calculate_settlement
from typing import List, Optional
from datetime import datetime

# DOS Protection: limit number of trades per order
# Prevents attacker from creating 1000 micro-orders causing N+1 query problem
MAX_TRADES_PER_ORDER = 50


def match_order(new_order: Order, db: Session) -> List[Trade]:
    """
    Match order against orderbook

    Security:
    - Row-level locking (SKIP LOCKED) prevents double-matching
    - Max trades limit (DOS protection)
    - Atomic transaction (caller must commit)

    Algorithm:
    1. Find best counter-order (price-time priority + row lock)
    2. Calculate fill amount (min of both remaining amounts)
    3. Execute trade (create Trade + ledger entries)
    4. Update filled amounts and statuses
    5. Repeat until no more matches or hit MAX_TRADES limit

    Args:
        new_order: Order to match (must be flushed to DB)
        db: Database session

    Returns:
        List of trades created

    Example:
        >>> order = Order(market_id=1, side='yes', price_bp=6500, amount_kopecks=10000)
        >>> db.add(order)
        >>> db.flush()
        >>> trades = match_order(order, db)
        >>> len(trades)  # Number of matches found
        1
    """
    trades = []
    remaining = new_order.amount_kopecks - new_order.filled_kopecks

    # DOS protection: limit iterations
    while remaining > 0 and len(trades) < MAX_TRADES_PER_ORDER:
        # Find best match with row-level lock
        counter = find_best_match(new_order, db)
        if not counter:
            break  # No more matches available

        # Calculate fill amount
        counter_remaining = counter.amount_kopecks - counter.filled_kopecks
        fill_amount = min(remaining, counter_remaining)

        # Safety check: stop if fill amount is invalid
        # This can happen in edge cases (e.g., concurrent updates)
        # Using 'break' instead of 'continue' to avoid infinite loop
        if fill_amount <= 0:
            break

        # Execute trade
        trade = execute_trade(new_order, counter, fill_amount, db)
        trades.append(trade)

        # Update filled amounts
        new_order.filled_kopecks += fill_amount
        counter.filled_kopecks += fill_amount
        remaining -= fill_amount

        # Update statuses
        update_order_status(new_order)
        update_order_status(counter)

        # CRITICAL: Flush changes to DB so next iteration sees updated statuses
        # This ensures filled orders are filtered out in next find_best_match call
        db.flush()

    return trades


def find_best_match(order: Order, db: Session) -> Optional[Order]:
    """
    Find best counter-order with LOCKING

    CRITICAL: with_for_update(skip_locked=True)
    - PostgreSQL: SELECT FOR UPDATE SKIP LOCKED (row-level lock)
    - SQLite: degrades to table lock (acceptable for MVP)

    This prevents race condition where two orders try to match same counter:
    - Order A and Order B both match Counter C
    - Without lock: both get Counter C → double-spending!
    - With SKIP LOCKED: Order A locks C, Order B skips to next

    Priority:
    1. Best price (highest for YES when selling to NO buyer)
    2. FIFO at same price (earliest created_at)

    Args:
        order: Order to find match for
        db: Database session

    Returns:
        Best matching order (locked), or None if no matches

    Example:
        >>> # Orderbook: NO @ 3500 (T1), NO @ 3500 (T2), NO @ 4000
        >>> # New order: YES @ 6500
        >>> match = find_best_match(yes_order, db)
        >>> match.price_bp  # 3500 (matches 6500)
        >>> match.created_at  # T1 (FIFO)
    """
    opposite_side = 'no' if order.side == 'yes' else 'yes'
    matching_price = 10000 - order.price_bp  # YES 6500 matches NO 3500

    # Build query for opposite side
    base_query = db.query(Order).filter(
        Order.market_id == order.market_id,
        Order.side == opposite_side,
        Order.status.in_(['open', 'partial']),
        Order.id != order.id  # Don't match with self
    )

    if order.side == 'yes':
        # YES buyer wants cheapest NO (lowest NO price = highest YES price)
        # YES @ 6500 can match NO @ 3500 or lower (3500, 3000, etc.)
        query = base_query.filter(
            Order.price_bp <= matching_price
        ).order_by(
            Order.price_bp.desc(),  # Best price first (highest for NO = cheapest for YES buyer)
            Order.created_at.asc()  # FIFO at same price
        )
    else:
        # NO buyer wants cheapest YES (lowest YES price)
        # NO @ 3500 can match YES @ 6500 or lower (6500, 6000, etc.)
        query = base_query.filter(
            Order.price_bp >= matching_price
        ).order_by(
            Order.price_bp.desc(),  # Best price first (highest YES price = best for NO buyer)
            Order.created_at.asc()  # FIFO
        )

    # CRITICAL: Row-level lock
    # PostgreSQL: SELECT FOR UPDATE SKIP LOCKED
    # - Locks the row so other transactions can't modify it
    # - SKIP LOCKED: if row is already locked, skip it and try next
    # SQLite: table-level lock (less concurrent but safe)
    return query.with_for_update(skip_locked=True).first()


def execute_trade(order1: Order, order2: Order, amount: int, db: Session) -> Trade:
    """
    Execute trade between two orders

    Creates:
    - Trade record
    - Ledger entries for settlement

    Ensures:
    - Settlement invariant (yes_cost + no_cost = amount)
    - Both orders are settled correctly

    Args:
        order1: First order (YES or NO)
        order2: Second order (opposite side)
        amount: Amount to match in kopecks
        db: Database session

    Returns:
        Created Trade object

    Example:
        >>> yes_order = Order(side='yes', price_bp=6500, ...)
        >>> no_order = Order(side='no', price_bp=3500, ...)
        >>> trade = execute_trade(yes_order, no_order, 10000, db)
        >>> trade.yes_cost_kopecks
        6500  # YES pays 65₽
        >>> trade.no_cost_kopecks
        3500  # NO pays 35₽
    """
    # Determine which order is YES and which is NO
    yes_order = order1 if order1.side == 'yes' else order2
    no_order = order2 if order1.side == 'yes' else order1

    # Calculate settlement (with invariant check)
    yes_cost, no_cost = calculate_settlement(amount, yes_order.price_bp)

    # Create trade record
    trade = Trade(
        market_id=yes_order.market_id,
        yes_order_id=yes_order.id,
        no_order_id=no_order.id,
        price_bp=yes_order.price_bp,
        amount_kopecks=amount,
        yes_cost_kopecks=yes_cost,
        no_cost_kopecks=no_cost
    )
    db.add(trade)
    db.flush()  # Get trade.id for ledger entries

    # Settle both orders
    settle_order_for_trade(yes_order, amount, yes_cost, trade.id, db)
    settle_order_for_trade(no_order, amount, no_cost, trade.id, db)

    return trade


def settle_order_for_trade(order: Order, amount: int, cost: int, trade_id: int, db: Session):
    """
    Create ledger entries for settlement

    CRITICAL: Must unlock MATCHED AMOUNT (not just cost) to preserve ledger invariant!

    Settlement process:
    1. Unlock matched amount from original order_lock
    2. Lock actual cost for trade
    3. Net: (amount - cost) returned to available balance

    Example (exact match):
        Order: 10000 kopecks @ 6500bp YES
        Matched: 10000 kopecks (full order)
        Cost: 6500 kopecks (65% of 10000)

        Ledger entries:
        - Unlock: +10000 (matched amount)
        - Lock for trade: -6500 (actual cost)
        - Net: +3500 returned to available (35% excess)

    Args:
        order: Order being settled
        amount: Matched amount in kopecks (portion of order that matched)
        cost: Actual cost for this fill (from calculate_settlement)
        trade_id: Trade ID for reference
        db: Database session
    """
    # CRITICAL FIX: Unlock matched AMOUNT (not cost!)
    # This preserves ledger invariant: unlock what was locked
    # Cost < amount because user only pays their side's percentage
    unlock_amount = amount

    # Create unlock entry
    db.add(LedgerEntry(
        user_id=order.user_id,
        amount_kopecks=unlock_amount,
        type='order_unlock',
        reference_id=order.id
    ))

    # Lock for trade (actual cost)
    db.add(LedgerEntry(
        user_id=order.user_id,
        amount_kopecks=-cost,
        type='trade_lock',
        reference_id=trade_id
    ))


def update_order_status(order: Order):
    """
    Update order status based on filled amount

    Statuses:
    - open: No fills yet (filled_kopecks = 0)
    - partial: Some filled, some remaining (0 < filled < amount)
    - filled: Completely filled (filled >= amount)
    - cancelled: (set elsewhere, not by matching)

    Args:
        order: Order to update

    Example:
        >>> order.amount_kopecks = 10000
        >>> order.filled_kopecks = 0
        >>> update_order_status(order)
        >>> order.status
        'open'
        >>> order.filled_kopecks = 5000
        >>> update_order_status(order)
        >>> order.status
        'partial'
        >>> order.filled_kopecks = 10000
        >>> update_order_status(order)
        >>> order.status
        'filled'
    """
    if order.filled_kopecks == 0:
        order.status = 'open'
    elif order.filled_kopecks >= order.amount_kopecks:
        order.status = 'filled'
    else:
        order.status = 'partial'

    order.updated_at = datetime.utcnow()
