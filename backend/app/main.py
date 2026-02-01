"""
Pravda Market API - FastAPI Application

Простое prediction market приложение для Telegram Mini App
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

# Создаем FastAPI приложение
app = FastAPI(
    title="Pravda Market API",
    description="Платформа коллективных прогнозов для российского рынка",
    version="0.1.0",
)

# CORS для frontend (Telegram Mini App)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def get_markets():
    """
    Получить список активных рынков (пока mock данные)

    TODO: Заменить на реальные данные из database
    """
    # Mock данные для тестирования
    return [
        {
            "id": 1,
            "title": "Биткоин выше $100,000 до конца февраля 2026?",
            "description": "Достигнет ли BTC цены $100k или выше до 28 февраля 2026 23:59 UTC?",
            "deadline": (datetime.now() + timedelta(days=27)).isoformat(),
            "resolved": False,
            "yes_price": 0.65,
            "no_price": 0.35,
            "volume": 125000,  # в рублях
            "category": "crypto",
        },
        {
            "id": 2,
            "title": "Спартак выиграет следующий матч РПЛ?",
            "description": "Победит ли Спартак Москва в следующем матче чемпионата России?",
            "deadline": (datetime.now() + timedelta(days=14)).isoformat(),
            "resolved": False,
            "yes_price": 0.58,
            "no_price": 0.42,
            "volume": 45000,
            "category": "sports",
        },
        {
            "id": 3,
            "title": "Температура в Москве выше +5°C 15 февраля?",
            "description": "Будет ли максимальная дневная температура в Москве выше +5°C 15 февраля 2026?",
            "deadline": (datetime.now() + timedelta(days=14)).isoformat(),
            "resolved": False,
            "yes_price": 0.42,
            "no_price": 0.58,
            "volume": 18000,
            "category": "weather",
        },
    ]


# Запуск приложения:
# uvicorn app.main:app --reload
#
# Тестирование:
# curl http://localhost:8000/
# curl http://localhost:8000/markets
