"""
Unit tests for Matching Engine

TDD Approach: Tests written FIRST (RED), then implementation (GREEN)
Security Focus: Ledger invariant, DOS protection, settlement correctness
"""

import pytest
from sqlalchemy import func
from app.db.models import LedgerEntry, Order, Market, User


# ============================================================================
# SECURITY TESTS - CRITICAL
# ============================================================================

@pytest.mark.unit
def test_ledger_invariant_after_match(test_db_session):
    """
    CRITICAL: Money не создается/уничтожается при matching

    Ledger invariant: sum(all ledger entries) = CONSTANT
    This test ensures matching doesn't create or destroy money
    """
    from app.services.matching import match_order

    # Setup: Create two users with deposits
    user_a = User(telegram_id=111, username="userA", first_name="User A")
    user_b = User(telegram_id=222, username="userB", first_name="User B")
    test_db_session.add_all([user_a, user_b])
    test_db_session.flush()

    # Deposit 1000₽ each (100000 kopecks each = 200000 total)
    test_db_session.add(LedgerEntry(
        user_id=user_a.id,
        amount_kopecks=100000,
        type='deposit',
        reference_id=1
    ))
    test_db_session.add(LedgerEntry(
        user_id=user_b.id,
        amount_kopecks=100000,
        type='deposit',
        reference_id=2
    ))
    test_db_session.flush()

    # CRITICAL: Check total BEFORE matching
    # Invariant: sum(deposits) - sum(withdrawals) = money in system
    # Locks don't affect total, they just move money between available and locked
    total_before = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(
        LedgerEntry.type.in_(['deposit', 'withdrawal'])
    ).scalar() or 0

    assert total_before == 200000  # Sanity check (only deposits so far)

    # Create market
    from datetime import datetime, timedelta
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.utcnow() + timedelta(days=7),  # 7 days from now
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    # User A: Create YES order @ 6500bp for 10000 kopecks (100₽)
    order_a = Order(
        user_id=user_a.id,
        market_id=market.id,
        side='yes',
        price_bp=6500,
        amount_kopecks=10000,
        filled_kopecks=0,
        status='open'
    )
    test_db_session.add(order_a)
    test_db_session.flush()

    # Lock funds for order A
    test_db_session.add(LedgerEntry(
        user_id=user_a.id,
        amount_kopecks=-10000,
        type='order_lock',
        reference_id=order_a.id
    ))

    # User B: Create NO order @ 3500bp for 10000 kopecks (100₽)
    # This should match with order A (6500 + 3500 = 10000 = 100%)
    order_b = Order(
        user_id=user_b.id,
        market_id=market.id,
        side='no',
        price_bp=3500,
        amount_kopecks=10000,
        filled_kopecks=0,
        status='open'
    )
    test_db_session.add(order_b)
    test_db_session.flush()

    # Lock funds for order B
    test_db_session.add(LedgerEntry(
        user_id=user_b.id,
        amount_kopecks=-10000,
        type='order_lock',
        reference_id=order_b.id
    ))
    test_db_session.flush()

    # Perform matching
    trades = match_order(order_b, test_db_session)
    test_db_session.flush()

    # CRITICAL: Check total AFTER matching
    # Invariant: sum(deposits) - sum(withdrawals) = constant
    # Matching creates locks but doesn't add/remove money from system
    total_after = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(
        LedgerEntry.type.in_(['deposit', 'withdrawal'])
    ).scalar() or 0

    # INVARIANT: Total money in system must remain constant!
    assert total_before == total_after, \
        f"Ledger invariant VIOLATED! Before: {total_before}, After: {total_after}"

    # Additional checks
    assert len(trades) == 1, "Should create exactly 1 trade"
    assert trades[0].amount_kopecks == 10000, "Trade amount should be 10000 kopecks"


@pytest.mark.unit
def test_minimum_order_size_validation():
    """
    DOS protection: reject orders < 1₽ (100 kopecks)

    Without minimum order size, attacker could create 1000 orders
    at 1 kopeck each, causing victim's large order to execute
    1000 trades → database timeout
    """
    from app.services.validation import validate_order_size

    # Should reject orders < 100 kopecks (1₽)
    with pytest.raises(ValueError, match="Minimum order"):
        validate_order_size(99)  # 0.99₽ - rejected

    with pytest.raises(ValueError, match="Minimum order"):
        validate_order_size(50)  # 0.5₽ - rejected

    with pytest.raises(ValueError, match="Minimum order"):
        validate_order_size(1)   # 0.01₽ - rejected

    # Should accept orders >= 100 kopecks
    validate_order_size(100)  # 1₽ - accepted (no exception)
    validate_order_size(150)  # 1.5₽ - accepted
    validate_order_size(10000)  # 100₽ - accepted


