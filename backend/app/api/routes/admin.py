"""
Admin API Routes

Administrative endpoints for market management.
Requires admin authentication.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import hmac

from app.db.session import get_db
from app.db.models import Market
from app.core.rate_limit import limiter
from app.core.logging_config import get_logger
from app.core.config import settings

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

logger = get_logger()


class ResolveRequest(BaseModel):
    """Request body for market resolution"""
    outcome: str  # "yes" or "no"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "outcome": "yes"
            }
        }
    )


class CreateMarketRequest(BaseModel):
    """Request body for creating a new market"""
    title: str = Field(..., min_length=10, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)
    deadline: datetime
    yes_price: float = Field(..., ge=0.01, le=0.99)  # 0.01 - 0.99

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Bitcoin достигнет $150,000 до июля 2026?",
                "description": "Цена BTC на любой крупной бирже достигнет $150,000 USD.",
                "category": "crypto",
                "deadline": "2026-07-01T00:00:00Z",
                "yes_price": 0.35
            }
        }
    )


class MarketResponse(BaseModel):
    """Response for created market"""
    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    deadline: datetime
    yes_price: float
    no_price: float
    volume: float
    resolved: bool

    model_config = ConfigDict(from_attributes=True)


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
    expected_header = f"Bearer {settings.ADMIN_TOKEN}"

    # SECURITY: Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(authorization, expected_header):
        logger.warning("Unauthorized admin access attempt")
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return True


@router.post("/markets", response_model=MarketResponse)
@limiter.limit("30/minute")
async def create_market(
    request: Request,
    market_request: CreateMarketRequest,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user)
) -> MarketResponse:
    """
    Create a new prediction market

    Admin-only endpoint for creating markets.

    Args:
        market_request: Market details (title, description, category, deadline, yes_price)

    Returns:
        Created market with ID

    Raises:
        403: If not admin
        400: If validation fails
    """
    # Validate deadline is in the future
    if market_request.deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Deadline must be in the future"
        )

    # Convert yes_price (0.0-1.0) to basis points (0-10000)
    yes_price_bp = int(market_request.yes_price * 10000)
    no_price_bp = 10000 - yes_price_bp

    # Create market
    market = Market(
        title=market_request.title,
        description=market_request.description,
        category=market_request.category,
        deadline=market_request.deadline,
        yes_price=yes_price_bp,
        no_price=no_price_bp,
        volume=0,
        resolved=False,
    )

    db.add(market)
    db.commit()
    db.refresh(market)

    logger.info("Market created", extra={
        "market_id": market.id,
        "title": market.title,
        "category": market.category,
        "deadline": market.deadline.isoformat(),
        "yes_price": market_request.yes_price,
    })

    return MarketResponse(
        id=market.id,
        title=market.title,
        description=market.description,
        category=market.category,
        deadline=market.deadline,
        yes_price=market.yes_price_decimal,
        no_price=market.no_price_decimal,
        volume=market.volume_rubles,
        resolved=market.resolved,
    )


@router.get("/markets", response_model=List[MarketResponse])
@limiter.limit("30/minute")
async def list_all_markets(
    request: Request,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user)
) -> List[MarketResponse]:
    """
    List all markets (including resolved)

    Admin-only endpoint for viewing all markets.
    """
    markets = db.query(Market).order_by(Market.id.desc()).all()

    return [
        MarketResponse(
            id=m.id,
            title=m.title,
            description=m.description,
            category=m.category,
            deadline=m.deadline,
            yes_price=m.yes_price_decimal,
            no_price=m.no_price_decimal,
            volume=m.volume_rubles,
            resolved=m.resolved,
        )
        for m in markets
    ]


@router.delete("/markets/{market_id}", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def delete_market(
    request: Request,
    market_id: int,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Delete a market (only if no orders exist)

    Admin-only endpoint. Cannot delete markets with existing orders.
    """
    from app.db.models import Order

    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail=f"Market {market_id} not found")

    # Check for existing orders
    order_count = db.query(Order).filter(Order.market_id == market_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete market with {order_count} existing orders"
        )

    title = market.title
    db.delete(market)
    db.commit()

    logger.info("Market deleted", extra={"market_id": market_id, "title": title})

    return {"success": True, "deleted_market_id": market_id}


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

    # Settle market (creates ledger entries, does NOT commit)
    try:
        settlement_stats = settle_market(market_id, resolve_request.outcome, db)

        # CRITICAL: Commit in the route handler (not in the service)
        # This gives the caller control over the transaction boundary
        db.commit()

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
            detail="Failed to resolve market. Please check server logs."
        )
