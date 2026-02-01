"""
User Routes

Endpoints for user profile and authentication
"""

from fastapi import APIRouter, Depends
from app.db.models import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/user", tags=["users"])


@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    """
    Get current user profile

    Requires authentication via Telegram initData

    Returns:
        User profile information

    Example:
        curl -H "Authorization: twa query_id=xxx&user=..." http://localhost:8000/user/profile
    """
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "created_at": user.created_at.isoformat()
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """
    Get current user (alias for /profile)

    Same as /user/profile but shorter URL
    """
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name
    }
