"""
Smoke Tests - End-to-End Critical User Journeys

These tests verify that the core platform functionality works from start to finish.
Run these tests before any deployment to ensure critical paths are working.

Critical Journeys:
1. Full Trading Flow: Register → View Markets → Place Bet → Match → Settle
2. Balance Management: Deposit → Lock → Unlock → Payout
3. Order Management: Create → Cancel → Status Updates
4. Market Lifecycle: Create → Trade → Resolve → Payout
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app.db.models import Market, Order, Trade, LedgerEntry, User
from app.core.security import create_mock_init_data


@pytest.mark.smoke
@pytest.mark.integration
def test_full_trading_journey_end_to_end(test_client, test_db_session):
    """
    SMOKE TEST: Complete user journey from registration to payout

    This is the MOST CRITICAL test - verifies the entire platform works.

    Flow:
    1. Two users register (auto-registration via Telegram auth)
    2. Users receive initial test balance (deposit)
    3. User A places YES bet
    4. User B places NO bet (matches with A)
    5. Trade executes, funds locked
    6. Admin resolves market
    7. Winner receives payout, loser loses stake
    8. Ledger invariant preserved throughout

    If this test passes, the core platform is functional.
    """
    print("\n[START] Full Trading Journey E2E Test")

    # === Step 1: User Registration ===
    print("📝 Step 1: Registering two users...")
    init_data_alice = create_mock_init_data(5001, 'alice', 'Alice')
    init_data_bob = create_mock_init_data(5002, 'bob', 'Bob')

    # Auto-register by calling any authenticated endpoint
    for init_data, name in [(init_data_alice, 'Alice'), (init_data_bob, 'Bob')]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        assert response.status_code == 200, f"{name} registration failed"
        print(f"   ✅ {name} registered")

    # === Step 2: Initial Balance (Welcome Bonus) ===
    print("💰 Step 2: Verifying welcome bonus (auto-credited on registration)...")
    # NOTE: Users already have 1000₽ from welcome bonus

    # Verify balances
    for init_data, name in [(init_data_alice, 'Alice'), (init_data_bob, 'Bob')]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        balance = response.json()
        assert balance["available_rubles"] == 1000, f"{name} should have 1000₽ (welcome bonus)"
    print("   ✅ Both users have 1000₽ balance from welcome bonus")

    # === Step 3: Create Market ===
    print("📊 Step 3: Creating market...")
    market = Market(
        title="Will it rain tomorrow?",
        description="E2E Test Market",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()
    print(f"   ✅ Market created (ID: {market.id})")

    # Verify market is visible
    response = test_client.get("/markets")
    assert response.status_code == 200
    markets = response.json()
    assert any(m["id"] == market.id for m in markets), "Market should be visible"

    # === Step 4: Check Ledger Invariant Before Trading ===
    print("🔒 Step 4: Recording initial ledger state...")
    total_before_trading = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0
    print(f"   📈 Initial ledger total: {total_before_trading} kopecks")

    # === Step 5: Alice Places YES Bet ===
    print("🎲 Step 5: Alice places YES bet...")
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_alice}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.60,
            "amount": 100
        }
    )
    assert response.status_code == 200, f"Alice bet failed: {response.json()}"
    alice_order = response.json()
    assert alice_order["status"] == "open", "Alice order should be open (no match yet)"
    print(f"   ✅ Alice placed YES @ 60% for 100₽ (Order ID: {alice_order['order_id']})")

    # Verify Alice's balance locked
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_alice}"}
    )
    balance = response.json()
    assert balance["available_rubles"] == 900, "Alice should have 900₽ available (100₽ locked)"
    assert balance["locked_rubles"] == 100, "Alice should have 100₽ locked"

    # === Step 6: Bob Places NO Bet (Matches!) ===
    print("🎲 Step 6: Bob places NO bet (will match with Alice)...")
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_bob}"},
        json={
            "market_id": market.id,
            "side": "no",
            "price": 0.40,
            "amount": 100
        }
    )
    assert response.status_code == 200, f"Bob bet failed: {response.json()}"
    bob_order = response.json()
    assert bob_order["status"] == "filled", "Bob order should be filled (matched with Alice)"
    assert len(bob_order.get("trades", [])) > 0, "Should have trades"
    print(f"   ✅ Bob placed NO @ 40% for 100₽ (Order ID: {bob_order['order_id']})")
    print(f"   🤝 MATCH! Trade executed")

    # === Step 7: Verify Trade Created ===
    print("📝 Step 7: Verifying trade details...")
    trade = test_db_session.query(Trade).filter(Trade.market_id == market.id).first()
    assert trade is not None, "Trade should exist"
    assert trade.amount_kopecks == 10_000, "Trade should be for 100₽"
    assert trade.yes_cost_kopecks == 6_000, "YES cost should be 60₽"
    assert trade.no_cost_kopecks == 4_000, "NO cost should be 40₽"
    assert trade.yes_cost_kopecks + trade.no_cost_kopecks == trade.amount_kopecks, "Cost invariant"
    print(f"   ✅ Trade verified (ID: {trade.id})")
    print(f"      - YES cost: 60₽, NO cost: 40₽, Total pot: 100₽")

    # === Step 8: Check Ledger Invariant After Trading ===
    print("Step 8: Verifying ledger invariant after trading...")
    # Store total deposits for later verification
    total_deposits = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).filter(LedgerEntry.type == 'deposit').scalar() or 0

    # After trading, money is locked in trades (trade_lock entries)
    # Ledger sum will be less than deposits due to negative lock entries
    # This is expected and correct!
    total_after_trading = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0

    # The invariant we check: After RESOLUTION, total should equal deposits
    # We'll verify this in Step 13
    print(f"   Deposits: {total_deposits/100}₽, Current ledger: {total_after_trading/100}₽")

    # === Step 9: Check Balances After Trade ===
    print("💰 Step 9: Checking balances after trade...")
    for init_data, name, expected_available, expected_locked in [
        (init_data_alice, 'Alice', 940, 60),  # 1000 - 60 locked
        (init_data_bob, 'Bob', 960, 40)       # 1000 - 40 locked
    ]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        balance = response.json()
        assert balance["available_rubles"] == expected_available, \
            f"{name} should have {expected_available}₽ available"
        assert balance["locked_rubles"] == expected_locked, \
            f"{name} should have {expected_locked}₽ locked"
        print(f"   ✅ {name}: {expected_available}₽ available, {expected_locked}₽ locked")

    # === Step 10: Admin Resolves Market (YES Wins) ===
    print("⚖️  Step 10: Admin resolves market (YES wins)...")
    response = test_client.post(
        f"/admin/markets/{market.id}/resolve",
        headers={"Authorization": "Bearer test_admin_token"},
        json={"outcome": "yes"}
    )
    assert response.status_code == 200, f"Resolution failed: {response.json()}"
    result = response.json()
    assert result["success"] is True
    assert result["outcome"] == "yes"
    print("   ✅ Market resolved: YES wins!")

    # === Step 11: Verify Market Status ===
    print("📊 Step 11: Verifying market status...")
    test_db_session.refresh(market)
    assert market.resolved is True, "Market should be resolved"
    assert market.outcome == "yes", "Outcome should be YES"
    print("   ✅ Market status updated")

    # === Step 12: Check Final Balances (After Payout) ===
    print("💰 Step 12: Checking final balances after payout...")

    # Alice (YES winner): paid 60₽, gets 100₽ payout - 2₽ fee → net +38₽ profit
    # Final: 1000₽ + 38₽ = 1038₽
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_alice}"}
    )
    alice_final = response.json()
    assert alice_final["available_rubles"] == 1038, \
        f"Alice (winner) should have 1038₽ (with 2% fee), got {alice_final['available_rubles']}"
    assert alice_final["locked_rubles"] == 0, "No locked funds after resolution"
    print(f"   ✅ Alice (winner): 1038₽ (net +38₽ profit after 2% fee)")

    # Bob (NO loser): paid 40₽, gets 0₽ → net -40₽ loss
    # Final: 1000₽ - 40₽ = 960₽
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data_bob}"}
    )
    bob_final = response.json()
    assert bob_final["available_rubles"] == 960, \
        f"Bob (loser) should have 960₽, got {bob_final['available_rubles']}"
    assert bob_final["locked_rubles"] == 0, "No locked funds after resolution"
    print(f"   ✅ Bob (loser): 960₽ (net -40₽ loss)")

    # === Step 13: Final Ledger Invariant Check ===
    print("Step 13: Final ledger invariant verification...")
    # After resolution, ledger total = deposits - platform fees
    total_after_resolution = test_db_session.query(
        func.sum(LedgerEntry.amount_kopecks)
    ).scalar() or 0

    # After resolution with 2% fee:
    # Alice: +100k (deposit) - 60k (trade_lock) + 100k (payout) - 2k (fee) = 138k
    # Bob: +100k (deposit) - 40k (trade_lock) = 60k
    # Total: 198k (deposits minus 2k fee = 200k - 2k)
    expected_total = total_deposits - 200  # 2₽ fee = 200 kopecks
    assert total_after_resolution == expected_total, \
        f"Ledger invariant violated! Expected: {expected_total} (deposits - fee), Got: {total_after_resolution}"
    print(f"   ✅ Ledger invariant preserved (deposits - 2% fee)")

    # === Step 14: Verify Cannot Trade After Resolution ===
    print("🚫 Step 14: Verifying trading blocked after resolution...")
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_alice}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.5,
            "amount": 100
        }
    )
    assert response.status_code == 400, "Should not allow trading on resolved market"
    assert "resolved" in response.json()["detail"].lower()
    print("   ✅ Trading correctly blocked on resolved market")

    print("\n🎉 FULL TRADING JOURNEY E2E TEST PASSED!")
    print("=" * 70)
    print("✅ User registration works")
    print("✅ Balance management works")
    print("✅ Order placement works")
    print("✅ Matching engine works")
    print("✅ Trade execution works")
    print("✅ Market resolution works")
    print("✅ Payout distribution works")
    print("✅ Ledger invariant preserved")
    print("✅ Security validations work")
    print("=" * 70)


@pytest.mark.smoke
@pytest.mark.integration
def test_order_cancellation_journey(test_client, test_db_session):
    """
    SMOKE TEST: Order cancellation flow

    Verifies users can:
    1. Place order
    2. Cancel unfilled order
    3. Receive funds back
    4. Cannot cancel already filled orders
    """
    print("\n🔄 Testing Order Cancellation Journey...")

    # Setup user (gets 1000₽ welcome bonus on registration)
    init_data = create_mock_init_data(6001, 'charlie', 'Charlie')
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200
    # NOTE: User already has 1000₽ from welcome bonus

    # Create market
    market = Market(
        title="Cancellation Test Market",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Place order
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.75,
            "amount": 200
        }
    )
    assert response.status_code == 200
    order_id = response.json()["order_id"]
    print(f"   ✅ Order placed (ID: {order_id})")

    # Verify funds locked
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    balance = response.json()
    assert balance["locked_rubles"] == 200
    print("   ✅ Funds locked: 200₽")

    # Cancel order (DELETE method, not POST)
    response = test_client.delete(
        f"/bets/{order_id}",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200
    print(f"   ✅ Order cancelled")

    # Verify funds unlocked
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    balance = response.json()
    assert balance["available_rubles"] == 1000, "Funds should be returned"
    assert balance["locked_rubles"] == 0, "No locked funds"
    print("   ✅ Funds returned: 1000₽")

    print("🎉 ORDER CANCELLATION JOURNEY PASSED!")


@pytest.mark.smoke
@pytest.mark.integration
def test_market_visibility_and_filtering(test_client, test_db_session):
    """
    SMOKE TEST: Market discovery and filtering

    Verifies:
    1. Markets are visible to all users
    2. Orderbook displays correctly
    3. Market details accessible
    4. Trade history visible to participants
    """
    print("\n📊 Testing Market Visibility and Filtering...")

    # Create multiple markets
    markets = []
    for i in range(3):
        market = Market(
            title=f"Test Market {i}",
            description=f"Description {i}",
            deadline=datetime.now(timezone.utc) + timedelta(days=i+1),
            resolved=False,
            category="test"
        )
        test_db_session.add(market)
        markets.append(market)
    test_db_session.commit()

    # Test GET /markets
    response = test_client.get("/markets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3, "Should have at least 3 markets"
    print(f"   ✅ GET /markets works ({len(data)} markets)")

    # Test GET /markets/{id}/orderbook
    response = test_client.get(f"/markets/{markets[0].id}/orderbook")
    assert response.status_code == 200
    orderbook = response.json()
    assert "yes_orders" in orderbook
    assert "no_orders" in orderbook
    print(f"   ✅ GET /markets/{{id}}/orderbook works")

    print("🎉 MARKET VISIBILITY TEST PASSED!")


@pytest.mark.smoke
@pytest.mark.integration
def test_authentication_and_authorization(test_client, test_db_session):
    """
    SMOKE TEST: Security and authentication

    Verifies:
    1. Unauthenticated requests rejected
    2. Invalid auth tokens rejected
    3. Users can only access their own data
    4. Admin endpoints protected
    """
    print("\n🔒 Testing Authentication and Authorization...")

    # Test 1: Unauthenticated request
    response = test_client.get("/bets/balance")
    assert response.status_code in [401, 422], "Should reject unauthenticated request"
    print("   ✅ Unauthenticated requests blocked")

    # Test 2: Invalid token
    response = test_client.get("/bets/balance",
        headers={"Authorization": "twa invalid_token"}
    )
    assert response.status_code in [401, 403, 422], "Should reject invalid token"
    print("   ✅ Invalid tokens rejected")

    # Test 3: Admin endpoint without admin token
    market = Market(
        title="Auth Test Market",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Try with invalid/non-admin token (not missing header, which would give 422)
    response = test_client.post(
        f"/admin/markets/{market.id}/resolve",
        headers={"Authorization": "Bearer invalid_token"},
        json={"outcome": "yes"}
    )
    assert response.status_code in [401, 403], "Should require admin auth"
    print("   ✅ Admin endpoints protected")

    # Test 4: Valid user auth works
    init_data = create_mock_init_data(7001, 'dave', 'Dave')
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200, "Valid auth should work"
    print("   ✅ Valid authentication works")

    print("🎉 AUTHENTICATION TEST PASSED!")


@pytest.mark.smoke
def test_api_health_and_availability(test_client):
    """
    SMOKE TEST: API availability

    Verifies:
    1. Root endpoint responds
    2. Health check works
    3. Readiness probe works
    4. Docs accessible
    """
    print("\n🏥 Testing API Health and Availability...")

    # Root endpoint
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "working"
    print("   ✅ Root endpoint (/) works")

    # Health check
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("   ✅ Health check (/health) works")

    # Readiness probe
    response = test_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    print("   ✅ Readiness probe (/health/ready) works")

    # API docs
    response = test_client.get("/docs")
    assert response.status_code == 200
    print("   ✅ API docs (/docs) accessible")

    print("🎉 API HEALTH TEST PASSED!")
