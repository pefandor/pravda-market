"""
Database Session Management

Настройка SQLAlchemy для работы с SQLite
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from app.core.logging_config import get_logger

logger = get_logger()

# SQLite database file path
DATABASE_FILE = "pravda_market.db"
DATABASE_URL = f"sqlite:///./{DATABASE_FILE}"

# Create engine
# check_same_thread=False нужен для SQLite с FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # True для debug SQL queries
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency для FastAPI endpoints

    Usage:
        @app.get("/markets")
        async def get_markets(db: Session = Depends(get_db)):
            markets = db.query(Market).all()
            return markets
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Инициализация database

    Создает все таблицы из models
    """
    from app.db.models import Base

    logger.info("Creating database tables", extra={"database_url": DATABASE_URL})
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_db():
    """
    Удалить все таблицы (для тестов)
    """
    from app.db.models import Base

    logger.warning("Dropping all database tables")
    Base.metadata.drop_all(bind=engine)
    logger.info("All database tables dropped")


# Для удобства
__all__ = ["engine", "SessionLocal", "get_db", "init_db", "drop_db"]
