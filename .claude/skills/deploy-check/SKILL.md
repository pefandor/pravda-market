---
description: Предварительная проверка перед деплоем. Проверяет что всё готово к продакшену. Использовать ПЕРЕД каждым деплоем.
allowed-tools: Read, Grep, Glob, Bash(cd:*), Bash(python:*), Bash(npx:*), Bash(cat:*), Bash(docker:*), Bash(git:*)
---

# Чеклист перед деплоем Pravda Market

ultrathink

## Обязательные проверки

### ✅ Тесты
- [ ] Backend тесты проходят: `cd backend && python -m pytest`
- [ ] Frontend тесты проходят: `cd frontend && npx vitest run`
- [ ] Нет skipped тестов без причины

### ✅ Секреты
- [ ] `.env` файлы НЕ в git: `git status` не показывает `.env`
- [ ] Нет хардкод-секретов в коде: `grep -r "token\|password\|secret" --include="*.py" --include="*.ts" --include="*.tsx" backend/app/ frontend/src/`
- [ ] Все env переменные документированы и задеплоены на Railway

### ✅ Конфигурация
- [ ] `CORS_ORIGINS` — конкретный домен, не `"*"`
- [ ] `ENVIRONMENT=production` задан
- [ ] `base: '/'` в `vite.config.ts` (не `/reactjs-template/`)
- [ ] `VITE_API_URL` указывает на продакшен бэкенд
- [ ] Frontend build работает без ошибок: `cd frontend && npm run build`

### ✅ База данных
- [ ] `DATABASE_URL` указывает на PostgreSQL (не SQLite)
- [ ] Миграции актуальны: `cd backend && alembic upgrade head`
- [ ] Нет pending миграций

### ✅ Docker
- [ ] `Dockerfile` имеет `USER` directive (не root)
- [ ] Python версия в Docker совпадает с CI
- [ ] Docker build проходит: `docker build -t pravda-market .`

### ✅ CI/CD
- [ ] Deploy зависит от тестов (needs: [test])
- [ ] Lint реально блокирует при ошибках (не continue-on-error)
- [ ] Миграции запускаются автоматически при деплое

### ✅ Безопасность
- [ ] Rate limiting настроен
- [ ] Error messages не утекают internals
- [ ] Admin endpoints защищены

## Формат ответа

Для каждого пункта:
- ✅ — всё ок
- ❌ — проблема (описать и показать как починить)
- ⚠️ — не критично, но стоит обратить внимание

В конце: **ВЕРДИКТ — деплоить можно / нельзя** с обоснованием.
