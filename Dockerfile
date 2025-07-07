FROM python:3.11-slim

# Установка зависимостей для psycopg2 и других пакетов
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./app/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app/ .  # копируем все файлы из папки app

COPY wait_for_db.py ./wait_for_db.py

# Запускаем сервер (без app. в пути к модулю)
CMD ["sh", "-c", "python wait_for_db.py && uvicorn main:app --host 0.0.0.0 --port $PORT"]
