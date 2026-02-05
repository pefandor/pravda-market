"""
Security Module - Telegram WebApp Authentication

Validates Telegram initData using HMAC-SHA256
"""

import hmac
import hashlib
import json
from urllib.parse import parse_qsl
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.core.config import settings

# Get BOT_TOKEN from settings
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# Init data max age (24 hours)
INIT_DATA_MAX_AGE = timedelta(hours=24)


def validate_telegram_init_data(init_data: str) -> dict:
    """
    Validate Telegram WebApp initData

    Checks:
    1. HMAC-SHA256 signature
    2. Timestamp (not older than 24 hours)
    3. Required fields present

    Args:
        init_data: Raw initData string from Telegram WebApp

    Returns:
        dict: User data (user_id, username, first_name, auth_date)

    Raises:
        HTTPException(401): If validation fails

    Example:
        init_data = "query_id=xxx&user=%7B%22id%22%3A123%7D&auth_date=1234567890&hash=abc..."
        user_data = validate_telegram_init_data(init_data)
        # {"user_id": 123, "username": "john", "first_name": "John", "auth_date": datetime(...)}
    """

    try:
        # Parse init_data into key-value pairs
        parsed = dict(parse_qsl(init_data))

        # Extract hash (signature)
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            raise ValueError("Missing hash in initData")

        # Check auth_date (timestamp)
        auth_date_str = parsed.get('auth_date')
        if not auth_date_str:
            raise ValueError("Missing auth_date in initData")

        auth_date = int(auth_date_str)
        auth_datetime = datetime.fromtimestamp(auth_date, tz=timezone.utc)

        # Check if expired (older than 24 hours)
        if datetime.now(timezone.utc) - auth_datetime > INIT_DATA_MAX_AGE:
            raise ValueError(f"Init data expired (older than {INIT_DATA_MAX_AGE})")

        # Create data-check-string
        # Format: "key1=value1\nkey2=value2\n..." (sorted by keys)
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        # Calculate secret key
        # secret_key = HMAC-SHA256(BOT_TOKEN, "WebAppData")
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Calculate hash
        # hash = HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Compare hashes (constant-time comparison to prevent timing attacks)
        if not hmac.compare_digest(calculated_hash, received_hash):
            raise ValueError("Invalid hash - authentication failed")

        # Parse user data from JSON
        user_json = parsed.get('user', '{}')
        user_data = json.loads(user_json)

        # Extract user info
        return {
            'user_id': user_data.get('id'),
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'auth_date': auth_datetime
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=401,
            detail="Invalid user data format"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Authentication error"
        )


def create_mock_init_data(user_id: int, username: str = "testuser", first_name: str = "Test") -> str:
    """
    Create mock initData for testing (ONLY FOR DEVELOPMENT!)

    WARNING: This bypasses security! Only use in development/testing.

    Args:
        user_id: Telegram user ID
        username: Username (optional)
        first_name: First name

    Returns:
        str: Valid initData string that will pass validation

    Example:
        init_data = create_mock_init_data(123, "john", "John")
        # Can be used with validate_telegram_init_data() for testing
    """
    from time import time

    # Create user data
    user = {
        "id": user_id,
        "username": username,
        "first_name": first_name
    }

    # Create parsed data
    auth_date = int(time())
    parsed = {
        'query_id': 'test_query_id',
        'user': json.dumps(user),
        'auth_date': str(auth_date)
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

    return init_data
