"""
Unit Tests for Balance Service

Тесты для ledger-based balance management
"""

import pytest
from app.services.balance import (
    get_user_balance,
    get_available_balance,
    has_sufficient_balance
)
from app.db.models import LedgerEntry


@pytest.mark.unit
def test_get_user_balance_no_entries(test_db_session, sample_user):
    """Test balance is 0 when no ledger entries"""
    balance = get_user_balance(sample_user.id, test_db_session)
    assert balance == 0


@pytest.mark.unit
def test_get_user_balance_single_deposit(test_db_session, sample_user):
    """Test balance calculation with single deposit"""
    # Add deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,  # 1000₽
        type='deposit'
    ))
    test_db_session.commit()

    balance = get_user_balance(sample_user.id, test_db_session)
    assert balance == 100000


@pytest.mark.unit
def test_get_user_balance_multiple_entries(test_db_session, sample_user):
    """Test balance calculation with multiple entries"""
    # Deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,  # 1000₽
        type='deposit'
    ))
    # Lock
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=-30000,  # -300₽
        type='order_lock'
    ))
    # Another deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=50000,  # 500₽
        type='deposit'
    ))
    test_db_session.commit()

    balance = get_user_balance(sample_user.id, test_db_session)
    assert balance == 120000  # 1000 - 300 + 500


@pytest.mark.unit
def test_available_balance_no_locks(test_db_session, sample_user):
    """Test available balance equals total when no locks"""
    # Deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    test_db_session.commit()

    total = get_user_balance(sample_user.id, test_db_session)
    available = get_available_balance(sample_user.id, test_db_session)

    assert total == available == 100000


@pytest.mark.unit
def test_available_balance_with_locked(test_db_session, sample_user):
    """Test available balance with locked funds"""
    # Deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    # Lock
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=-30000,
        type='order_lock'
    ))
    test_db_session.commit()

    total = get_user_balance(sample_user.id, test_db_session)
    available = get_available_balance(sample_user.id, test_db_session)

    assert total == 70000  # 1000 - 300
    assert available == 70000


@pytest.mark.unit
def test_has_sufficient_balance_true(test_db_session, sample_user):
    """Test sufficient balance check returns True"""
    # Deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    test_db_session.commit()

    assert has_sufficient_balance(sample_user.id, 50000, test_db_session) is True
    assert has_sufficient_balance(sample_user.id, 100000, test_db_session) is True


@pytest.mark.unit
def test_has_sufficient_balance_false(test_db_session, sample_user):
    """Test sufficient balance check returns False"""
    # Deposit
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=100000,
        type='deposit'
    ))
    test_db_session.commit()

    assert has_sufficient_balance(sample_user.id, 100001, test_db_session) is False
    assert has_sufficient_balance(sample_user.id, 200000, test_db_session) is False


@pytest.mark.unit
def test_available_balance_never_negative(test_db_session, sample_user):
    """Test available balance never returns negative"""
    # No deposits, only lock (should not happen in real scenario)
    test_db_session.add(LedgerEntry(
        user_id=sample_user.id,
        amount_kopecks=-10000,
        type='order_lock'
    ))
    test_db_session.commit()

    available = get_available_balance(sample_user.id, test_db_session)
    assert available == 0  # Should return 0, not negative
