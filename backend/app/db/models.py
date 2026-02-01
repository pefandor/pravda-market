"""
SQLAlchemy Models для Pravda Market

Базовые модели для MVP:
- User: пользователи из Telegram
- Market: prediction markets
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """
    Пользователь Telegram

    Минимальная версия без balance column
    (по production плану - balance через ledger, но для MVP упрощаем)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, first_name='{self.first_name}')>"


class Market(Base):
    """
    Prediction Market

    Рынок для прогнозирования событий
    """
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)

    # Дедлайн события
    deadline = Column(DateTime, nullable=False)

    # Резолюция
    resolved = Column(Boolean, default=False, index=True)
    resolution_value = Column(Boolean, nullable=True)  # True=YES, False=NO, None=не резолвнут

    # Временные поля для цен (в production это будет вычисляться из orderbook)
    # Для MVP - просто храним здесь
    yes_price = Column(Integer, default=5000)  # в basis points (5000 = 50%)
    no_price = Column(Integer, default=5000)   # в basis points

    # Volume (для статистики)
    volume = Column(Integer, default=0)  # в копейках

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Market(id={self.id}, title='{self.title[:50]}...', resolved={self.resolved})>"

    @property
    def yes_price_decimal(self):
        """Цена YES в десятичном формате (0.0 - 1.0)"""
        return self.yes_price / 10000

    @property
    def no_price_decimal(self):
        """Цена NO в десятичном формате (0.0 - 1.0)"""
        return self.no_price / 10000

    @property
    def volume_rubles(self):
        """Volume в рублях"""
        return self.volume / 100


# В будущем добавим:
# - Order (ордера)
# - Trade (исполненные сделки)
# - Ledger (балансы)
# - PaymentRequest (платежи)
# - OrderEvent (audit trail)
