"""
Pravda Market API - FastAPI Application

Простое prediction market приложение для Telegram Mini App
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db.session import get_db, init_db
from app.db.models import Market
from app.api.routes import users

# Создаем FastAPI приложение
app = FastAPI(
    title="Pravda Market API",
    description="Платформа коллективных прогнозов для российского рынка",
    version="0.1.0",
)


# Инициализация database при старте
@app.on_event("startup")
async def startup_event():
    """
    Выполняется при запуске приложения

    Создает database tables если их нет
    """
    init_db()
    print("[OK] Database initialized")

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


@app.get("/")
async def root():
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
async def health():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/markets")
async def get_markets(db: Session = Depends(get_db)):
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


# Запуск приложения:
# uvicorn app.main:app --reload
#
# Тестирование:
# curl http://localhost:8000/
# curl http://localhost:8000/markets
