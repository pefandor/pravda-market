"""
Seed Script - Заполнение тестовых данных

Создает database и добавляет тестовые рынки
"""

from app.db.session import init_db, SessionLocal
from app.db.models import User, Market
from datetime import datetime, timedelta


def seed_data():
    """Создать тестовые данные"""

    # Инициализировать database
    init_db()

    # Создать session
    db = SessionLocal()

    try:
        # Проверить: уже есть данные?
        existing_markets = db.query(Market).count()
        if existing_markets > 0:
            print(f"[WARN]  Database already has {existing_markets} markets")
            print("   Run with --force to recreate")
            return

        # Создать тестовые рынки
        markets = [
            Market(
                title="Биткоин выше $100,000 до конца февраля 2026?",
                description="Достигнет ли BTC цены $100,000 или выше до 28 февраля 2026 23:59 UTC?",
                category="crypto",
                deadline=datetime.now() + timedelta(days=27),
                yes_price=6500,  # 65%
                no_price=3500,   # 35%
                volume=12500000,  # 125,000RUB в копейках
            ),
            Market(
                title="Спартак выиграет следующий матч РПЛ?",
                description="Победит ли Спартак Москва в следующем матче чемпионата России?",
                category="sports",
                deadline=datetime.now() + timedelta(days=14),
                yes_price=5800,  # 58%
                no_price=4200,   # 42%
                volume=4500000,  # 45,000RUB
            ),
            Market(
                title="Температура в Москве выше +5°C 15 февраля?",
                description="Будет ли максимальная дневная температура в Москве выше +5°C 15 февраля 2026?",
                category="weather",
                deadline=datetime.now() + timedelta(days=14),
                yes_price=4200,  # 42%
                no_price=5800,   # 58%
                volume=1800000,  # 18,000RUB
            ),
            Market(
                title="Ethereum достигнет $5,000 в марте 2026?",
                description="Достигнет ли ETH цены $5,000 или выше в течение марта 2026?",
                category="crypto",
                deadline=datetime.now() + timedelta(days=58),
                yes_price=5500,
                no_price=4500,
                volume=8200000,
            ),
            Market(
                title="ЦСКА займет топ-3 в РПЛ этого сезона?",
                description="Финиширует ли ЦСКА в топ-3 чемпионата России 2025/26?",
                category="sports",
                deadline=datetime.now() + timedelta(days=120),
                yes_price=7200,
                no_price=2800,
                volume=3100000,
            ),
        ]

        # Добавить в database
        for market in markets:
            db.add(market)

        db.commit()

        print(f"[OK] Created {len(markets)} test markets")
        print("\nMarkets:")
        for market in markets:
            print(f"  - {market.title}")
            print(f"    YES: {market.yes_price_decimal:.1%}, Volume: {market.volume_rubles:,.0f}RUB")

        print(f"\n[OK] Seed complete!")
        print(f"  Database: pravda_market.db")
        print(f"  Markets: {len(markets)}")

    except Exception as e:
        print(f"[ERROR] Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    # Check for --force flag
    force = "--force" in sys.argv

    if force:
        from app.db.session import drop_db
        drop_db()

    seed_data()
