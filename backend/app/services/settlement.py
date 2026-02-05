"""
Settlement Service - Market Resolution and Payout Distribution

CRITICAL: This module handles financial settlement.
Ledger invariant MUST be preserved: total sum of ledger entries remains constant.

Settlement Logic:
- Winner: Gets payout (100 kopecks per share) MINUS 2% fee, trade_lock stays (their cost)
- Loser: Gets nothing, trade_lock stays (they lose it)
- Platform: Collects 2% fee from winner's payout

Example for 100₽ trade at YES @ 65%:
- YES cost: 65₽ (locked in trade_lock = -6500)
- NO cost: 35₽ (locked in trade_lock = -3500)
- Total pot: 100₽

If YES wins:
- Fee: 2₽ (2% of 100₽)
- YES: payout +98₽, trade_lock stays -65₽ = net +33₽ profit ✅
- NO: payout 0₽, trade_lock stays -35₽ = net -35₽ loss ✅
- Platform: +2₽ fee ✅

If NO wins:
- Fee: 2₽ (2% of 100₽)
- NO: payout +98₽, trade_lock stays -35₽ = net +63₽ profit ✅
- YES: payout 0₽, trade_lock stays -65₽ = net -65₽ loss ✅
- Platform: +2₽ fee ✅
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Dict, Any

from app.db.models import Market, Trade, Order, LedgerEntry
from app.core.logging_config import get_logger

logger = get_logger()

# Platform fee rate (2% = 0.02)
# Fee is deducted from winner's payout
PLATFORM_FEE_RATE = 0.02


def settle_market(market_id: int, outcome: str, db: Session) -> Dict[str, Any]:
    """
    Settle market and distribute payouts

    This is the main entry point for market resolution.

    Args:
        market_id: ID of market to settle
        outcome: "yes" or "no" - which side won
        db: Database session

    Returns:
        Dictionary with settlement statistics

    Side effects:
        - Updates market.resolved = True
        - Creates ledger entries for all settlements
        - CRITICAL: Preserves ledger invariant

    Raises:
        Exception: If settlement fails (will be rolled back by caller)
    """
    logger.info("Starting market settlement", extra={
        "market_id": market_id,
        "outcome": outcome
    })

    # CRITICAL: Lock market row to prevent concurrent resolution (race condition)
    # SELECT ... FOR UPDATE — blocks other transactions from resolving same market
    # On SQLite (dev): with_for_update() is silently ignored (safe)
    # On PostgreSQL (prod): provides row-level locking
    market = db.query(Market).filter(
        Market.id == market_id
    ).with_for_update().first()

    if not market:
        raise ValueError(f"Market {market_id} not found")

    # Re-check resolved status AFTER acquiring lock (prevents TOCTOU race)
    if market.resolved:
        raise ValueError(f"Market {market_id} is already resolved (race condition prevented)")

    # Get all trades for this market
    trades = db.query(Trade).filter(Trade.market_id == market_id).all()

    logger.debug("Found trades for settlement", extra={
        "market_id": market_id,
        "trade_count": len(trades)
    })

    # Track statistics
    winners_paid = 0
    losers_count = 0
    total_payout_kopecks = 0
    total_fees_kopecks = 0

    # Settle each trade
    for trade in trades:
        # Calculate fee (2% of pot)
        fee_kopecks = int(trade.amount_kopecks * PLATFORM_FEE_RATE)
        # Gross payout = full pot, fee deducted separately for transparency
        gross_payout = trade.amount_kopecks

        if outcome == 'yes':
            # YES wins, NO loses
            settle_winner(trade.yes_order_id, gross_payout, fee_kopecks, trade.id, db)
            settle_loser(trade.no_order_id, trade.id, db)
            winners_paid += 1
            losers_count += 1
            total_payout_kopecks += gross_payout - fee_kopecks  # Net payout for stats
            total_fees_kopecks += fee_kopecks
        else:  # outcome == 'no'
            # NO wins, YES loses
            settle_winner(trade.no_order_id, gross_payout, fee_kopecks, trade.id, db)
            settle_loser(trade.yes_order_id, trade.id, db)
            winners_paid += 1
            losers_count += 1
            total_payout_kopecks += gross_payout - fee_kopecks  # Net payout for stats
            total_fees_kopecks += fee_kopecks

    # Update market status (row already locked)
    market.resolved = True
    market.outcome = outcome
    market.resolved_at = datetime.now(timezone.utc)

    # CRITICAL: Runtime ledger invariant check before commit
    # Flush pending changes to DB so we can query them
    db.flush()

    # Verify: payout + fee entries sum correctly
    trade_ids = [t.id for t in trades]
    if trade_ids:
        # Sum of gross payouts (should equal sum of trade amounts)
        actual_payout_sum = db.query(
            func.sum(LedgerEntry.amount_kopecks)
        ).filter(
            LedgerEntry.type == 'payout',
            LedgerEntry.reference_id.in_(trade_ids)
        ).scalar() or 0

        # Sum of fees (should equal total_fees_kopecks, but negative)
        actual_fee_sum = db.query(
            func.sum(LedgerEntry.amount_kopecks)
        ).filter(
            LedgerEntry.type == 'fee',
            LedgerEntry.reference_id.in_(trade_ids)
        ).scalar() or 0

        # Expected: payout (gross) - fee = net payout
        expected_gross_payout = total_payout_kopecks + total_fees_kopecks
        expected_fee = -total_fees_kopecks

        if actual_payout_sum != expected_gross_payout:
            db.rollback()
            logger.critical("LEDGER INVARIANT VIOLATED in settlement (payout)!", extra={
                "market_id": market_id,
                "expected_gross_payout": expected_gross_payout,
                "actual_payout": actual_payout_sum,
            })
            raise ValueError(
                f"Ledger invariant violated! Expected gross payout {expected_gross_payout}, "
                f"got {actual_payout_sum}"
            )

        if actual_fee_sum != expected_fee:
            db.rollback()
            logger.critical("LEDGER INVARIANT VIOLATED in settlement (fee)!", extra={
                "market_id": market_id,
                "expected_fee": expected_fee,
                "actual_fee": actual_fee_sum,
            })
            raise ValueError(
                f"Ledger invariant violated! Expected fee {expected_fee}, "
                f"got {actual_fee_sum}"
            )

    # NOTE: Caller is responsible for db.commit() — gives route handler control
    # over the transaction boundary

    logger.info("Market settlement completed", extra={
        "market_id": market_id,
        "outcome": outcome,
        "winners_paid": winners_paid,
        "losers_count": losers_count,
        "total_payout_rubles": total_payout_kopecks / 100,
        "total_fees_rubles": total_fees_kopecks / 100,
        "fee_rate": f"{PLATFORM_FEE_RATE:.0%}"
    })

    return {
        "winners_paid": winners_paid,
        "losers_count": losers_count,
        "total_payout_rubles": total_payout_kopecks / 100,
        "total_fees_rubles": total_fees_kopecks / 100,
        "fee_rate_percent": PLATFORM_FEE_RATE * 100
    }


def settle_winner(order_id: int, gross_payout: int, fee_amount: int, trade_id: int, db: Session):
    """
    Settle winner's position

    Winner receives:
    - Gross payout (full pot) as positive entry
    - Fee deducted as separate negative entry (for transparency)
    - trade_lock stays locked (it's their cost that went into the pot)

    Net effect: -cost (from trade_lock) + payout - fee = profit

    Example (100₽ pot, 2% fee):
    - YES paid 65₽ (trade_lock = -6500, stays)
    - Payout: 100₽ (+10000)
    - Fee: -2₽ (-200)
    - Net: -6500 + 10000 - 200 = +3300 (33₽ profit) ✅

    Args:
        order_id: ID of winning order
        gross_payout: Gross payout amount (in kopecks) = full pot
        fee_amount: Fee deducted (in kopecks) = pot * 2%
        trade_id: ID of trade being settled
        db: Database session

    Side effects:
        - Creates 'payout' ledger entry (positive, gross amount)
        - Creates 'fee' ledger entry (negative, platform takes this)
        - trade_lock stays as-is (negative, represents their cost)
    """
    # Get order to find user_id
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        logger.error("Order not found for settlement", extra={"order_id": order_id})
        raise ValueError(f"Order {order_id} not found")

    # Add gross payout (full pot)
    db.add(LedgerEntry(
        user_id=order.user_id,
        amount_kopecks=gross_payout,
        type='payout',
        reference_id=trade_id
    ))

    # Record fee (negative for user, platform revenue)
    if fee_amount > 0:
        db.add(LedgerEntry(
            user_id=order.user_id,
            amount_kopecks=-fee_amount,
            type='fee',
            reference_id=trade_id
        ))

    logger.debug("Winner settled", extra={
        "user_id": order.user_id,
        "order_id": order_id,
        "trade_id": trade_id,
        "gross_payout_kopecks": gross_payout,
        "fee_kopecks": fee_amount,
        "net_payout_kopecks": gross_payout - fee_amount
    })


def settle_loser(order_id: int, trade_id: int, db: Session):
    """
    Settle loser's position

    Loser receives:
    - No payout (they lost)
    - trade_lock stays locked (they lose their stake to the winner)

    Net effect: -cost (from trade_lock) + 0 = loss

    Example:
    - NO paid 35₽ (trade_lock = -3500, stays)
    - Payout: 0₽
    - Net: -3500 + 0 = -3500 (35₽ loss) ✅

    Args:
        order_id: ID of losing order
        trade_id: ID of trade being settled
        db: Database session

    Side effects:
        - No ledger entries created
        - trade_lock stays as-is (negative, represents their loss)
    """
    # Get order to find user_id (for logging)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        logger.error("Order not found for settlement", extra={"order_id": order_id})
        raise ValueError(f"Order {order_id} not found")

    # DON'T unlock trade_lock - they lose their stake
    # DON'T add payout - they lost

    logger.debug("Loser settled", extra={
        "user_id": order.user_id,
        "order_id": order_id,
        "trade_id": trade_id,
        "payout_kopecks": 0
    })
