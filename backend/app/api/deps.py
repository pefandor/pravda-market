"""
API Dependencies

FastAPI dependencies for authentication and database access
"""

from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.core.security import validate_telegram_init_data


async def get_current_user(
    authorization: str = Header(..., description="Telegram initData (format: 'twa <initData>')"),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from Telegram initData

    This is a FastAPI dependency that:
    1. Extracts initData from Authorization header
    2. Validates Telegram signature
    3. Gets or creates user in database
    4. Returns User object

    Usage in endpoints:
        @app.get("/user/profile")
        async def get_profile(user: User = Depends(get_current_user)):
            return {"user_id": user.id, "name": user.first_name}

    Args:
        authorization: HTTP header "Authorization: twa <initData>"
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException(401): If authorization header is invalid or missing
        HTTPException(401): If Telegram validation fails
    """

    # Check Authorization header format
    if not authorization.startswith("twa "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: 'Authorization: twa <initData>'"
        )

    # Extract initData (remove "twa " prefix)
    init_data = authorization[4:]

    # Validate Telegram initData (raises HTTPException if invalid)
    telegram_data = validate_telegram_init_data(init_data)

    telegram_id = telegram_data['user_id']
    if not telegram_id:
        raise HTTPException(
            status_code=401,
            detail="Missing user_id in Telegram data"
        )

    # Get or create user in database
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        # Auto-register new user
        user = User(
            telegram_id=telegram_id,
            username=telegram_data.get('username'),
            first_name=telegram_data.get('first_name')
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"[OK] New user registered: {user.telegram_id} ({user.first_name})")

    return user
