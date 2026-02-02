"""
Pytest Configuration and Fixtures

Shared test fixtures for backend testing
"""

import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.db.models import Base, User
from app.core.security import create_mock_init_data

# Get test database URL from environment or use SQLite as fallback
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///./test_pravda_market.db"
)

# Determine if using SQLite
is_sqlite = TEST_DATABASE_URL.startswith("sqlite")

# Create test database engine
if is_sqlite:
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 60,  # Increased timeout for slower systems
            "isolation_level": None  # Autocommit mode to reduce locking
        }
    )
    # Enable WAL mode for better concurrency (SQLite only)
    with test_engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=60000"))  # 60 second busy timeout
        conn.commit()
else:
    # PostgreSQL settings
    test_engine = create_engine(
        TEST_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Set up test database tables once for entire test session

    autouse=True means this runs automatically before any tests
    """
    import os
    # Remove old test database if it exists
    if os.path.exists("test_pravda_market.db"):
        try:
            os.remove("test_pravda_market.db")
        except PermissionError:
            pass  # File in use, will be cleaned up later

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

    # Close all connections
    test_engine.dispose()

    # Cleanup: remove test database file
    if os.path.exists("test_pravda_market.db"):
        try:
            os.remove("test_pravda_market.db")
        except PermissionError:
            pass  # File in use, will be cleaned up on next run


@pytest.fixture(scope="function")
def test_db_session():
    """
    Create fresh database session for each test

    Scope: function (new session per test)
    Ensures test isolation via rollback and cleanup
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        try:
            db.rollback()  # Rollback uncommitted changes
            # Clean up tables to ensure isolation between tests
            # Use separate transactions to avoid long locks
            db.execute(text("DELETE FROM trades"))
            db.execute(text("DELETE FROM ledger"))
            db.execute(text("DELETE FROM orders"))
            db.execute(text("DELETE FROM markets"))
            db.execute(text("DELETE FROM users"))
            db.commit()
        except Exception as e:
            # If cleanup fails, just rollback and continue
            db.rollback()
        finally:
            db.close()


def get_test_db():
    """
    Override function for get_db dependency

    Yields test database session instead of production database
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_client():
    """
    FastAPI test client with database dependency overridden

    Uses TestClient which is synchronous (perfect for testing)
    """
    from app.main import app
    from app.db.session import get_db

    # Override database dependency
    app.dependency_overrides[get_db] = get_test_db

    # Disable rate limiting for tests
    app.state.limiter.enabled = False

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def mock_init_data():
    """
    Helper fixture to create valid Telegram initData

    Usage:
        init_data = mock_init_data(user_id=123, username="test", first_name="Test")
    """
    return create_mock_init_data


@pytest.fixture
def sample_user(test_db_session):
    """
    Create a sample user in the test database

    Returns:
        User object with telegram_id=123456

    Note: Doesn't commit - relies on test_db_session's rollback for isolation
    """
    user = User(
        telegram_id=123456,
        username="testuser",
        first_name="Test"
    )
    test_db_session.add(user)
    test_db_session.flush()  # Flush to get ID, but don't commit
    return user
