"""
Integration Tests for Market Resolution (SLICE #5)

Tests the complete flow of resolving markets and distributing payouts.
CRITICAL: Verifies ledger invariant is preserved during settlement.
"""

import pytest
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.db.models import Market, Order, Trade, LedgerEntry, User
from app.core.security import create_mock_init_data


@pytest.mark.integration
def test_resolve_market_yes_wins(test_client, test_db_session):
    """
    Test full resolution flow when YES wins

    Scenario:
    1. Create market
    2. Two users trade (YES @ 65% vs NO @ 35%)
    3. Admin resolves market with outcome="yes"
    4. Verify YES user gets payout, NO user loses stake
    5. CRITICAL: Verify ledger invariant preserved
    """
    # Setup: Create two users
    init_data_a = create_mock_init_data(1001, 'userA', 'User A')
    init_data_b = create_mock_init_data(1002, 'userB', 'User B')

    # Register users
    for init_data in [init_data_a, init_data_b]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        assert response.status_code == 200

    # Get users from DB
    user_a = test_db_session.query(User).filter(User.telegram_id == 1001).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 1002).first()

    # Create market
    market = Market(
        title="Will it rain tomorrow?",
        description="Resolution test market",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # NOTE: Users already have 1000₽ from welcome bonus (auto-credited on registration)

    # CRITICAL: Check ledger BEFORE trading and resolution
    total_before = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0

    # User A: YES @ 65% for 100₽
    response_a = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_a}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )
    assert response_a.status_code == 200

    # User B: NO @ 35% for 100₽ (should match!)
    response_b = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_b}"},
        json={
            "market_id": market.id,
            "side": "no",
            "price": 0.35,
            "amount": 100
        }
    )
    assert response_b.status_code == 200
    assert response_b.json()["status"] == "filled", "Orders should match"

    # Verify trade was created
    trade = test_db_session.query(Trade).filter(Trade.market_id == market.id).first()
    assert trade is not None, "Trade should exist"
    assert trade.amount_kopecks == 10000  # 100₽
    assert trade.yes_cost_kopecks == 6500  # 65₽
    assert trade.no_cost_kopecks == 3500   # 35₽

    # Check balances before resolution
    response_balance_a = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_a}"}
    )
    balance_a_before = response_balance_a.json()

    response_balance_b = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_b}"}
    )
    balance_b_before = response_balance_b.json()

    # User A: 1000₽ - 65₽ locked = 935₽ available
    assert balance_a_before["available_rubles"] == 935
    assert balance_a_before["locked_rubles"] == 65

    # User B: 1000₽ - 35₽ locked = 965₽ available
    assert balance_b_before["available_rubles"] == 965
    assert balance_b_before["locked_rubles"] == 35

    # === RESOLUTION: YES WINS ===
    response = test_client.post(
        f"/admin/markets/{market.id}/resolve",
        headers={"Authorization": "Bearer test_admin_token"},
        json={"outcome": "yes"}
    )
    assert response.status_code == 200, f"Resolution failed: {response.json()}"

    data = response.json()
    assert data["success"] == True
    assert data["market_id"] == market.id
    assert data["outcome"] == "yes"

    # Check market updated
    test_db_session.refresh(market)
    assert market.resolved == True
    assert market.outcome == "yes"
    assert market.resolved_at is not None

    # Check YES user balance (should increase - they won!)
    response_balance_a = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_a}"}
    )
    balance_a_after = response_balance_a.json()

    # User A wins: payout 98₽ (100₽ - 2% fee) - 65₽ cost = net +33₽ profit
    # Total: 1000₽ + 33₽ = 1033₽
    assert balance_a_after["available_rubles"] == 1033, \
        f"YES winner should have 1033₽ (with 2% fee), got {balance_a_after['available_rubles']}"
    assert balance_a_after["locked_rubles"] == 0, "No locked funds after resolution"

    # Check NO user balance (should decrease - they lost!)
    response_balance_b = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_b}"}
    )
    balance_b_after = response_balance_b.json()

    # User B loses: loses 35₽ stake = net -35₽ loss
    # Total: 1000₽ - 35₽ = 965₽
    assert balance_b_after["available_rubles"] == 965, \
        f"NO loser should have 965₽, got {balance_b_after['available_rubles']}"
    assert balance_b_after["locked_rubles"] == 0, "No locked funds after resolution"

    # CRITICAL: Verify ledger invariant (deposits - fees preserved)
    total_after = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0

    # With 2% fee on 100₽ pot = 2₽ fee = 200 kopecks
    expected_after = total_before - 200
    assert total_after == expected_after, \
        f"Ledger invariant violated! Expected: {expected_after} (before - fee), After: {total_after}"

    # Verify cannot trade after resolution
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_a}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.5,
            "amount": 100
        }
    )
    assert response.status_code == 400
    assert "resolved" in response.json()["detail"].lower()


