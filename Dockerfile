FROM python:3.11-slim

WORKDIR /app

COPY ./app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app/ .  # Копирует все исходники в /app
COPY wait_for_db.py ./wait_for_db.py

# Убедись, что $PORT есть в Render и используй его:
CMD ["sh", "-c", "python wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
