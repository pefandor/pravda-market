# CI/CD Workflows

Этот проект использует GitHub Actions для автоматической проверки кода и тестирования.

## Workflows

### 1. Tests (`tests.yml`)

Запускается при каждом push или pull request в ветки `master`, `main`, `develop`.

**Этапы:**
- **Backend Tests**: Запускает все unit и integration тесты Python
- **Frontend Tests**: Запускает все unit и component тесты Vitest
- **Smoke Tests**: Выполняет E2E тесты критических путей (только после успешных unit tests)

**Coverage:** Результаты покрытия автоматически загружаются в Codecov (требуется настройка токена).

### 2. Lint (`lint.yml`)

Проверка качества кода перед merge.

**Backend:**
- Ruff linter (быстрая проверка стиля Python)
- Ruff formatter (проверка форматирования)

**Frontend:**
- ESLint (проверка TypeScript/React кода)
- TypeScript type checking

## Настройка

### Codecov (опционально)

Для автоматической загрузки coverage reports:

1. Зарегистрируйтесь на [codecov.io](https://codecov.io)
2. Подключите репозиторий
3. Добавьте `CODECOV_TOKEN` в GitHub Secrets:
   - Settings → Secrets and variables → Actions → New repository secret
   - Name: `CODECOV_TOKEN`
   - Value: (токен из Codecov)

### Локальный запуск

**Backend tests:**
```bash
cd backend
pytest -v --cov=app
```

**Frontend tests:**
```bash
cd frontend
npm test -- --run --coverage
```

**Smoke tests:**
```bash
cd backend
pytest -m smoke -v
```

**Linting:**
```bash
# Backend
cd backend
ruff check app tests
ruff format app tests

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
```

## Статус тестов

Текущая статистика:
- ✅ Backend: 82/82 tests passing (100%)
- ✅ Frontend: 83/83 tests passing (100%)
- ✅ Total: 165/165 tests passing (100%)

## Badge

Добавьте в README.md для отображения статуса:

```markdown
![Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Tests/badge.svg)
![Lint](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Lint/badge.svg)
```
