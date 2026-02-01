"""
Unit Tests for app/api/deps.py

Tests for FastAPI authentication dependencies
"""

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user
from app.db.models import User


@pytest.mark.unit
def test_get_current_user_success(test_db_session, mock_init_data):
    """Test successful authentication with valid initData"""
    # Create valid initData
    init_data = mock_init_data(user_id=999, username="newuser", first_name="New")
    authorization = f"twa {init_data}"

    # Call dependency
    user = get_current_user(authorization=authorization, db=test_db_session)

    # Assert user was created and returned
    assert user.telegram_id == 999
    assert user.username == "newuser"
    assert user.first_name == "New"

    # Verify user was saved to database
    db_user = test_db_session.query(User).filter(User.telegram_id == 999).first()
    assert db_user is not None
    assert db_user.id == user.id


@pytest.mark.unit
def test_get_current_user_missing_header(test_db_session):
    """Test that missing Authorization header raises HTTPException"""
    # Note: FastAPI will handle this at the framework level,
    # but we can test the header validation logic
    authorization = ""

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=authorization, db=test_db_session)

    assert exc_info.value.status_code == 401


@pytest.mark.unit
def test_get_current_user_invalid_format(test_db_session):
    """Test that invalid header format raises HTTPException"""
    # Header without "twa " prefix
    authorization = "Bearer some_token_here"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=authorization, db=test_db_session)

    assert exc_info.value.status_code == 401
    assert "Invalid authorization header format" in exc_info.value.detail


@pytest.mark.unit
def test_get_current_user_invalid_init_data(test_db_session):
    """Test that invalid initData raises HTTPException"""
    # Use header with invalid initData
    authorization = "twa invalid_init_data_here"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=authorization, db=test_db_session)

    assert exc_info.value.status_code == 401


@pytest.mark.unit
def test_get_current_user_existing_user(test_db_session, sample_user, mock_init_data):
    """Test that existing user is returned without duplication"""
    # sample_user has telegram_id=123456
    initial_user_id = sample_user.id

    # Create initData for existing user
    init_data = mock_init_data(
        user_id=123456,
        username="testuser",
        first_name="Test"
    )
    authorization = f"twa {init_data}"

    # Call dependency
    user = get_current_user(authorization=authorization, db=test_db_session)

    # Assert same user is returned
    assert user.id == initial_user_id
    assert user.telegram_id == 123456

    # Verify no duplicate was created
    user_count = test_db_session.query(User).filter(
        User.telegram_id == 123456
    ).count()
    assert user_count == 1


@pytest.mark.unit
def test_get_current_user_auto_registration(test_db_session, mock_init_data):
    """Test that new user is automatically registered"""
    # Verify no user exists
    user_count_before = test_db_session.query(User).count()

    # Create initData for new user
    init_data = mock_init_data(
        user_id=777777,
        username="newbie",
        first_name="Newbie User"
    )
    authorization = f"twa {init_data}"

    # Call dependency
    user = get_current_user(authorization=authorization, db=test_db_session)

    # Assert new user was created
    assert user.telegram_id == 777777
    assert user.username == "newbie"
    assert user.first_name == "Newbie User"

    # Verify user count increased by 1
    user_count_after = test_db_session.query(User).count()
    assert user_count_after == user_count_before + 1

    # Verify user exists in database
    db_user = test_db_session.query(User).filter(
        User.telegram_id == 777777
    ).first()
    assert db_user is not None
    assert db_user.id == user.id
