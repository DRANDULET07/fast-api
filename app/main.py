from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import redis.asyncio as redis
import json
import logging
import time
import traceback
import os

from prometheus_fastapi_instrumentator import Instrumentator

from app.websocket import manager
from app import crud, models, schemas
from app.database import async_session, init_db
from app.tasks import send_email
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.config import settings  # ⬅️ добавлено

app = FastAPI(
    title="📓 Сервис Заметок",
    description="FastAPI-приложение для создания, хранения и отображения заметок с использованием Redis, Celery, Prometheus и ограничения по частоте запросов.",
    version="1.0.0"
)

# Middleware для ограничения частоты запросов
app.add_middleware(RateLimiterMiddleware)

# Prometheus метрики
instrumentator = Instrumentator().instrument(app).expose(app)

# JSON логгер
logger = logging.getLogger("uvicorn.access")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}')
handler.setFormatter(formatter)
logger.handlers = [handler]

# Middleware логирования
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(json.dumps({
            "error": str(e),
            "trace": traceback.format_exc()
        }))
        raise
    process_time = round(time.time() - start_time, 4)
    logger.info(json.dumps({
        "method": request.method,
        "url": request.url.path,
        "status_code": response.status_code,
        "duration": process_time
    }))
    return response

# Health Check
@app.get("/health")
async def health_check():
    try:
        redis_client = app.state.redis
        pong = await redis_client.ping()
        if pong:
            return {"status": "ok"}
        return JSONResponse(status_code=500, content={"status": "Redis unavailable"})
    except Exception as e:
        logger.error(json.dumps({
            "error": "Health check failed",
            "trace": traceback.format_exc()
        }))
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

@app.on_event("startup")
async def on_startup():
    await init_db()
    try:
        app.state.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await app.state.redis.ping()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.error(json.dumps({
            "error": "Failed to connect to Redis during startup",
            "trace": traceback.format_exc()
        }))
        raise

@app.get(
    "/notes",
    response_model=List[schemas.NoteOut],
    summary="Получить список заметок",
    description="Возвращает кэшированный или свежий список всех заметок из базы данных.",
    tags=["Заметки"],
    responses={
        200: {"description": "Успешный ответ со списком заметок"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def get_notes(session: AsyncSession = Depends(async_session)):
    redis_client = app.state.redis
    cache_key = "notes_cache"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    notes = await crud.get_notes(session)
    await redis_client.set(cache_key, json.dumps([note.model_dump() for note in notes]), ex=60)
    return notes

@app.post(
    "/notes",
    response_model=schemas.NoteOut,
    summary="Добавить новую заметку",
    tags=["Заметки"],
    responses={
        201: {"description": "Заметка успешно создана"},
        400: {"description": "Неверные данные"},
    }
)
async def add_note(note: schemas.NoteCreate, session: AsyncSession = Depends(async_session)):
    new_note = await crud.create_note(session, note)
    await app.state.redis.delete("notes_cache")
    return new_note

@app.get(
    "/send-email/",
    summary="Отправить email через Celery",
    description="Добавляет задачу отправки письма в очередь Celery",
    tags=["Почта"]
)
async def trigger_email(email: str):
    task = send_email.delay(email)
    return {
        "message": f"Задача на отправку письма на {email} отправлена в очередь",
        "task_id": task.id
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"📨 Сообщение: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("❌ Кто-то отключился")

@app.get("/test", response_class=HTMLResponse, include_in_schema=False)
async def websocket_test_page():
    html_content = """
    <html>
        <head>
            <title>WebSocket Чат</title>
        </head>
        <body>
            <h1>Простой WebSocket чат</h1>
            <input id="messageInput" type="text" placeholder="Введите сообщение..."/>
            <button onclick="sendMessage()">Отправить</button>
            <ul id="messages"></ul>
            <script>
                const ws = new WebSocket(`wss://${window.location.host}/ws`);
                ws.onmessage = (event) => {
                    const messages = document.getElementById('messages');
                    const message = document.createElement('li');
                    message.textContent = event.data;
                    messages.appendChild(message);
                };
                function sendMessage() {
                    const input = document.getElementById("messageInput");
                    ws.send(input.value);
                    input.value = '';
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ⬇️ Для Render: автоматический запуск через порт
import os

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

