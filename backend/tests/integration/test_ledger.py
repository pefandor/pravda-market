"""
Integration Tests for Ledger Endpoints

Тесты для GET /ledger/transactions
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.db.models import Market, LedgerEntry, Order
from app.core.security import create_mock_init_data


@pytest.mark.integration
def test_get_transactions_empty(test_client, test_db_session, sample_user):
    """Test GET /ledger/transactions with no transactions"""
    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
def test_get_transactions_deposit_only(test_client, test_db_session, sample_user):
    """Test GET /ledger/transactions with deposit"""
    # Add deposit
    deposit = LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,  # 1000₽
        type='deposit'
    )
    test_db_session.add(deposit)
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "deposit"
    assert data[0]["amount_rubles"] == 1000.0
    assert data[0]["reference_id"] is None
    assert "Deposit: +1000.00₽" in data[0]["description"]


@pytest.mark.integration
def test_get_transactions_full_flow(test_client, test_db_session, sample_user):
    """Test transaction history for full order lifecycle"""
    # Setup: market
    market = Market(
        title="Test Market",
        description="Test",
        category="test",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        resolved=False
    )
    test_db_session.add(market)
    test_db_session.flush()

    # 1. Deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))

    # 2. Create order (lock funds)
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

    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=-10000,
        type='order_lock',
        reference_id=order.id
    ))

    # 3. Cancel order (unlock funds)
    order.status = 'cancelled'
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=10000,
        type='order_unlock',
        reference_id=order.id
    ))

    test_db_session.commit()

    # Get transactions
    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Verify order (desc by created_at, so unlock is first)
    assert data[0]["type"] == "order_unlock"
    assert data[0]["amount_rubles"] == 100.0
    assert data[0]["reference_id"] == order.id

    assert data[1]["type"] == "order_lock"
    assert data[1]["amount_rubles"] == -100.0
    assert data[1]["reference_id"] == order.id

    assert data[2]["type"] == "deposit"
    assert data[2]["amount_rubles"] == 1000.0


@pytest.mark.integration
def test_get_transactions_pagination_default(test_client, test_db_session, sample_user):
    """Test pagination with default limit"""
    # Create 60 transactions
    for i in range(60):
        test_db_session.add(LedgerEntry(
            user_id=sample_user.id,
            amount_kopecks=1000,
            type='deposit'
        ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 50  # Default limit


@pytest.mark.integration
def test_get_transactions_pagination_custom_limit(test_client, test_db_session, sample_user):
    """Test pagination with custom limit"""
    # Create 30 transactions
    for i in range(30):
        test_db_session.add(LedgerEntry(
            user_id=sample_user.id,
            amount_kopecks=1000,
            type='deposit'
        ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions?limit=10",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10


@pytest.mark.integration
def test_get_transactions_pagination_max_limit(test_client, test_db_session, sample_user):
    """Test limit is capped at 100"""
    # Create 120 transactions
    for i in range(120):
        test_db_session.add(LedgerEntry(
            user_id=sample_user.id,
            amount_kopecks=1000,
            type='deposit'
        ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    # Request 200, should get max 100
    response = test_client.get(
        "/ledger/transactions?limit=200",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 100  # Capped at 100


@pytest.mark.integration
def test_get_transactions_pagination_offset(test_client, test_db_session, sample_user):
    """Test pagination with offset"""
    # Create 20 transactions
    for i in range(20):
        test_db_session.add(LedgerEntry(
            user_id=sample_user.id,
            amount_kopecks=1000 + i,  # Different amounts for verification
            type='deposit'
        ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    # Get first page
    response1 = test_client.get(
        "/ledger/transactions?limit=10&offset=0",
        headers={"Authorization": f"twa {init_data}"}
    )

    # Get second page
    response2 = test_client.get(
        "/ledger/transactions?limit=10&offset=10",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    page1 = response1.json()
    page2 = response2.json()

    assert len(page1) == 10
    assert len(page2) == 10

    # Verify no overlap
    page1_ids = {t["id"] for t in page1}
    page2_ids = {t["id"] for t in page2}
    assert len(page1_ids & page2_ids) == 0  # No common IDs


@pytest.mark.integration
def test_get_transactions_only_own_transactions(test_client, test_db_session, sample_user):
    """Test user can only see their own transactions"""
    # Create other user
    from app.db.models import User
    other_user = User(
        telegram_id=9999,
        username="otheruser",
        first_name="Other"
    )
    test_db_session.add(other_user)
    test_db_session.flush()

    # Add transactions for both users
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=10000,
        type='deposit'
    ))
    test_db_session.add(LedgerEntry(
        user_id=other_user.id,
        amount_kopecks=20000,
        type='deposit'
    ))
    test_db_session.commit()

    # Get transactions as sample_user
    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1  # Only sample_user's transaction
    assert data[0]["amount_rubles"] == 100.0  # sample_user's deposit


@pytest.mark.integration
def test_get_transactions_description_formats(test_client, test_db_session, sample_user):
    """Test different transaction types have correct descriptions"""
    # Create different transaction types
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

    # Different transaction types
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=-10000,
        type='order_lock',
        reference_id=order.id
    ))
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=10000,
        type='order_unlock',
        reference_id=order.id
    ))
    test_db_session.commit()

    init_data = create_mock_init_data(user_id=sample_user.telegram_id)

    response = test_client.get(
        "/ledger/transactions",
        headers={"Authorization": f"twa {init_data}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Find each type and verify description
    types_found = {t["type"]: t["description"] for t in data}

    assert "deposit" in types_found
    assert "Deposit: +1000.00₽" in types_found["deposit"]

    assert "order_lock" in types_found
    assert f"Locked for order #{order.id}" == types_found["order_lock"]

    assert "order_unlock" in types_found
    assert f"Unlocked from order #{order.id}" == types_found["order_unlock"]
