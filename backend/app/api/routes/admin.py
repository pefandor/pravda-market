"""
Admin API Routes

Administrative endpoints for market management.
Requires admin authentication.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any
import os

from app.db.session import get_db
from app.db.models import Market
from app.core.rate_limit import limiter
from app.core.logging_config import get_logger

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

logger = get_logger()


class ResolveRequest(BaseModel):
    """Request body for market resolution"""
    outcome: str  # "yes" or "no"

    class Config:
        json_schema_extra = {
            "example": {
                "outcome": "yes"
            }
        }


def get_admin_user(authorization: str = Header(...)) -> bool:
    """
    Admin authentication dependency

    For MVP: Simple token-based authentication via environment variable.
    Production: Replace with proper role-based auth (JWT, OAuth, etc.)

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        True if authenticated as admin

    Raises:
        HTTPException: 403 if not authorized
    """
    admin_token = os.getenv("ADMIN_TOKEN", "admin_secret_token")
    expected_header = f"Bearer {admin_token}"

    if authorization != expected_header:
        logger.warning("Unauthorized admin access attempt", extra={
            "provided_auth": authorization[:20] + "..." if len(authorization) > 20 else authorization
        })
        raise HTTPException(
            status_code=403,
            detail="Admin access required. Please provide valid admin token."
        )

    return True


@router.post("/markets/{market_id}/resolve", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def resolve_market(
    request: Request,
    market_id: int,
    resolve_request: ResolveRequest,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Resolve a market and distribute payouts

    Admin-only endpoint. Settles all trades for the market based on outcome.

    Args:
        market_id: ID of the market to resolve
        resolve_request: Contains outcome ("yes" or "no")

    Returns:
        Success message with settlement statistics

    Raises:
        403: If not admin
        404: If market not found
        400: If market already resolved or invalid outcome
    """
    from app.services.settlement import settle_market

    # Validate outcome
    if resolve_request.outcome not in ["yes", "no"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outcome: {resolve_request.outcome}. Must be 'yes' or 'no'."
        )

    # Check market exists
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(
            status_code=404,
            detail=f"Market with ID {market_id} not found."
        )

    # Check market not already resolved
    if market.resolved:
        raise HTTPException(
            status_code=400,
            detail=f"Market {market_id} is already resolved with outcome: {market.outcome}"
        )

    logger.info("Resolving market", extra={
        "market_id": market_id,
        "outcome": resolve_request.outcome,
        "title": market.title
    })

    # Settle market (this updates market.resolved = True)
    try:
        settlement_stats = settle_market(market_id, resolve_request.outcome, db)

        logger.info("Market resolved successfully", extra={
            "market_id": market_id,
            "outcome": resolve_request.outcome,
            **settlement_stats
        })

        return {
            "success": True,
            "market_id": market_id,
            "outcome": resolve_request.outcome,
            **settlement_stats
        }

    except Exception as e:
        db.rollback()
        logger.error("Market resolution failed", extra={
            "market_id": market_id,
            "outcome": resolve_request.outcome,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve market: {str(e)}"
        )
