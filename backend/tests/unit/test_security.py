"""
Unit Tests for app/core/security.py

Tests for Telegram WebApp authentication validation
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from urllib.parse import urlencode
import json

from app.core.security import validate_telegram_init_data, create_mock_init_data


@pytest.mark.unit
@pytest.mark.security
def test_validate_telegram_init_data_success(mock_init_data):
    """Test successful validation of valid Telegram initData"""
    # Create valid initData
    init_data = mock_init_data(user_id=123, username="test", first_name="Test User")

    # Validate
    result = validate_telegram_init_data(init_data)

    # Assert
    assert result["user_id"] == 123
    assert result["username"] == "test"
    assert result["first_name"] == "Test User"
    assert isinstance(result["auth_date"], datetime)
    assert datetime.now(timezone.utc) - result["auth_date"] < timedelta(minutes=1)


@pytest.mark.unit
@pytest.mark.security
def test_validate_telegram_init_data_invalid_hash():
    """Test validation fails with invalid (tampered) hash"""
    # Create initData with tampered hash
    user = {"id": 123, "username": "test", "first_name": "Test"}
    init_data = urlencode({
        "query_id": "test_query",
        "user": json.dumps(user),
        "auth_date": str(int(datetime.now().timestamp())),
        "hash": "invalid_hash_value_12345"
    })

    # Expect HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_telegram_init_data(init_data)

    assert exc_info.value.status_code == 401
    assert "Authentication failed" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.security
def test_validate_telegram_init_data_missing_hash():
    """Test validation fails when hash parameter is missing"""
    # Create initData without hash
    user = {"id": 123, "username": "test", "first_name": "Test"}
    init_data = urlencode({
        "query_id": "test_query",
        "user": json.dumps(user),
        "auth_date": str(int(datetime.now().timestamp()))
        # No hash parameter
    })

    # Expect HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_telegram_init_data(init_data)

    assert exc_info.value.status_code == 401
    assert "Authentication failed" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.security
def test_validate_telegram_init_data_missing_auth_date():
    """Test validation fails when auth_date parameter is missing"""
    # Create initData without auth_date
    user = {"id": 123, "username": "test", "first_name": "Test"}
    init_data = urlencode({
        "query_id": "test_query",
        "user": json.dumps(user),
        # No auth_date
        "hash": "some_hash"
    })

    # Expect HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_telegram_init_data(init_data)

    assert exc_info.value.status_code == 401
    assert "Authentication failed" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.security
def test_validate_telegram_init_data_expired():
    """Test validation fails when timestamp is older than 24 hours"""
    # Create initData with old timestamp (25 hours ago)
    old_timestamp = int((datetime.now() - timedelta(hours=25)).timestamp())
    user = {"id": 123, "username": "test", "first_name": "Test"}

    # We need to create a properly signed but expired initData
    # We'll use create_mock_init_data and manually adjust the timestamp
    from app.core.security import BOT_TOKEN
    import hmac
    import hashlib

    parsed = {
        'query_id': 'test_query_id',
        'user': json.dumps(user),
        'auth_date': str(old_timestamp)
    }

    # Create data-check-string
    data_check_string = '\n'.join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Calculate secret key
    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=BOT_TOKEN.encode(),
        digestmod=hashlib.sha256
    ).digest()

    # Calculate hash
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    # Create initData string
    init_data = f"query_id={parsed['query_id']}&user={parsed['user']}&auth_date={parsed['auth_date']}&hash={calculated_hash}"

    # Expect HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_telegram_init_data(init_data)

    assert exc_info.value.status_code == 401
    assert "Authentication failed" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.security
def test_validate_telegram_init_data_invalid_user_json():
    """Test validation fails when user JSON is malformed"""
    # Create initData with invalid JSON
    init_data = urlencode({
        "query_id": "test_query",
        "user": "{invalid json here}",  # Malformed JSON
        "auth_date": str(int(datetime.now().timestamp())),
        "hash": "some_hash"
    })

    # Expect HTTPException (will fail on hash check first, or JSON parse)
    with pytest.raises(HTTPException) as exc_info:
        validate_telegram_init_data(init_data)

    assert exc_info.value.status_code == 401
    # Could fail on hash or JSON, both are valid


@pytest.mark.unit
@pytest.mark.security
def test_create_mock_init_data():
    """Test that create_mock_init_data generates valid initData"""
    # Create mock initData
    init_data = create_mock_init_data(
        user_id=999,
        username="mockuser",
        first_name="Mock User"
    )

    # Verify it's a string
    assert isinstance(init_data, str)

    # Verify it contains expected components
    assert "query_id=" in init_data
    assert "user=" in init_data
    assert "auth_date=" in init_data
    assert "hash=" in init_data

    # Verify it passes validation
    result = validate_telegram_init_data(init_data)

    assert result["user_id"] == 999
    assert result["username"] == "mockuser"
    assert result["first_name"] == "Mock User"
