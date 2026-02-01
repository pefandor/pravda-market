# 🎯 Правда Маркет

> Платформа коллективных прогнозов для российского рынка
> Telegram Mini App + FastAPI Backend

## 📋 Описание

**Правда Маркет** - социальная платформа прогнозирования событий (prediction market), адаптированная под российский рынок.

### Ключевые особенности:

- ✅ 30-секундный onboarding через Telegram
- ✅ Рубли + СБП/МИР (без крипто фрикции)
- ✅ TON интеграция для крипто аудитории
- ✅ Локальный контент (РПЛ, КХЛ, российская политика)
- ✅ Production-grade архитектура

## 🏗️ Технологический стек

### Frontend (Telegram Mini App)
- **Framework:** React 18 + Vite
- **UI:** Telegram UI Kit (@telegram-apps/telegram-ui)
- **SDK:** @twa-dev/sdk
- **State:** Zustand
- **Charts:** Lightweight Charts

### Backend
- **Framework:** Python FastAPI
- **Bot:** aiogram 3 (Telegram Bot API)
- **Database:** PostgreSQL + SQLAlchemy
- **Cache:** Redis
- **Auth:** Telegram initData validation

### Infrastructure
- **Frontend Hosting:** Cloudflare Pages
- **Backend Hosting:** Railway / Render
- **Database:** Supabase / Neon
- **Monitoring:** Prometheus + Grafana + Sentry

## 📁 Структура проекта

```
pravda-market/
├── frontend/           # Telegram Mini App (React)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── store/
│   └── package.json
│
├── backend/            # FastAPI Server
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── services/
│   │   └── bot/
│   └── requirements.txt
│
├── docs/              # Документация
└── PLAN.md           # Детальный план разработки
```

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp .env.example .env
# Отредактировать .env с вашими credentials

# Инициализировать базу данных
python -c "from app.db.session import init_db; from app.core.logging_config import setup_logging; setup_logging(); init_db()"

# Seed тестовый баланс (опционально)
python -m app.db.seed

# Запустить сервер
uvicorn app.main:app --reload
```

#### Database Configuration

**SQLite (Development - по умолчанию):**
```bash
DATABASE_URL=sqlite:///./pravda_market.db
```

**PostgreSQL (Production/Testing):**
```bash
# Install PostgreSQL: https://www.postgresql.org/download/
createdb pravda_market
DATABASE_URL=postgresql://username:password@localhost:5432/pravda_market
```

### Frontend Setup

```bash
cd frontend

# Установить зависимости
npm install

# Запустить dev server
npm run dev
```

## 📊 Database Schema

Production-ready схема с:
- ✅ Ledger-based balance management
- ✅ Integer-based prices (basis points)
- ✅ Партиционирование по месяцам
- ✅ Оптимизированные индексы

Детали в [PLAN.md](./PLAN.md#database-schema)

## 🔐 Security

- ✅ Telegram initData validation (HMAC-SHA256)
- ✅ Rate limiting
- ✅ Input validation (Pydantic)
- ✅ CSRF protection
- ✅ Idempotency keys для payments

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest --cov=app --cov-report=html

# Load testing
locust -f tests/load/locustfile.py
```

**Coverage targets:**
- Overall: 80%+
- Matching Engine: 95%+
- Ledger: 95%+

## 📈 Roadmap

**Текущий статус:** 🚧 В разработке

### Week 1: Foundation
- [x] Project setup
- [ ] Database schema
- [ ] Order matching engine

### Week 2: API & Real-time
- [ ] REST API endpoints
- [ ] WebSocket implementation
- [ ] Payment integration

### Week 3: Polish & Testing
- [ ] Comprehensive testing
- [ ] Monitoring setup
- [ ] Security audit

### Week 4: Launch
- [ ] Beta testing
- [ ] Soft launch
- [ ] Iteration

Детальный roadmap: [PLAN.md](./PLAN.md#roadmap)

## 📚 Документация

- [PLAN.md](./PLAN.md) - Детальный технический план (3294 строки)
- [API Documentation](./docs/API.md) - API endpoints (TODO)
- [Architecture](./docs/ARCHITECTURE.md) - Архитектурные решения (TODO)

## 🤝 Contributing

TBD

## 📞 Контакты

TBD

## 📄 License

TBD

---

**Версия:** 0.1.0-alpha
**Последнее обновление:** 2026-02-01
