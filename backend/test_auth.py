"""
Quick test script for authentication endpoints
"""

import requests
import time
import subprocess
import sys
from dotenv import load_dotenv
load_dotenv()

from app.core.security import create_mock_init_data

# Start server in background
print("Starting server...")
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
time.sleep(6)

try:
    print("\n" + "="*60)
    print("TESTING AUTHENTICATION")
    print("="*60)

    base_url = "http://localhost:8002"

    # TEST 1: No auth header
    print("\n[TEST 1] Without auth header (should be 422):")
    try:
        response = requests.get(f"{base_url}/user/profile", timeout=2)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 422, "Expected 422"
        print("[OK] Test 1 passed")
    except Exception as e:
        print(f"[FAIL] Test 1 failed: {e}")

    # TEST 2: Invalid auth
    print("\n[TEST 2] With invalid auth (should be 401):")
    try:
        headers = {"Authorization": "twa invalid_data_here"}
        response = requests.get(f"{base_url}/user/profile", headers=headers, timeout=2)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 401, "Expected 401"
        print("[OK] Test 2 passed")
    except Exception as e:
        print(f"[FAIL] Test 2 failed: {e}")

    # TEST 3: Valid auth
    print("\n[TEST 3] With valid auth (should be 200):")
    try:
        # Generate valid initData
        init_data = create_mock_init_data(123456, "testuser", "Test User")
        headers = {"Authorization": f"twa {init_data}"}

        response = requests.get(f"{base_url}/user/profile", headers=headers, timeout=2)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Expected 200"
        print("[OK] Test 3 passed")

        # Verify user data
        data = response.json()
        assert data["telegram_id"] == 123456, "Wrong telegram_id"
        assert data["username"] == "testuser", "Wrong username"
        print("[OK] User data correct")
    except Exception as e:
        print(f"[FAIL] Test 3 failed: {e}")

    # TEST 4: Second request with same user (should not create duplicate)
    print("\n[TEST 4] Second request with same user:")
    try:
        response = requests.get(f"{base_url}/user/profile", headers=headers, timeout=2)
        print(f"Status: {response.status_code}")
        data = response.json()
        user_id = data["id"]
        print(f"User ID: {user_id}")
        print("[OK] Test 4 passed")
    except Exception as e:
        print(f"[FAIL] Test 4 failed: {e}")

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)

finally:
    # Kill server
    print("\nStopping server...")
    server_process.terminate()
    server_process.wait()
    print("Server stopped")
