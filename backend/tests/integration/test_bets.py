"""
Integration Tests for Bets Endpoints

Тесты для POST /bets, GET /bets/orders, GET /bets/balance, DELETE /bets/{id}
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.db.models import Market, LedgerEntry, Order
from app.core.security import create_mock_init_data


@pytest.mark.integration
def test_get_balance_no_deposits(test_client, test_db_session):
    """Test GET /bets/balance with no deposits"""
    init_data = create_mock_init_data(user_id=1001)

    response = test_client.get(
        "/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rubles"] == 0
    assert data["available_rubles"] == 0
    assert data["locked_rubles"] == 0


@pytest.mark.integration
def test_get_balance_with_deposit(test_client, test_db_session, sample_user):
    """Test GET /bets/balance with deposit"""
    # Add deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,  # 1000₽
        type='deposit'
    ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/bets/balance",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rubles"] == 1000.0
    assert data["available_rubles"] == 1000.0
    assert data["locked_rubles"] == 0.0


@pytest.mark.integration
def test_place_bet_success(test_client, test_db_session, sample_user):
    """Test successful bet placement"""
    # Setup: deposit + market
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,  # 1000₽
        type='deposit'
    ))
    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    # Place bet
    response = test_client.post(
        "/bets/",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "order_id" in data
    assert data["status"] == "open"

    # Verify order created
    order = test_db_session.query(Order).filter(Order.id == data["order_id"]).first()
    assert order is not None
    assert order.user_id == sample_user.id
    assert order.market_id == market.id
    assert order.side == "yes"
    assert order.price_bp == 6500
    assert order.amount_kopecks == 10000

    # Verify funds locked
    lock_entry = test_db_session.query(LedgerEntry).filter(
        LedgerEntry.type == 'order_lock',
        LedgerEntry.user_id == sample_user.id
    ).first()
    assert lock_entry is not None
    assert lock_entry.amount_kopecks == -10000
    assert lock_entry.reference_id == order.id


@pytest.mark.integration
def test_place_bet_insufficient_funds(test_client, test_db_session, sample_user):
    """Test bet fails with insufficient funds"""
    # Setup: small deposit + market
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=5000,  # 50₽
        type='deposit'
    ))
    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    # Try to place bet for 100₽
    response = test_client.post(
        "/bets/",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )

    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]


@pytest.mark.integration
def test_place_bet_market_not_found(test_client, test_db_session, sample_user):
    """Test bet fails for non-existent market"""
    # Setup: deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    # Try to place bet on non-existent market
    response = test_client.post(
        "/bets/",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": 99999,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )

    assert response.status_code == 404
    assert "Market not found" in response.json()["detail"]


@pytest.mark.integration
def test_place_bet_resolved_market(test_client, test_db_session, sample_user):
    """Test bet fails on resolved market"""
    # Setup: deposit + resolved market
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    market = Market(
        title="Resolved Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) - timedelta(days=1),
        resolved=True,
        resolution_value=True
    )
    test_db_session.add(market)
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.post(
        "/bets/",
        headers={"Authorization": f"twa {init_data}"},
        json={
            "market_id": market.id,
            "side": "yes",
            "price": 0.65,
            "amount": 100
        }
    )

    assert response.status_code == 400
    assert "already resolved" in response.json()["detail"]


@pytest.mark.integration
def test_get_orders_empty(test_client, test_db_session, sample_user):
    """Test GET /bets/orders with no orders"""
    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/bets/orders",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
def test_get_orders_with_data(test_client, test_db_session, sample_user):
    """Test GET /bets/orders returns user orders"""
    # Setup: market + order
    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    order = Order(
        user_id=sample_user.id,
        market_id=market.id,
        side="yes",
        price_bp=6500,
        amount_kopecks=10000,
        status='open'
    )
    test_db_session.add(order)
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/bets/orders",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == order.id
    assert data[0]["market_id"] == market.id
    assert data[0]["side"] == "yes"
    assert data[0]["price"] == 0.65
    assert data[0]["amount"] == 100.0
    assert data[0]["status"] == "open"


@pytest.mark.integration
def test_cancel_order_success(test_client, test_db_session, sample_user):
    """Test successful order cancellation"""
    # Setup: deposit + market + order
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    order = Order(
        user_id=sample_user.id,
        market_id=market.id,
        side="yes",
        price_bp=6500,
        amount_kopecks=10000,
        status='open'
    )
    test_db_session.add(order)
    test_db_session.flush()

    # Lock funds
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=-10000,
        type='order_lock',
        reference_id=order.id
    ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    # Cancel order
    response = test_client.delete(
        f"/bets/{order.id}",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["order_id"] == order.id
    assert data["status"] == "cancelled"
    assert data["unlocked_amount"] == 100.0

    # Verify order status updated
    test_db_session.refresh(order)
    assert order.status == "cancelled"

    # Verify funds unlocked
    unlock_entry = test_db_session.query(LedgerEntry).filter(
        LedgerEntry.type == 'order_unlock',
        LedgerEntry.user_id == sample_user.id,
        LedgerEntry.reference_id == order.id
    ).first()
    assert unlock_entry is not None
    assert unlock_entry.amount_kopecks == 10000


@pytest.mark.integration
def test_cancel_order_not_found(test_client, test_db_session, sample_user):
    """Test cancelling non-existent order returns 404"""
    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.delete(
        "/bets/99999",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 404
    assert "Order not found" in response.json()["detail"]


@pytest.mark.integration
def test_cancel_order_already_cancelled(test_client, test_db_session, sample_user):
    """Test cannot cancel already cancelled order"""
    # Setup: cancelled order
    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    order = Order(
        user_id=sample_user.id,
        market_id=market.id,
        side="yes",
        price_bp=6500,
        amount_kopecks=10000,
        status='cancelled'  # Already cancelled
    )
    test_db_session.add(order)
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.delete(
        f"/bets/{order.id}",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 400
    assert "Cannot cancel order with status" in response.json()["detail"]


@pytest.mark.integration
def test_cancel_other_user_order(test_client, test_db_session, sample_user):
    """Test cannot cancel another user's order"""
    # Setup: market + order from another user
    from app.db.models import User
    other_user = User(
        telegram_id=9999,
        username="otheruser",
        first_name="Other"
    )
    test_db_session.add(other_user)
    test_db_session.flush()

    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    order = Order(
        user_id=other_user.id,  # Different user
        market_id=market.id,
        side="yes",
        price_bp=6500,
        amount_kopecks=10000,
        status='open'
    )
    test_db_session.add(order)
    test_db_session.commit()

    # Try to cancel as sample_user
    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.delete(
        f"/bets/{order.id}",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 404  # Returns 404 (security through obscurity)
