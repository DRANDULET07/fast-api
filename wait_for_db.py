import time
import psycopg2
from psycopg2 import OperationalError
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("PSYCOPG2_DATABASE_URL")  # Новый URL только для psycopg2

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
