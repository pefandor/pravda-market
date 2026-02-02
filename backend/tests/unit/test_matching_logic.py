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
    from datetime import datetime, timedelta, timezone
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),  # 7 days from now
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


# ============================================================================
# PARTIAL FILLS TESTS (Phase 2)
# ============================================================================

@pytest.mark.unit
def test_partial_fill_preserves_ledger_invariant(test_db_session):
    """
    CRITICAL: Partial fill preserves ledger invariant

    Scenario:
    - Order A: YES @ 6500bp for 30000 kopecks (300₽)
    - Order B: NO @ 3500bp for 10000 kopecks (100₽)
    - Expected: B fully filled, A partially filled (100₽), 200₽ remaining

    Ledger invariant must hold: money is conserved
    """
    from app.services.matching import match_order
    from datetime import datetime, timedelta, timezone

    # Setup: Create two users with deposits
    user_a = User(telegram_id=111, username="userA", first_name="User A")
    user_b = User(telegram_id=222, username="userB", first_name="User B")
    test_db_session.add_all([user_a, user_b])
    test_db_session.flush()

    # Deposit 1000₽ each
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

    # Check ledger BEFORE matching
    total_before = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(
        LedgerEntry.type.in_(['deposit', 'withdrawal'])
    ).scalar() or 0

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    # User A: Create large YES order @ 6500bp for 30000 kopecks (300₽)
    order_a = Order(
        user_id=user_a.id,
        market_id=market.id,
        side='yes',
        price_bp=6500,
        amount_kopecks=30000,
        filled_kopecks=0,
        status='open'
    )
    test_db_session.add(order_a)
    test_db_session.flush()

    # Lock funds for order A
    test_db_session.add(LedgerEntry(
        user_id=user_a.id,
        amount_kopecks=-30000,
        type='order_lock',
        reference_id=order_a.id
    ))

    # User B: Create smaller NO order @ 3500bp for 10000 kopecks (100₽)
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

    # Check ledger AFTER matching
    total_after = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(
        LedgerEntry.type.in_(['deposit', 'withdrawal'])
    ).scalar() or 0

    # INVARIANT: Total money must remain constant!
    assert total_before == total_after, \
        f"Ledger invariant VIOLATED! Before: {total_before}, After: {total_after}"

    # Verify trade created correctly
    assert len(trades) == 1, "Should create exactly 1 trade"
    trade = trades[0]
    assert trade.amount_kopecks == 10000, "Trade amount should be 10000 kopecks (100₽)"
    assert trade.yes_cost_kopecks == 6500, "YES cost should be 6500 (65%)"
    assert trade.no_cost_kopecks == 3500, "NO cost should be 3500 (35%)"

    # Verify order statuses
    assert order_b.status == 'filled', "Order B should be fully filled"
    assert order_b.filled_kopecks == 10000, "Order B filled amount should be 10000"

    assert order_a.status == 'partial', "Order A should be partially filled"
    assert order_a.filled_kopecks == 10000, "Order A filled amount should be 10000 (only 100₽ of 300₽)"


@pytest.mark.unit
def test_multiple_matches_single_order(test_db_session):
    """
    Test single order matching against multiple counter-orders

    Scenario:
    - Order A: YES @ 6500bp for 30000 kopecks (300₽)
    - Order B1: NO @ 3500bp for 10000 kopecks (100₽)
    - Order B2: NO @ 3500bp for 10000 kopecks (100₽)
    - Order B3: NO @ 3500bp for 10000 kopecks (100₽)

    Expected: A matches all 3 B orders (fully filled), all at same price
    """
    from app.services.matching import match_order
    from datetime import datetime, timedelta, timezone

    # Setup users (unique IDs to avoid conflicts with other tests)
    user_a = User(telegram_id=2001, username="userA", first_name="User A")
    user_b1 = User(telegram_id=2002, username="userB1", first_name="User B1")
    user_b2 = User(telegram_id=2003, username="userB2", first_name="User B2")
    user_b3 = User(telegram_id=2004, username="userB3", first_name="User B3")
    test_db_session.add_all([user_a, user_b1, user_b2, user_b3])
    test_db_session.flush()

    # Deposits
    for user in [user_a, user_b1, user_b2, user_b3]:
        test_db_session.add(LedgerEntry(
            user_id=user.id,
            amount_kopecks=100000,
            type='deposit',
            reference_id=user.id
        ))
    test_db_session.flush()

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    # Create counter-orders first (B1, B2, B3) - these go on orderbook
    orders_b = []
    for i, user_b in enumerate([user_b1, user_b2, user_b3], 1):
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

        # Lock funds
        test_db_session.add(LedgerEntry(
            user_id=user_b.id,
            amount_kopecks=-10000,
            type='order_lock',
            reference_id=order_b.id
        ))
        orders_b.append(order_b)

    # Create large order A (will match all 3 B orders)
    order_a = Order(
        user_id=user_a.id,
        market_id=market.id,
        side='yes',
        price_bp=6500,
        amount_kopecks=30000,
        filled_kopecks=0,
        status='open'
    )
    test_db_session.add(order_a)
    test_db_session.flush()

    # Lock funds for A
    test_db_session.add(LedgerEntry(
        user_id=user_a.id,
        amount_kopecks=-30000,
        type='order_lock',
        reference_id=order_a.id
    ))
    test_db_session.flush()

    # Match order A against orderbook
    trades = match_order(order_a, test_db_session)
    test_db_session.flush()

    # Verify: Should create 3 trades
    assert len(trades) == 3, f"Should create 3 trades, got {len(trades)}"

    # Verify all trades correct
    for trade in trades:
        assert trade.amount_kopecks == 10000, "Each trade should be 10000 kopecks"
        assert trade.yes_cost_kopecks == 6500, "YES cost should be 6500"
        assert trade.no_cost_kopecks == 3500, "NO cost should be 3500"

    # Verify order A fully filled
    assert order_a.status == 'filled', "Order A should be fully filled"
    assert order_a.filled_kopecks == 30000, "Order A should have 30000 filled"

    # Verify all B orders fully filled
    for order_b in orders_b:
        test_db_session.refresh(order_b)
        assert order_b.status == 'filled', f"Order {order_b.id} should be filled"
        assert order_b.filled_kopecks == 10000, f"Order {order_b.id} should have 10000 filled"