@pytest.mark.unit
def test_maximum_order_size_validation():
    """
    Overflow protection: reject orders > 1M₽ (100,000,000 kopecks)

    Prevents integer overflow and unreasonably large orders
    """
    from app.services.validation import validate_order_size

    # Should reject orders > 100,000,000 kopecks (1M₽)
    with pytest.raises(ValueError, match="Maximum order"):
        validate_order_size(100_000_001)  # 1,000,000.01₽ - rejected

    with pytest.raises(ValueError, match="Maximum order"):
        validate_order_size(999_999_999)  # Way too large

    # Should accept orders <= 100M kopecks
    validate_order_size(100_000_000)  # 1M₽ exactly - accepted
    validate_order_size(50_000_000)   # 500k₽ - accepted
    validate_order_size(1_000_000)    # 10k₽ - accepted


# ============================================================================
# CORRECTNESS TESTS
# ============================================================================

@pytest.mark.unit
def test_price_compatibility():
    """
    YES @ P% matches NO @ (100-P)%

    Examples:
    - YES @ 6500bp (65%) ↔ NO @ 3500bp (35%) ✓ (65+35=100)
    - YES @ 7000bp (70%) ↔ NO @ 4000bp (40%) ✗ (70+40≠100)
    """
    from app.services.validation import is_price_compatible

    # Compatible prices (sum = 10000bp = 100%)
    assert is_price_compatible(6500, 3500) is True  # 65% + 35%
    assert is_price_compatible(5000, 5000) is True  # 50% + 50%
    assert is_price_compatible(7500, 2500) is True  # 75% + 25%
    assert is_price_compatible(9000, 1000) is True  # 90% + 10%

    # Incompatible prices
    assert is_price_compatible(7000, 4000) is False  # 70% + 40% = 110%
    assert is_price_compatible(6000, 3000) is False  # 60% + 30% = 90%
    assert is_price_compatible(5000, 6000) is False  # 50% + 60% = 110%


@pytest.mark.unit
def test_settlement_math():
    """
    Settlement calculation correctness

    YES @ 6500bp + NO @ 3500bp on 100 kopecks:
    - YES pays: 65 kopecks
    - NO pays: 35 kopecks
    - Total: 100 kopecks (INVARIANT!)
    """
    from app.services.validation import calculate_settlement

    # Test basic settlement
    yes_cost, no_cost = calculate_settlement(amount_kopecks=100, price_bp=6500)
    assert yes_cost == 65, "YES should pay 65 kopecks (65% of 100)"
    assert no_cost == 35, "NO should pay 35 kopecks (35% of 100)"
    assert yes_cost + no_cost == 100, "Settlement MUST sum to total amount"

    # Test 50/50 split
    yes_cost, no_cost = calculate_settlement(amount_kopecks=1000, price_bp=5000)
    assert yes_cost == 500
    assert no_cost == 500
    assert yes_cost + no_cost == 1000

    # Test 90/10 split
    yes_cost, no_cost = calculate_settlement(amount_kopecks=10000, price_bp=9000)
    assert yes_cost == 9000
    assert no_cost == 1000
    assert yes_cost + no_cost == 10000


@pytest.mark.unit
def test_settlement_rounding():
    """
    Edge case: price that doesn't divide evenly

    Example: price=3333bp (33.33%) on 100 kopecks
    - YES pays: floor(100 * 3333 / 10000) = floor(33.33) = 33
    - NO pays: 100 - 33 = 67
    - Total: 33 + 67 = 100 ✓

    CRITICAL: Settlement MUST still sum to 100 (no rounding errors!)
    """
    from app.services.validation import calculate_settlement

    # 33.33% price
    yes_cost, no_cost = calculate_settlement(amount_kopecks=100, price_bp=3333)
    assert yes_cost + no_cost == 100, "Must sum to 100 despite rounding"
    assert yes_cost == 33  # floor(33.33) = 33
    assert no_cost == 67   # 100 - 33 = 67

    # 66.66% price
    yes_cost, no_cost = calculate_settlement(amount_kopecks=100, price_bp=6666)
    assert yes_cost + no_cost == 100
    assert yes_cost == 66  # floor(66.66) = 66
    assert no_cost == 34   # 100 - 66 = 34

    # 1% price (edge case: very low price)
    yes_cost, no_cost = calculate_settlement(amount_kopecks=10000, price_bp=100)
    assert yes_cost + no_cost == 10000
    assert yes_cost == 100   # 1% of 10000 = 100
    assert no_cost == 9900   # 99%


@pytest.mark.unit
def test_settlement_large_amounts():
    """
    Test settlement with large amounts (near maximum)

    Ensures no integer overflow
    """
    from app.services.validation import calculate_settlement

    # 1M₽ order (100,000,000 kopecks) at 50%
    yes_cost, no_cost = calculate_settlement(
        amount_kopecks=100_000_000,
        price_bp=5000
    )
    assert yes_cost == 50_000_000
    assert no_cost == 50_000_000
    assert yes_cost + no_cost == 100_000_000

    # 1M₽ order at 90%
    yes_cost, no_cost = calculate_settlement(
        amount_kopecks=100_000_000,
        price_bp=9000
    )
    assert yes_cost == 90_000_000
    assert no_cost == 10_000_000
    assert yes_cost + no_cost == 100_000_000
