"""
Database Seed Script

Создание начального баланса для пользователей
"""

from app.db.session import SessionLocal
from app.db.models import User, LedgerEntry
from app.core.logging_config import get_logger

logger = get_logger()


def seed_initial_balance():
    """
    Дать всем пользователям 1000₽ для тестирования

    Idempotent: проверяет существование deposit записей
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()

        if not users:
            logger.warning("No users found to seed balance")
            return

        seeded_count = 0
        for user in users:
            # Check if already has balance
            existing = db.query(LedgerEntry).filter(
                LedgerEntry.user_id == user.id,
                LedgerEntry.type == 'deposit'
            ).first()

            if not existing:
                entry = LedgerEntry(
                    user_id=user.id,
                    amount_kopecks=100000,  # 1000₽
                    type='deposit'
                )
                db.add(entry)
                seeded_count += 1
                logger.info(f"Seeded 1000₽ to user {user.telegram_id}")

        db.commit()
        logger.info(f"Balance seeding completed. Seeded {seeded_count} users")

    except Exception as e:
        db.rollback()
        logger.error(f"Seed script failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Setup logging для standalone execution
    from app.core.logging_config import setup_logging
    setup_logging(level="INFO")

    logger.info("Starting balance seed script...")
    seed_initial_balance()
    logger.info("Seed script completed")
