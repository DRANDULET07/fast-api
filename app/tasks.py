from celery import Celery
import time

celery_app = Celery(
    "app.tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

@celery_app.task
def send_email(email: str):
    print(f"📨 Отправка письма на {email}...")
    time.sleep(5)
    print(f"✅ Письмо успешно отправлено на {email}")
    return {"status": "отправлено", "email": email}
