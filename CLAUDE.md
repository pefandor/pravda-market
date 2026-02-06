# Pravda Market — Prediction Market на TON

## Обзор проекта

Telegram Mini App для ставок на исходы событий (аналог Polymarket для СНГ).
Пользователи покупают YES/NO позиции, платформа берёт 2% комиссии с выигрыша.

## Текущий статус: MVP ГОТОВ ✅

- ✅ Backend задеплоен на Railway
- ✅ Frontend задеплоен на Railway  
- ✅ Mini App работает в Telegram
- ✅ Escrow смарт-контракт задеплоен в testnet
- ⏳ Интеграция контракта с backend (в процессе)

---

## Архитектура

```
Telegram Mini App
       ↓
Frontend (React + Vite)
       ↓
Backend (FastAPI + PostgreSQL)
       ↓
TON Blockchain (Escrow Contract)
```

---

## Деплой

### Backend
- **URL:** https://pravda-market-production.up.railway.app
- **Платформа:** Railway
- **База:** PostgreSQL (Railway addon)

### Frontend  
- **URL:** https://adventurous-grace-production-88ef.up.railway.app
- **Платформа:** Railway
- **Builder:** Dockerfile (nginx)

### Telegram Bot
- **Username:** @RPFtru_bot
- **Mini App URL:** настроен в BotFather

---

## TON Smart Contract (Escrow)

### Статус: Testnet ✅

### Адреса
- **Contract:** `kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy`
- **Operator:** `kQAy-j1ayr7xj42pSE4e_D1TLskQW2vnTElSUkInkRYxvI2d`
- **Explorer:** https://testnet.tonscan.org/address/kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy

### Конфигурация
- Daily Limit: 10,000 TON
- Emergency Delay: 7 days
- Тесты: 24/24 passed

### Функции контракта
- `deposit` (0x01) — депозит с memo (telegram_id)
- `operator_withdraw` (0x02) — batch вывод оператором
- `request_emergency` (0x03) — запуск 7-дневного таймера
- `execute_emergency` (0x04) — вывод после 7 дней
- `pause/unpause` (0x10/0x11) — остановка контракта (multisig)

### Тестовый кошелёк
```
Адрес: kQAy-j1ayr7xj42pSE4e_D1TLskQW2vnTElSUkInkRYxvI2d
Мнемоника: pink clip giggle loan lake salmon cloth spike spread eye super often visual that observe affair pretty arrive festival finish primary swear year real
```

---

## Структура проекта

```
pravda-market/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   │   ├── admin.py     # Админка: markets, deposits, withdrawals
│   │   │   ├── bets.py      # Ставки, ордера
│   │   │   ├── withdrawals.py # Заявки на вывод
│   │   │   └── users.py     # Профиль, баланс
│   │   ├── db/
│   │   │   ├── models.py    # SQLAlchemy модели
│   │   │   └── session.py   # DB connection
│   │   ├── services/
│   │   │   ├── matching.py  # Matching engine
│   │   │   └── settlement.py # Резолюция + 2% комиссия
│   │   └── main.py
│   ├── alembic/             # Миграции
│   └── tests/               # 82 теста
│
├── frontend/
│   ├── src/
│   │   ├── pages/           # Страницы (Markets, Portfolio, Profile, Admin)
│   │   ├── components/      # UI компоненты
│   │   └── services/        # API клиент
│   └── tests/               # 83 теста
│
├── contracts/
│   ├── sources/
│   │   └── escrow.fc        # FunC контракт (478 строк)
│   ├── wrappers/
│   │   └── Escrow.ts        # TypeScript wrapper
│   ├── tests/
│   │   └── Escrow.spec.ts   # 24 теста
│   └── scripts/
│       ├── deploy-testnet.ts
│       └── batchWithdraw.ts # Скрипт batch вывода для оператора
│
└── .claude/
    └── commands/            # Slash-команды
        ├── check.md         # /check — диагностика
        ├── fix.md           # /fix — исправление
        ├── security.md      # /security — аудит
        └── deploy-check.md  # /deploy-check — чеклист
```

---

