from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import redis.asyncio as redis
import json
import logging
import time
import traceback

from prometheus_fastapi_instrumentator import Instrumentator

from app.websocket import manager
from app import crud, models, schemas
from app.database import async_session, init_db
from app.tasks import send_email
from app.middleware.rate_limiter import RateLimiterMiddleware

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
        app.state.redis = redis.Redis(host="redis", port=6379, decode_responses=True)
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
        200: {
            "description": "Успешный ответ со списком заметок",
        },
        500: {
            "description": "Внутренняя ошибка сервера"
        }
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


@app.post("/notes", response_model=schemas.NoteOut)
async def add_note(note: schemas.NoteCreate, session: AsyncSession = Depends(async_session)):
    new_note = await crud.create_note(session, note)
    await app.state.redis.delete("notes_cache")
    return new_note

@app.get("/send-email/")
async def trigger_email(email: str):
    task = send_email.delay(email)
    return {"message": f"Задача на отправку письма на {email} отправлена в очередь", "task_id": task.id}

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

@app.get("/test", response_class=HTMLResponse)
async def websocket_test_page():
    html_content = """ ... (оставь HTML без изменений) ... """
    return HTMLResponse(content=html_content)
