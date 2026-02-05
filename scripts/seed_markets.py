#!/usr/bin/env python3
"""
Seed Markets Script for Production

Creates test markets on Pravda Market production server.

Usage:
    python scripts/seed_markets.py --url URL --token TOKEN

    # Or with environment variables:
    export API_URL=https://pravda-market-production.up.railway.app
    export ADMIN_TOKEN=your_token
    python scripts/seed_markets.py

Example:
    python scripts/seed_markets.py \
        --url https://pravda-market-production.up.railway.app \
        --token abc123
"""

import argparse
import os
import sys
import requests
from datetime import datetime
from typing import Optional


# Market definitions
MARKETS = [
    # Crypto
    {
        "title": "Bitcoin достигнет $150,000 до июля 2026?",
        "description": (
            "Цена BTC достигнет или превысит $150,000 USD на любой из топ-5 бирж "
            "(Binance, Coinbase, Kraken, OKX, Bybit) до 1 июля 2026 00:00 UTC. "
            "Резолюция: данные CoinGecko или CoinMarketCap."
        ),
        "category": "crypto",
        "deadline": "2026-07-01T00:00:00Z",
        "yes_price": 0.35,
    },
    {
        "title": "TON войдёт в топ-10 по капитализации до конца 2026?",
        "description": (
            "Криптовалюта TON (Toncoin) войдёт в топ-10 криптовалют по рыночной "
            "капитализации (по данным CoinMarketCap) хотя бы на 1 день до 31 декабря 2026. "
            "Стейблкоины и wrapped токены не учитываются."
        ),
        "category": "crypto",
        "deadline": "2026-12-31T23:59:00Z",
        "yes_price": 0.45,
    },

    # Economy
    {
        "title": "Курс доллара превысит 120 рублей до конца 2026?",
        "description": (
            "Официальный курс USD/RUB ЦБ РФ достигнет или превысит 120.00 рублей "
            "хотя бы на один день до 31 декабря 2026. "
            "Резолюция: данные cbr.ru."
        ),
        "category": "economy",
        "deadline": "2026-12-31T23:59:00Z",
        "yes_price": 0.55,
    },
    {
        "title": "ЦБ снизит ключевую ставку до 15% к лету 2026?",
        "description": (
            "Банк России снизит ключевую ставку до 15% или ниже к 1 июня 2026. "
            "Учитывается официальное решение совета директоров ЦБ РФ. "
            "Резолюция: пресс-релизы cbr.ru."
        ),
        "category": "economy",
        "deadline": "2026-06-01T00:00:00Z",
        "yes_price": 0.40,
    },

    # Tech & Games
    {
        "title": "GTA 6 выйдет до октября 2026?",
        "description": (
            "Grand Theft Auto VI будет официально выпущена (релиз) для любой платформы "
            "(PS5, Xbox, PC) до 1 октября 2026. "
            "Ранний доступ и бета-версии не считаются. "
            "Резолюция: официальный анонс Rockstar Games."
        ),
        "category": "tech",
        "deadline": "2026-10-01T00:00:00Z",
        "yes_price": 0.70,
    },
    {
        "title": "Telegram достигнет 1 млрд MAU до 2027?",
        "description": (
            "Telegram официально объявит о достижении 1 миллиарда ежемесячных "
            "активных пользователей (MAU) до 1 января 2027. "
            "Резолюция: официальные заявления Telegram или Павла Дурова."
        ),
        "category": "tech",
        "deadline": "2027-01-01T00:00:00Z",
        "yes_price": 0.60,
    },
    {
        "title": "Apple выпустит складной iPhone в 2026?",
        "description": (
            "Apple официально анонсирует и начнёт продажи iPhone со складным экраном "
            "(foldable) в 2026 году. "
            "Резолюция: официальный анонс Apple, продажи должны начаться до 31.12.2026."
        ),
        "category": "tech",
        "deadline": "2026-12-31T23:59:00Z",
        "yes_price": 0.25,
    },
]


def create_market(api_url: str, token: str, market: dict) -> Optional[dict]:
    """Create a single market via API"""
    url = f"{api_url.rstrip('/')}/admin/markets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=market, headers=headers, timeout=30)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print(f"  [ERROR] Access denied - check ADMIN_TOKEN")
            return None
        else:
            print(f"  [ERROR] {response.status_code}: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Cannot connect to {api_url}")
        return None
    except requests.exceptions.Timeout:
        print(f"  [ERROR] Request timeout")
        return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def check_existing_markets(api_url: str, token: str) -> Optional[list]:
    """Get list of existing markets"""
    url = f"{api_url.rstrip('/')}/admin/markets"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Seed markets to Pravda Market API")
    parser.add_argument("--url", help="API base URL", default=os.environ.get("API_URL"))
    parser.add_argument("--token", help="Admin token", default=os.environ.get("ADMIN_TOKEN"))
    parser.add_argument("--dry-run", action="store_true", help="Show markets without creating")
    parser.add_argument("--force", action="store_true", help="Create even if markets exist")
    args = parser.parse_args()

    if not args.url:
        print("[ERROR] API_URL required. Use --url or set API_URL env var")
        sys.exit(1)

    if not args.token and not args.dry_run:
        print("[ERROR] ADMIN_TOKEN required. Use --token or set ADMIN_TOKEN env var")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Pravda Market - Seed Script")
    print(f"{'='*60}")
    print(f"  API URL: {args.url}")
    print(f"  Markets to create: {len(MARKETS)}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("Markets that would be created:\n")
        for i, market in enumerate(MARKETS, 1):
            print(f"  {i}. {market['title']}")
            print(f"     Category: {market['category']}")
            print(f"     YES price: {market['yes_price']:.0%}")
            print(f"     Deadline: {market['deadline']}")
            print()
        print("[DRY RUN] No markets created.")
        return

    # Check existing markets
    if not args.force:
        existing = check_existing_markets(args.url, args.token)
        if existing and len(existing) > 0:
            print(f"[WARN] Found {len(existing)} existing markets:")
            for m in existing[:5]:
                print(f"  - {m['title'][:50]}...")
            if len(existing) > 5:
                print(f"  ... and {len(existing) - 5} more")
            print("\nUse --force to add markets anyway.")
            print("Aborting.")
            sys.exit(0)

    # Create markets
    created = 0
    failed = 0

    for i, market in enumerate(MARKETS, 1):
        print(f"[{i}/{len(MARKETS)}] Creating: {market['title'][:50]}...")
        result = create_market(args.url, args.token, market)

        if result:
            print(f"  [OK] ID={result['id']}, YES={result['yes_price']:.0%}")
            created += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"  DONE!")
    print(f"  Created: {created}")
    print(f"  Failed: {failed}")
    print(f"{'='*60}\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