## Ключевые команды

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload          # Запуск
pytest                                   # Тесты (82)
alembic upgrade head                     # Миграции
```

### Frontend
```bash
cd frontend
npm install
npm run dev                              # Запуск
npm run test                             # Тесты (83)
npm run build                            # Сборка
```

### Contracts
```bash
cd contracts
npm install
npm run build                            # Компиляция FunC
npm run test                             # Тесты (24)
```

---

## Переменные окружения

### Backend (Railway)
```
DATABASE_URL=postgresql://...
TELEGRAM_BOT_TOKEN=<от BotFather>
ADMIN_TOKEN=<случайная строка>
ENVIRONMENT=production
ALLOWED_ORIGINS=https://adventurous-grace-production-88ef.up.railway.app
```

### Frontend (Railway)
```
VITE_API_URL=https://pravda-market-production.up.railway.app
```

---

## Бизнес-логика

### Комиссия
- 2% с выигрыша (в settlement.py)
- Записывается в ledger как type="platform_fee"

### Баланс
- Автоначисление 1000₽ при регистрации (для тестов)
- Всё в копейках (amount_kopecks)
- После интеграции TON — будет в nanoTON

### Резолюция
- Админ вызывает POST /admin/markets/{id}/resolve
- Body: {"outcome": "yes"} или {"outcome": "no"}
- Settlement автоматически распределяет выигрыши

### Вывод средств (Withdrawals)

#### Лимиты
- Минимум: 1 TON
- Комиссия: 0.05 TON
- Дневной лимит: 1000 TON на пользователя

#### API endpoints (пользователь)
- `POST /withdrawals` — создать заявку на вывод
- `GET /withdrawals` — список своих заявок
- `DELETE /withdrawals/{id}` — отменить pending заявку

#### API endpoints (админ)
- `GET /admin/withdrawals/pending` — заявки для обработки
- `POST /admin/withdrawals/process` — пометить как processing
- `POST /admin/withdrawals/complete` — завершить (с tx_hash)
- `POST /admin/withdrawals/fail` — ошибка (возврат средств)

#### Batch Withdrawal Script (Оператор)
```bash
cd contracts

# Тестовый запуск (без отправки транзакции)
OPERATOR_MNEMONIC="..." \
BACKEND_URL="https://pravda-market-production.up.railway.app" \
ADMIN_TOKEN="..." \
DRY_RUN=true \
npx ts-node scripts/batchWithdraw.ts

# Реальный запуск
OPERATOR_MNEMONIC="pink clip giggle..." \
BACKEND_URL="https://pravda-market-production.up.railway.app" \
ADMIN_TOKEN="<admin_token>" \
npx ts-node scripts/batchWithdraw.ts
```

**Переменные окружения:**
- `OPERATOR_MNEMONIC` — 24-word мнемоника оператора (обязательно)
- `BACKEND_URL` — URL бекенда (по умолчанию: localhost:8000)
- `ADMIN_TOKEN` — токен авторизации админа (обязательно)
- `MAX_BATCH_SIZE` — максимум заявок в батче (по умолчанию: 50)
- `DRY_RUN` — true для симуляции без отправки

**Что делает скрипт:**
1. Получает pending заявки из бекенда
2. Проверяет состояние контракта (пауза, дневной лимит)
3. Помечает заявки как processing
4. Отправляет batch транзакцию в контракт (opcode 0x02)
5. Помечает заявки как completed с tx_hash
6. При ошибке — помечает как failed, баланс возвращается

---

## Безопасность (исправлено)

- ✅ Race conditions — FOR UPDATE на balance и orders
- ✅ Self-trading запрещён
- ✅ Deadline проверяется при ставке
- ✅ CORS ограничен
- ✅ Security headers добавлены
- ✅ Docker non-root
- ✅ Swagger скрыт в production

---

## Следующие шаги

1. **Интеграция TON с backend:**
   - TonCenter indexer для отслеживания депозитов
   - Webhook при получении депозита
   - Автоматическое зачисление баланса

2. ~~**UI для депозитов:**~~ ✅
   - ~~Кнопка "Пополнить" → генерация TON транзакции~~

3. ~~**Вывод средств:**~~ ✅
   - ~~Endpoint POST /withdraw~~
   - ~~Batch withdrawals через контракт~~

4. **Mainnet:**
   - Security audit контракта
   - Новые ключи (не тестовые!)
   - Деплой в mainnet

---

## Полезные ссылки

- **Testnet Explorer:** https://testnet.tonscan.org/
- **TON Docs:** https://docs.ton.org/
- **Blueprint:** https://github.com/ton-org/blueprint
- **Railway:** https://railway.app/

---

## Slash-команды Claude Code

- `/check` — полная диагностика проекта
- `/fix <описание>` — исправление с планом
- `/security` — аудит безопасности
- `/status` — быстрый обзор
- `/deploy-check` — чеклист перед деплоем
