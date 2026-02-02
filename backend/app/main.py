"""
Pravda Market API - FastAPI Application

Простое prediction market приложение для Telegram Mini App
"""

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, List, Any
from contextlib import asynccontextmanager
import os

from app.db.session import get_db, init_db
from app.db.models import Market, Order
from app.api.routes import users, bets, ledger, admin
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
    init_db()
    logger.info("Database initialized successfully")

    yield

    # Shutdown (if needed)
    logger.info("Shutting down Pravda Market API")


# Создаем FastAPI приложение с lifespan
app = FastAPI(
    title="Pravda Market API",
    description="Платформа коллективных прогнозов для российского рынка",
    version="0.1.0",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add structured exception handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# CORS для frontend (Telegram Mini App)
# SECURITY: Restrict origins in production (configured via ALLOWED_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(users.router)
app.include_router(bets.router)
app.include_router(ledger.router)
app.include_router(admin.router)


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
        "timestamp": datetime.now().isoformat(),
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
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["status"] = "not_ready"
        checks["checks"]["database"] = f"error: {str(e)}"
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
