"""
Integration Tests for GET /markets/{id}/orderbook endpoint

Tests orderbook aggregation and privacy (no individual user identification)
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.db.models import Market, LedgerEntry, Order, User
from app.core.security import create_mock_init_data


@pytest.mark.integration
def test_get_orderbook_market_not_found(test_client, test_db_session):
    """Test 404 when market doesn't exist"""
    response = test_client.get("/markets/99999/orderbook")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"].lower()


@pytest.mark.integration
def test_get_orderbook_empty(test_client, test_db_session):
    """Test orderbook with no orders"""
    # Create market
    market = Market(
        title="Empty Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Get orderbook (should be empty)
    response = test_client.get(f"/markets/{market.id}/orderbook")
    assert response.status_code == 200

    data = response.json()
    assert data["market_id"] == market.id
    assert data["yes_orders"] == []
    assert data["no_orders"] == []


@pytest.mark.integration
def test_get_orderbook_with_orders(test_client, test_db_session):
    """Test orderbook with multiple orders"""
    # Create user
    init_data = create_mock_init_data(9001, 'userA', 'User A')
    response = test_client.get("/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )
    assert response.status_code == 200

    user = test_db_session.query(User).filter(User.telegram_id == 9001).first()

    # Create market
    market = Market(
        title="Test Market",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Give user balance
    test_db_session.add(LedgerEntry(
        user_id=user.id,
        amount_kopecks=500000,
        type='deposit',
        reference_id=1
    ))
    test_db_session.commit()

    # Place multiple orders (use prices that DON'T match to keep them in orderbook)
    # YES @ 75% for 100₽ (would match NO @ 25% or lower - not present)
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.75,
            "amount": 100
        }
    )
    assert response.status_code == 200

    # YES @ 80% for 200₽ (would match NO @ 20% or lower - not present)
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.80,
            "amount": 200
        }
    )
    assert response.status_code == 200

    # NO @ 15% for 150₽ (would match YES @ 85% or higher - not present)
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "no",
            "price": 0.15,
            "amount": 150
        }
    )
    assert response.status_code == 200

    # Get orderbook
    response = test_client.get(f"/markets/{market.id}/orderbook")
    assert response.status_code == 200

    data = response.json()
    assert data["market_id"] == market.id

    # Check YES orders (should be sorted by price desc - best first)
    yes_orders = data["yes_orders"]
    assert len(yes_orders) == 2
    assert yes_orders[0]["price"] == 0.80  # Best price first
    assert yes_orders[0]["amount"] == 200.0
    assert yes_orders[1]["price"] == 0.75
    assert yes_orders[1]["amount"] == 100.0

    # Check NO orders
    no_orders = data["no_orders"]
    assert len(no_orders) == 1
    assert no_orders[0]["price"] == 0.15
    assert no_orders[0]["amount"] == 150.0


@pytest.mark.integration
def test_get_orderbook_aggregates_same_price(test_client, test_db_session):
    """
    Test orderbook aggregates orders at same price level

    PRIVACY: Multiple users' orders at same price should be aggregated
    """
    # Create two users
    init_data_a = create_mock_init_data(9101, 'userA', 'User A')
    init_data_b = create_mock_init_data(9102, 'userB', 'User B')

    for init_data in [init_data_a, init_data_b]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        assert response.status_code == 200

    # Get users
    user_a = test_db_session.query(User).filter(User.telegram_id == 9101).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 9102).first()

    # Create market
    market = Market(
        title="Aggregation Test",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Give users balance
    for user in [user_a, user_b]:
        test_db_session.add(LedgerEntry(
            user_id=user.id,
            amount_kopecks=200000,
            type='deposit',
            reference_id=user.id
        ))
    test_db_session.commit()

    # User A: YES @ 65% for 100₽
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_a}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )
    assert response.status_code == 200

    # User B: YES @ 65% for 150₽ (SAME PRICE!)
    response = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_b}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 150
        }
    )
    assert response.status_code == 200

    # Get orderbook
    response = test_client.get(f"/markets/{market.id}/orderbook")
    assert response.status_code == 200

    data = response.json()
    yes_orders = data["yes_orders"]

    # Should aggregate to single entry
    assert len(yes_orders) == 1
    assert yes_orders[0]["price"] == 0.65
    # PRIVACY: Aggregated amount (no way to tell it's from 2 users)
    assert yes_orders[0]["amount"] == 250.0  # 100 + 150


@pytest.mark.integration
def test_get_orderbook_only_shows_open_orders(test_client, test_db_session):
    """Test orderbook only shows open/partial orders, not filled/cancelled"""
    # Create two users
    init_data_a = create_mock_init_data(9201, 'userA', 'User A')
    init_data_b = create_mock_init_data(9202, 'userB', 'User B')

    for init_data in [init_data_a, init_data_b]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        assert response.status_code == 200

    # Get users
    user_a = test_db_session.query(User).filter(User.telegram_id == 9201).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 9202).first()

    # Create market
    market = Market(
        title="Filled Orders Test",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Give users balance
    for user in [user_a, user_b]:
        test_db_session.add(LedgerEntry(
            user_id=user.id,
            amount_kopecks=200000,
            type='deposit',
            reference_id=user.id
        ))
    test_db_session.commit()

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
    order_a_id = response_a.json()["order_id"]

    # User B: NO @ 35% for 100₽ (matches with A!)
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

    # Both orders should be filled now
    # Get orderbook - should be empty (no open orders)
    response = test_client.get(f"/markets/{market.id}/orderbook")
    assert response.status_code == 200

    data = response.json()
    # Both orders filled, so orderbook empty
    assert len(data["yes_orders"]) == 0
    assert len(data["no_orders"]) == 0


@pytest.mark.integration
def test_get_orderbook_shows_partial_orders(test_client, test_db_session):
    """Test orderbook shows remaining amount of partial orders"""
    # Create two users
    init_data_a = create_mock_init_data(9301, 'userA', 'User A')
    init_data_b = create_mock_init_data(9302, 'userB', 'User B')

    for init_data in [init_data_a, init_data_b]:
        response = test_client.get("/bets/balance",
            headers={"Authorization": f"twa {init_data}"}
        )
        assert response.status_code == 200

    # Get users
    user_a = test_db_session.query(User).filter(User.telegram_id == 9301).first()
    user_b = test_db_session.query(User).filter(User.telegram_id == 9302).first()

    # Create market
    market = Market(
        title="Partial Fill Test",
        description="Test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    # Give users balance
    for user in [user_a, user_b]:
        test_db_session.add(LedgerEntry(
            user_id=user.id,
            amount_kopecks=300000,
            type='deposit',
            reference_id=user.id
        ))
    test_db_session.commit()

    # User A: YES @ 65% for 300₽ (large order)
    response_a = test_client.post("/bets",
        headers={"Authorization": f"twa {init_data_a}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 300
        }
    )
    assert response_a.status_code == 200

    # User B: NO @ 35% for 100₽ (partial match!)
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

    # Order A should be partial (300 - 100 = 200 remaining)
    # Get orderbook
    response = test_client.get(f"/markets/{market.id}/orderbook")
    assert response.status_code == 200

    data = response.json()
    yes_orders = data["yes_orders"]

    # Should show remaining 200₽ from User A's order
    assert len(yes_orders) == 1
    assert yes_orders[0]["price"] == 0.65
    assert yes_orders[0]["amount"] == 200.0  # Remaining after partial fill

    # NO order fully filled, so not in orderbook
    assert len(data["no_orders"]) == 0