@pytest.mark.unit
def test_max_trades_per_order_limit(test_db_session):
    """
    DOS Protection: MAX_TRADES_PER_ORDER limit enforced

    Scenario:
    - Create 100 tiny NO orders (100 kopecks each)
    - Create 1 large YES order (10000 kopecks = 100₽)
    - MAX_TRADES_PER_ORDER = 50

    Expected: Only 50 trades created, order stays 'partial'
    """
    from app.services.matching import match_order, MAX_TRADES_PER_ORDER
    from datetime import datetime, timedelta, timezone

    # Setup user (unique ID to avoid conflicts)
    user_a = User(telegram_id=3001, username="userA_max", first_name="User A Max")
    test_db_session.add(user_a)
    test_db_session.flush()

    # Deposit large amount
    test_db_session.add(LedgerEntry(
        user_id=user_a.id,
        amount_kopecks=1000000,  # 10000₽
        type='deposit',
        reference_id=3001
    ))
    test_db_session.flush()

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    # Create 100 tiny NO orders on orderbook
    for i in range(100):
        user_b = User(telegram_id=10000 + i, username=f"userB_max_{i}", first_name=f"User B{i}")
        test_db_session.add(user_b)
        test_db_session.flush()

        # Small deposit
        test_db_session.add(LedgerEntry(
            user_id=user_b.id,
            amount_kopecks=10000,
            type='deposit',
            reference_id=1000 + i
        ))

        # Tiny NO order (200 kopecks = 2₽ each, total 200₽ in orderbook)
        order_b = Order(
            user_id=user_b.id,
            market_id=market.id,
            side='no',
            price_bp=3500,
            amount_kopecks=200,  # 2₽ each
            filled_kopecks=0,
            status='open'
        )
        test_db_session.add(order_b)
        test_db_session.flush()

        # Lock funds
        test_db_session.add(LedgerEntry(
            user_id=user_b.id,
            amount_kopecks=-200,
            type='order_lock',
            reference_id=order_b.id
        ))

    # Create large YES order (should match all 100, but limited to 50)
    # Order size = 200₽ (20000 kopecks) > 50 trades * 2₽ = 100₽
    # So order will hit MAX_TRADES limit and remain partial
    order_a = Order(
        user_id=user_a.id,
        market_id=market.id,
        side='yes',
        price_bp=6500,
        amount_kopecks=20000,  # 200₽
        filled_kopecks=0,
        status='open'
    )
    test_db_session.add(order_a)
    test_db_session.flush()

    # Lock funds
    test_db_session.add(LedgerEntry(
        user_id=user_a.id,
        amount_kopecks=-20000,
        type='order_lock',
        reference_id=order_a.id
    ))
    test_db_session.flush()

    # Match (should hit MAX_TRADES limit)
    trades = match_order(order_a, test_db_session)
    test_db_session.flush()

    # Verify: MAX_TRADES_PER_ORDER enforced
    assert len(trades) == MAX_TRADES_PER_ORDER, \
        f"Should create exactly {MAX_TRADES_PER_ORDER} trades (DOS protection), got {len(trades)}"

    # Order should be partial (hit trade limit before fully filled)
    # 50 trades * 200 kopecks = 10000 kopecks filled out of 20000 total
    assert order_a.status == 'partial', "Order A should be partial (hit trade limit)"
    assert order_a.filled_kopecks == MAX_TRADES_PER_ORDER * 200, \
        f"Order A should have {MAX_TRADES_PER_ORDER * 200} filled (50 trades * 200 kopecks each)"
