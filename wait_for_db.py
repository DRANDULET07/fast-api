import time
import psycopg2
from psycopg2 import OperationalError
import os

# Получаем URL напрямую из переменной окружения (без load_dotenv)
DATABASE_URL = os.environ.get("PSYCOPG2_DATABASE_URL")

MAX_RETRIES = 30
retries = 0

while retries < MAX_RETRIES:
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        print("✅ Database is ready!")
        break
    except OperationalError:
        print(f"⏳ Waiting for database... Attempt {retries + 1}/{MAX_RETRIES}")
        retries += 1
        time.sleep(1)
else:
    print("❌ Database is not available. Exiting.")
    exit(1)
