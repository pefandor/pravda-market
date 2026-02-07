"""
Pravda Market API - FastAPI Application

Простое prediction market приложение для Telegram Mini App
"""

from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from contextlib import asynccontextmanager
import os

from app.db.session import get_db, init_db
from app.db.models import Market, Order
from app.api.routes import users, bets, ledger, admin, withdrawals
from app.core.logging_config import setup_logging, get_logger
from app.core.config import settings
from app.core.exceptions import (
    APIException,
    api_exception_handler,
    http_exception_handler
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
from fastapi import HTTPException


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager - replaces deprecated on_event("startup")

    Выполняется при запуске и остановке приложения
    """
    # Startup: Setup logging and initialize database
    setup_logging(level=settings.LOG_LEVEL, json_format=settings.use_json_logs)

    logger = get_logger()
    logger.info("Starting Pravda Market API", extra={
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT
    })

    # Initialize database
    # Production: Alembic migrations run before app start (see Dockerfile CMD)
    # Development (SQLite): Use create_all as fallback for convenience
    if settings.is_development and settings.DATABASE_URL.startswith("sqlite"):
        init_db()
        logger.info("Database initialized via create_all (dev mode)")
    else:
        logger.info("Skipping create_all — using Alembic migrations")

    # Start TON deposit indexer (if enabled)
    if settings.TON_INDEXER_ENABLED:
        from app.ton.indexer import start_deposit_indexer
        await start_deposit_indexer()
        logger.info("TON deposit indexer started")
    else:
        logger.info("TON deposit indexer disabled (TON_INDEXER_ENABLED=False)")

    yield

    # Shutdown
    if settings.TON_INDEXER_ENABLED:
        from app.ton.indexer import stop_deposit_indexer
        await stop_deposit_indexer()
        logger.info("TON deposit indexer stopped")

    logger.info("Shutting down Pravda Market API")


# Создаем FastAPI приложение с lifespan
# SECURITY: Hide Swagger/ReDoc in production (prevent API exploration by attackers)
app = FastAPI(
    title="Pravda Market API",
    description="Платформа коллективных прогнозов для российского рынка",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add structured exception handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Security headers middleware (runs AFTER CORS middleware in the stack)
app.add_middleware(SecurityHeadersMiddleware)

# CORS для frontend (Telegram Mini App)
# SECURITY: Restrict origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Подключение роутеров
app.include_router(users.router)
app.include_router(bets.router)
app.include_router(ledger.router)
app.include_router(admin.router)
app.include_router(withdrawals.router)


@app.get("/")
@limiter.limit("100/minute")
def root(request: Request) -> Dict[str, str]:
    """
    Корневой endpoint - проверка что API работает
    """
    return {
        "message": "Pravda Market API",
        "status": "working",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request) -> Dict[str, str]:
    """
    Basic health check endpoint

    Returns 200 if application is running.
    Use for liveness probes.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/ready")
@limiter.limit("60/minute")
async def health_ready(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check endpoint for Kubernetes

    Verifies that application is ready to serve traffic:
    - Database connection is working
    - All dependencies are available

    Returns:
        200: Application is ready
        503: Application is not ready (with details)

    Use for readiness probes in K8s deployments.
    """
    from fastapi import HTTPException
    from sqlalchemy import text

    checks = {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }

    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        checks["checks"]["database"] = "ok"
    except Exception as e:
        logger = get_logger()
        logger.error("Database health check failed", extra={"error": str(e)})
        checks["status"] = "not_ready"
        checks["checks"]["database"] = "unavailable"
        raise HTTPException(503, detail=checks)

    # Add more checks here as needed
    # - Redis connection (if using)
    # - External API availability
    # - File system access

    return checks


@app.get("/markets")
@limiter.limit("60/minute")
async def get_markets(request: Request, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Получить список активных рынков из database

    Returns: List of active (unresolved) markets
    """
    # Получить активные рынки из database
    markets = db.query(Market).filter(Market.resolved == False).all()

    # Конвертировать в JSON-friendly format
    return [
        {
            "id": market.id,
            "title": market.title,
            "description": market.description,
            "deadline": market.deadline.isoformat(),
            "resolved": market.resolved,
            "yes_price": market.yes_price_decimal,  # 0.0 - 1.0
            "no_price": market.no_price_decimal,
            "volume": market.volume_rubles,  # в рублях
            "category": market.category,
        }
        for market in markets
    ]


@app.get("/markets/{market_id}")
@limiter.limit("60/minute")
async def get_market(
    request: Request,
    market_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a single market by ID
    """
    from app.core.exceptions import MarketNotFoundException
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise MarketNotFoundException(market_id)

    return {
        "id": market.id,
        "title": market.title,
        "description": market.description,
        "deadline": market.deadline.isoformat(),
        "resolved": market.resolved,
        "outcome": market.outcome,
        "yes_price": market.yes_price_decimal,
        "no_price": market.no_price_decimal,
        "volume": market.volume_rubles,
        "category": market.category,
    }


@app.get("/markets/{market_id}/orderbook")
@limiter.limit("60/minute")
async def get_orderbook(
    request: Request,
    market_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get orderbook for a specific market

    Returns aggregated orders by price level for privacy.
    Does not show individual user orders.

    Args:
        market_id: ID of the market

    Returns:
        Dictionary with yes_orders and no_orders aggregated by price

    Security:
        - Aggregates by price level (privacy: no user identification)
        - Only shows open/partial orders (not filled/cancelled)
    """
    # Check market exists
    from app.core.exceptions import MarketNotFoundException
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise MarketNotFoundException(market_id)

    # PERFORMANCE: Aggregate in SQL using GROUP BY (not Python)
    # Get YES orders aggregated by price level
    yes_results = db.query(
        Order.price_bp,
        func.sum(Order.amount_kopecks - Order.filled_kopecks).label('total_remaining')
    ).filter(
        Order.market_id == market_id,
        Order.side == 'yes',
        Order.status.in_(['open', 'partial'])
    ).group_by(Order.price_bp).all()

    # Get NO orders aggregated by price level
    no_results = db.query(
        Order.price_bp,
        func.sum(Order.amount_kopecks - Order.filled_kopecks).label('total_remaining')
    ).filter(
        Order.market_id == market_id,
        Order.side == 'no',
        Order.status.in_(['open', 'partial'])
    ).group_by(Order.price_bp).all()

    # Format response (sorted by best price first)
    return {
        "market_id": market_id,
        "yes_orders": [
            {"price": price_bp / 10000, "amount": total / 100}
            for price_bp, total in sorted(yes_results, key=lambda x: x[0], reverse=True)
        ],
        "no_orders": [
            {"price": price_bp / 10000, "amount": total / 100}
            for price_bp, total in sorted(no_results, key=lambda x: x[0], reverse=True)
        ]
    }


# Запуск приложения:
# uvicorn app.main:app --reload
#
# Тестирование:
# curl http://localhost:8000/
# curl http://localhost:8000/markets
# curl http://localhost:8000/markets/1/orderbook
