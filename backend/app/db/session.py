"""
Database Session Management

Настройка SQLAlchemy для работы с SQLite или PostgreSQL
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from app.core.logging_config import get_logger

# Load environment variables
load_dotenv()

logger = get_logger()

# Get database URL from environment or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pravda_market.db")

# Determine if using SQLite
is_sqlite = DATABASE_URL.startswith("sqlite")

# Create engine with appropriate settings
if is_sqlite:
    # SQLite-specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    logger.info(f"Using SQLite database: {DATABASE_URL}")
else:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False
    )
    logger.info("Using PostgreSQL database")

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
