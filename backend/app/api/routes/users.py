"""
User Routes

Endpoints for user profile and authentication
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
from app.db.models import User
from app.api.deps import get_current_user
from app.core.rate_limit import limiter

router = APIRouter(prefix="/user", tags=["users"])


@router.get("/profile")
@limiter.limit("100/minute")
def get_profile(request: Request, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get current user profile

    Requires authentication via Telegram initData

    Returns:
        User profile information

    Example:
        curl -H "Authorization: twa query_id=xxx&user=..." http://localhost:8000/user/profile
    """
    # Store user in request state for rate limiter
    request.state.user = user

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "created_at": user.created_at.isoformat()
    }


@router.get("/me")
@limiter.limit("100/minute")
def get_me(request: Request, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get current user (alias for /profile)

    Same as /user/profile but shorter URL
    """
    # Store user in request state for rate limiter
    request.state.user = user

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name
    }
