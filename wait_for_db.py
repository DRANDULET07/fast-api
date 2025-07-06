import time
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = "db"

while True:
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
        print("⏳ Waiting for database...")
        time.sleep(1)
