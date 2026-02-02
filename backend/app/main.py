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
from app.api.routes import users, bets, ledger
from app.core.logging_config import setup_logging, get_logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager - replaces deprecated on_event("startup")

    Выполняется при запуске и остановке приложения
    """
    # Startup: Setup logging and initialize database
    log_level = os.getenv("LOG_LEVEL", "INFO")
    json_logs = os.getenv("LOG_FORMAT", "text") == "json"
    setup_logging(level=log_level, json_format=json_logs)

    logger = get_logger()
    logger.info("Starting Pravda Market API", extra={
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development")
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

# CORS для frontend (Telegram Mini App)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(users.router)
app.include_router(bets.router)
app.include_router(ledger.router)


@app.get("/")
def root() -> Dict[str, str]:
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
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/markets")
async def get_markets(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
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
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        from fastapi import HTTPException
        raise HTTPException(404, "Market not found")

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
