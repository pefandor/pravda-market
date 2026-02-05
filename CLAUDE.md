# Pravda Market — Prediction Market (Polymarket clone)

## Архитектура

```
Telegram → Frontend (Mini App) → Backend API (FastAPI) → DB
              │                        │
              │ Auth: twa <initData>   │ HMAC-SHA256 validation
              │                        │ Auto-register user
              └── Services (api.ts) ───┘
```

**Backend:** Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, Alembic
**Frontend:** React 19, TypeScript 5.9, Vite 6.3
**Telegram SDK:** @tma.js/sdk-react 3.0, @telegram-apps/telegram-ui 2.1
**Blockchain:** @tonconnect/ui-react 2.2 (TON wallet)
**DB:** SQLite (dev) / PostgreSQL (prod)
**Deploy:** Docker → Railway, GitHub Actions CI/CD
**Testing:** pytest (backend, 82 tests), vitest (frontend, 83 tests)

## Структура проекта

```
RPF/
├── backend/             # FastAPI приложение
│   ├── app/
│   │   ├── main.py      # Эндпоинты: /markets, /bets, /bets/balance
│   │   ├── models.py    # SQLAlchemy модели
│   │   ├── config.py    # Settings (Pydantic)
│   │   ├── security.py  # HMAC-SHA256 auth
│   │   ├── admin.py     # /admin/markets/{id}/resolve
│   │   ├── bets.py      # Ордера, баланс, торговля
│   │   ├── ledger.py    # Транзакции
│   │   └── settlement.py # Резолюция маркетов
│   ├── alembic/         # Миграции БД
│   └── .env             # ⚠️ Секреты — НЕ коммитить
├── frontend/            # React + Vite
│   ├── src/
│   │   ├── api.ts       # API клиент (axios)
│   │   ├── App.tsx      # Роутинг
│   │   └── pages/       # Страницы
│   └── .env             # VITE_API_URL
├── telegram-mini-app/   # Telegram Mini App обёртка
│   ├── Dockerfile
│   ├── PLAN.md
│   └── openapi.json
├── .github/             # CI/CD workflows
└── docs/                # Документация
```

## Ключевые .env переменные

### Backend (backend/.env)
| Переменная | Обязательна | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен от @BotFather |
| `DATABASE_URL` | ✅ | SQLite (dev) / PostgreSQL (prod) |
| `ADMIN_TOKEN` | ✅ | Токен для admin endpoints |
| `ENVIRONMENT` | ❌ | development / production |
| `LOG_LEVEL` | ❌ | DEBUG, INFO, etc. |
| `CORS_ORIGINS` | ❌ | Prod: домен фронта |

### Frontend (frontend/.env)
| Переменная | Обязательна | Описание |
|---|---|---|
| `VITE_API_URL` | ✅ | URL бэкенда |

## Правила для Claude

### Безопасность (КРИТИЧНО)
- НИКОГДА не хардкодить токены, пароли, секреты в код
- НИКОГДА не использовать fallback-значения для секретов (типа `"admin_secret_token"`)
- Всегда проверять что `.env*` файлы в `.gitignore`
- CORS в проде — только конкретные домены, НИКОГДА `"*"`
- Все секретные переменные должны вызывать ошибку при отсутствии, а не подставлять дефолт

### Стиль кода — Backend
- Python 3.11+, type hints обязательны
- FastAPI + Pydantic для валидации
- SQLAlchemy 2.0 async style
- Alembic для миграций — без ручных `CREATE TABLE`
- Все datetime — timezone-aware (`datetime.now(timezone.utc)`)
- Ошибки БД ловить, НЕ отдавать `str(e)` в HTTP response
- `assert` не использовать для валидации — только `if/raise`

### Стиль кода — Frontend
- TypeScript strict mode
- React functional components + hooks
- Типы в `types/` директории
- `parseInt()` всегда с NaN guard
- Не использовать `any` — типизировать явно
- Мёртвый код удалять

### Git
- Коммиты на русском или английском, осмысленные
- Ветки: `feature/`, `fix/`, `hotfix/`
- Перед коммитом: lint + тесты

### Тестирование
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npx vitest run`
- Новый код = новые тесты

### Деплой
- Docker build из корня
- Railway для хостинга
- CI/CD: GitHub Actions (`.github/`)
- Миграции: `alembic upgrade head` ПЕРЕД стартом приложения

## Известные проблемы (из аудита)

### КРИТИЧНЫЕ — исправить немедленно
1. `.env` key mismatch: Config ожидает `TELEGRAM_BOT_TOKEN`, а в `.env` записан `BOT_TOKEN`
2. Hardcoded admin fallback `"admin_secret_token"` в `admin.py:56`
3. `telegram_id = Integer` — нужен `BigInteger` (переполнение)
4. Реальный бот-токен лежит в `backend/.env` на диске
5. `base: '/reactjs-template/'` в `vite.config.ts` — из шаблона, нужно `'/'`
6. Docker runs as root — нужен `USER` directive
7. `.gitignore` не ловит `.env.production`

### ВАЖНЫЕ — исправить до продакшена
- `datetime.fromtimestamp()` без timezone в `security.py`
- `CORS = "*"` по умолчанию в `config.py`
- Нет rate limit на тяжёлые SQL запросы
- Error messages утекают internals в `admin.py`
- Partial orders нельзя отменить — средства залочены
- `Market.volume = Integer` — переполнение при ~21.5M
- Python 3.11 в Docker vs 3.13 в CI
- Deploy без зависимости от тестов

## Команды

```bash
# Backend
cd backend && pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload
cd backend && pytest
cd backend && alembic upgrade head

# Frontend
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npx vitest run
cd frontend && npm run build

# Docker
docker build -t pravda-market .
docker run -p 8000:8000 pravda-market
```
