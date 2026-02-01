"""
Rate Limiting Configuration

Uses slowapi for rate limiting authentication endpoints
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Callable
from fastapi import Request


def get_user_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting

    For authenticated requests: use telegram_id from user state
    For unauthenticated: use IP address
    """
    # Check if user is authenticated (set by dependency)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.telegram_id}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Create limiter instance
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["1000 per hour"],  # Global default
    storage_uri="memory://",  # Use in-memory storage (upgrade to Redis for production)
)