@pytest.mark.integration
def test_resolve_market_no_wins(test_client, test_db_session):
    """
    Test resolution flow when NO wins

    Verifies that payout logic works correctly for opposite outcome.
    """
    # Setup: Create two users
    init_data_a = create_mock_init_data(2001, 'userC', 'User C')
    init_data_b = create_mock_init_data(2002, 'userD', 'User D')

    # Register users
    for init_data in [init_data_a, init_data_b]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        assert response.status_code == 200

    # Get users from DB
    user_a = test_db_session.query(User).filter(User.telegram_id == 2001).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 2002).first()

    # Create market
    market = Market(
        title="Will NO win?",
        description="Test NO outcome",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # NOTE: Users already have 1000₽ from welcome bonus (auto-credited on registration)

    # Check ledger before
    total_before = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0

    # User A: YES @ 70% for 100₽
    response_a = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_a}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.70,
            "amount": 100
        }
    )
    assert response_a.status_code == 200

    # User B: NO @ 30% for 100₽ (matches!)
    response_b = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_b}"},
        json={
            "market_id": market.id,
            "side": "no",
            "price": 0.30,
            "amount": 100
        }
    )
    assert response_b.status_code == 200
    assert response_b.json()["status"] == "filled"

    # Resolve with outcome="no"
    response = test_client.post(
        f"/admin/markets/{market.id}/resolve",
        headers={"Authorization": "Bearer test_admin_token"},
        json={"outcome": "no"}
    )
    assert response.status_code == 200

    # Check market updated
    test_db_session.refresh(market)
    assert market.resolved == True
    assert market.outcome == "no"

    # Check YES user balance (loser)
    response_balance_a = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_a}"}
    )
    balance_a_after = response_balance_a.json()

    # User A loses: loses 70₽ stake = net -70₽ loss
    # Total: 1000₽ - 70₽ = 930₽
    assert balance_a_after["available_rubles"] == 930, \
        f"YES loser should have 930₽, got {balance_a_after['available_rubles']}"

    # Check NO user balance (winner)
    response_balance_b = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_b}"}
    )
    balance_b_after = response_balance_b.json()

    # User B wins: payout 98₽ (100₽ - 2% fee) - 30₽ cost = net +68₽ profit
    # Total: 1000₽ + 68₽ = 1068₽
    assert balance_b_after["available_rubles"] == 1068, \
        f"NO winner should have 1068₽ (with 2% fee), got {balance_b_after['available_rubles']}"

    # CRITICAL: Ledger invariant (deposits - fees preserved)
    total_after = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0

    # With 2% fee on 100₽ pot = 2₽ fee = 200 kopecks
    expected_after = total_before - 200
    assert total_after == expected_after, \
        f"Ledger invariant violated! Expected: {expected_after} (before - fee), After: {total_after}"


@pytest.mark.integration
def test_non_admin_cannot_resolve(test_client, test_db_session):
    """
    Security test: Non-admin users cannot resolve markets
    """
    # Create regular user
    init_data = create_mock_init_data(3001, 'hacker', 'Hacker User')
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Try to resolve without admin token
    response = test_client.post(
        f"/admin/markets/{market.id}/resolve",
        headers={"Authorization": f"twa {init_data}"},  # Regular user token
        json={"outcome": "yes"}
    )
    assert response.status_code == 403, "Should reject non-admin"
    assert "denied" in response.json()["detail"].lower()


@pytest.mark.integration
def test_cannot_resolve_nonexistent_market(test_client, test_db_session):
    """
    Error handling: Cannot resolve market that doesn't exist
    """
    response = test_client.post(
        "/admin/markets/99999/resolve",
        headers={"Authorization": "Bearer test_admin_token"},
        json={"outcome": "yes"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower() or \
           "does not exist" in response.json()["detail"].lower()


@pytest.mark.integration
def test_cannot_resolve_already_resolved_market(test_client, test_db_session):
    """
    Error handling: Cannot resolve market twice
    """
    # Create and resolve market
    market = Market(
        title="Already Resolved",
        description="Test",
        deadline=datetime.now(timezone.utc) - timedelta(days=1),
        resolved=True,  # Already resolved
        outcome="yes",
        resolved_at=datetime.now(timezone.utc)
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Try to resolve again
    response = test_client.post(
        f"/admin/markets/{market.id}/resolve",
        headers={"Authorization": "Bearer test_admin_token"},
        json={"outcome": "no"}
    )
    assert response.status_code == 400
    assert "already resolved" in response.json()["detail"].lower()
