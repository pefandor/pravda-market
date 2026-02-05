# Используем официальный Python образ (совпадает с CI — tests.yml, lint.yml)
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements для production
COPY backend/requirements.prod.txt requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY backend/ .

# Создаём непривилегированного пользователя
RUN useradd --create-home --no-log-init appuser
USER appuser

# Открываем порт (Railway автоматически определит)
EXPOSE 8000

# Запуск: сначала миграции, потом приложение
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
