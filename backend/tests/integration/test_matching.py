"""
Integration tests for Matching Engine

End-to-end tests через API endpoints
CRITICAL: Проверяет ledger invariant в реальных HTTP requests
"""

import pytest
from sqlalchemy import func
from app.db.models import LedgerEntry, Order, Trade, Market, User
from app.core.security import create_mock_init_data
from datetime import datetime, timedelta, timezone


@pytest.mark.integration
def test_exact_match_end_to_end(test_client, test_db_session):
    """
    Test full matching flow with ledger invariant

    CRITICAL: Проверяем что money не создается при matching через API

    Flow:
    1. Create market
    2. Give users balance (deposits)
    3. User A places YES @ 65% for 100₽ → status: open
    4. User B places NO @ 35% for 100₽ → status: filled (matched!)
    5. Verify ledger invariant preserved
    6. Verify trade created correctly
    """

    # Setup: Create test users with authentication
    init_data_a = create_mock_init_data(111, 'userA', 'User A')
    init_data_b = create_mock_init_data(222, 'userB', 'User B')

    # Create market via database (not API for simplicity)
    market = Market(
        title="Test Market",
        description="Test matching",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Give users balance (1000₽ each = 100000 kopecks)
    # In real app this would be via payment, but for test we add directly
    from app.db.models import User
    user_a = test_db_session.query(User).filter(User.telegram_id == 111).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 222).first()

    # Auto-register users by calling a protected endpoint (triggers get_current_user)
    # This creates users in DB if they don't exist
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_a}"}
    )
    assert response.status_code == 200

    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_b}"}
    )
    assert response.status_code == 200

    # Refresh users from DB
    user_a = test_db_session.query(User).filter(User.telegram_id == 111).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 222).first()

    # Add deposits to ledger
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
    test_db_session.commit()

    # CRITICAL: Check ledger invariant BEFORE matching
    total_before = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(
        LedgerEntry.type.in_(['deposit', 'withdrawal'])
    ).scalar() or 0

    assert total_before == 200000, "Initial deposits should be 200000 kopecks"

    # User A: YES @ 6500bp (65%) for 100₽
    response_a = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_a}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )

    assert response_a.status_code == 200, f"Failed to create order A: {response_a.json()}"
    data_a = response_a.json()

    # Order A should be open (no matches yet)
    assert data_a["status"] == "open", f"Order A should be open, got {data_a['status']}"
    assert data_a["filled"] == 0, "Order A should have 0 filled"
    assert "order_id" in data_a

    # User B: NO @ 3500bp (35%) for 100₽ (should match with A!)
    response_b = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_b}"},
        json={
            "market_id": market.id,
            "side": "no",
            "price": 0.35,
            "amount": 100
        }
    )

    assert response_b.status_code == 200, f"Failed to create order B: {response_b.json()}"
    data_b = response_b.json()

    # Order B should be filled (matched with A)
    assert data_b["status"] == "filled", f"Order B should be filled, got {data_b['status']}"
    assert data_b["filled"] == 100, "Order B should be fully filled (100₽)"
    assert len(data_b["trades"]) == 1, "Should have exactly 1 trade"

    trade_info = data_b["trades"][0]
    assert trade_info["amount"] == 100, "Trade amount should be 100₽"
    assert trade_info["price"] == 0.65, "Trade price should be 0.65 (YES price)"

    # CRITICAL: Check ledger invariant AFTER matching
    total_after = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(
        LedgerEntry.type.in_(['deposit', 'withdrawal'])
    ).scalar() or 0

    # INVARIANT: Total money in system must remain constant!
    assert total_before == total_after, \
        f"Ledger invariant VIOLATED! Before: {total_before}, After: {total_after}"

    # Verify trade in database
    trade = test_db_session.query(Trade).first()
    assert trade is not None, "Trade should exist in database"
    assert trade.market_id == market.id
    assert trade.amount_kopecks == 10000, "Trade amount should be 10000 kopecks (100₽)"
    assert trade.price_bp == 6500, "Trade price should be 6500bp (65%)"
    assert trade.yes_cost_kopecks == 6500, "YES should pay 6500 kopecks (65%)"
    assert trade.no_cost_kopecks == 3500, "NO should pay 3500 kopecks (35%)"

    # CRITICAL: Settlement invariant at DB level
    assert trade.yes_cost_kopecks + trade.no_cost_kopecks == trade.amount_kopecks, \
        "Settlement invariant violated in Trade record!"

    # Verify both orders are updated correctly
    order_a = test_db_session.query(Order).filter(Order.id == data_a["order_id"]).first()
    assert order_a.status == "filled", "Order A should be filled after match"
    assert order_a.filled_kopecks == 10000, "Order A should be fully filled"

    # Check user balances after matching
    # User A: deposit 100000, locked 10000, unlocked 10000, trade_lock -6500
    # Available: 100000 - 6500 = 93500 (935₽)
    # User B: deposit 100000, locked 10000, unlocked 10000, trade_lock -3500
    # Available: 100000 - 3500 = 96500 (965₽)

    response_balance_a = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_a}"}
    )
    balance_a = response_balance_a.json()

    response_balance_b = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_b}"}
    )
    balance_b = response_balance_b.json()

    # User A should have 935₽ available (1000 - 65 locked in trade)
    assert balance_a["available_rubles"] == 935, \
        f"User A should have 935₽ available, got {balance_a['available_rubles']}"
    assert balance_a["locked_rubles"] == 65, \
        f"User A should have 65₽ locked, got {balance_a['locked_rubles']}"

    # User B should have 965₽ available (1000 - 35 locked in trade)
    assert balance_b["available_rubles"] == 965, \
        f"User B should have 965₽ available, got {balance_b['available_rubles']}"
    assert balance_b["locked_rubles"] == 35, \
        f"User B should have 35₽ locked, got {balance_b['locked_rubles']}"


@pytest.mark.integration
def test_minimum_order_size_rejected(test_client, test_db_session):
    """
    DOS protection: reject orders < 1₽

    Security test: Ensures API validates minimum order size
    """
    init_data = create_mock_init_data(111, 'userA', 'User A')

    # Register user and give balance
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200

    user = test_db_session.query(User).filter(User.telegram_id == 111).first()
    test_db_session.add(LedgerEntry(
        user_id=user.id,
        amount_kopecks=100000,
        type='deposit',
        reference_id=1
    ))
    test_db_session.commit()

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Try to place order < 1₽ (should be rejected)
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 0.5  # 0.5₽ < minimum (1₽)
        }
    )

    # Should reject with 400 Bad Request
    assert response.status_code == 400, \
        f"Should reject small order, got status {response.status_code}"
    assert "Minimum order" in response.json()["detail"], \
        f"Error message should mention minimum order, got: {response.json()['detail']}"


@pytest.mark.integration
def test_maximum_order_size_rejected(test_client, test_db_session):
    """
    Overflow protection: reject orders > 1M₽

    Security test: Ensures API validates maximum order size
    """
    init_data = create_mock_init_data(111, 'userA', 'User A')

    # Register user (no need for huge balance, will fail validation first)
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Try to place order > 1M₽ (should be rejected)
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 1_000_001  # > 1M₽ maximum
        }
    )

    # Should reject with 400 Bad Request
    assert response.status_code == 400, \
        f"Should reject large order, got status {response.status_code}"
    assert "Maximum order" in response.json()["detail"], \
        f"Error message should mention maximum order, got: {response.json()['detail']}"
