FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt из корня, а не из ./app/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app/ .
COPY wait_for_db.py ./wait_for_db.py

# Используем переменную PORT от Render
CMD ["sh", "-c", "python wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
