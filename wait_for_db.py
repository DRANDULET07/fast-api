import time
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import os

load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")

MAX_RETRIES = 30
retries = 0

while retries < MAX_RETRIES:
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
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
