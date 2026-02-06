"""
Integration Tests for app/api/routes/users.py

Tests for user API endpoints
"""

import pytest


@pytest.mark.integration
def test_get_profile_success(test_client, mock_init_data):
    """Test GET /user/profile with valid authentication"""
    # Create auth header
    init_data = mock_init_data(user_id=123, username="test", first_name="Test")
    headers = {"Authorization": f"twa {init_data}"}

    # Make request
    response = test_client.get("/user/profile", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    # Profile now has nested user object and balance
    assert "user" in data
    assert "balance" in data
    assert data["user"]["telegram_id"] == 123
    assert data["user"]["username"] == "test"
    assert data["user"]["first_name"] == "Test"
    assert "id" in data["user"]
    assert "created_at" in data["user"]
    # New users get welcome bonus of 1000 rubles = 100000 kopecks
    assert data["balance"] == 100000


@pytest.mark.integration
def test_get_profile_unauthorized(test_client):
    """Test GET /user/profile without authentication"""
    # Make request without Authorization header
    response = test_client.get("/user/profile")

    # Assert - FastAPI returns 422 for missing required header
    assert response.status_code == 422


@pytest.mark.integration
def test_get_profile_invalid_auth(test_client):
    """Test GET /user/profile with invalid authentication"""
    # Use invalid initData
    headers = {"Authorization": "twa invalid_data_here"}

    # Make request
    response = test_client.get("/user/profile", headers=headers)

    # Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_get_me_success(test_client, mock_init_data):
    """Test GET /user/me with valid authentication"""
    # Create auth header
    init_data = mock_init_data(user_id=456, username="test2", first_name="Test2")
    headers = {"Authorization": f"twa {init_data}"}

    # Make request to /user/me
    response = test_client.get("/user/me", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_id"] == 456
    assert data["username"] == "test2"
    assert data["first_name"] == "Test2"
    assert "id" in data


@pytest.mark.integration
def test_user_auto_registration_flow(test_client, mock_init_data):
    """Test user auto-registration on first request"""
    # Create auth header for new user
    init_data = mock_init_data(
        user_id=999999,
        username="newuser",
        first_name="New User"
    )
    headers = {"Authorization": f"twa {init_data}"}

    # First request - should create user
    response1 = test_client.get("/user/profile", headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    user_id_1 = data1["user"]["id"]

    # Second request - should return same user
    response2 = test_client.get("/user/profile", headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    user_id_2 = data2["user"]["id"]

    # Verify user_id is consistent
    assert user_id_1 == user_id_2
    assert data1["user"]["telegram_id"] == data2["user"]["telegram_id"] == 999999


@pytest.mark.integration
def test_profile_fields_correct(test_client, mock_init_data):
    """Test that profile response contains all expected fields"""
    # Create auth header
    init_data = mock_init_data(
        user_id=777,
        username="fieldtest",
        first_name="Field Test"
    )
    headers = {"Authorization": f"twa {init_data}"}

    # Make request
    response = test_client.get("/user/profile", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Check top-level fields
    assert "user" in data
    assert "balance" in data
    assert isinstance(data["balance"], int)  # balance in kopecks

    # Check all expected user fields exist
    user = data["user"]
    expected_fields = ["id", "telegram_id", "username", "first_name", "created_at", "updated_at"]
    for field in expected_fields:
        assert field in user, f"Missing field: {field}"

    # Check data types
    assert isinstance(user["id"], int)
    assert isinstance(user["telegram_id"], int)
    assert isinstance(user["username"], str)
    assert isinstance(user["first_name"], str)
    assert isinstance(user["created_at"], str)  # ISO format string

    # Verify created_at is ISO format (basic check)
    assert "T" in user["created_at"] or "-" in user["created_at"]
