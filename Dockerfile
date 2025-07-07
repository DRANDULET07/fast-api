FROM python:3.11-slim

# Установка зависимостей для psycopg2 и других пакетов
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements.txt из папки app и устанавливаем зависимости
COPY ./app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё из папки app/ и корневой wait_for_db.py
COPY ./app/ ./app/
COPY wait_for_db.py ./wait_for_db.py

# Запуск: ждем БД, затем запускаем Uvicorn с app.main:app
CMD ["sh", "-c", "python wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
