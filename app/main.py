from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import redis.asyncio as redis  # ✅ Новая версия Redis

from app.websocket import manager
from app import crud, models, schemas
from app.database import async_session, init_db
from app.tasks import send_email
import json

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await init_db()
    app.state.redis = redis.Redis(host="redis", port=6379, decode_responses=True)


# ✅ Получение заметок с кешированием
@app.get("/notes", response_model=List[schemas.NoteOut])
async def get_notes(session: AsyncSession = Depends(async_session)):
    redis_client = app.state.redis
    cache_key = "notes_cache"

    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    notes = await crud.get_notes(session)
    await redis_client.set(cache_key, json.dumps([note.model_dump() for note in notes]), ex=60)
    return notes


# ✅ Добавление заметки и инвалидация кеша
@app.post("/notes", response_model=schemas.NoteOut)
async def add_note(note: schemas.NoteCreate, session: AsyncSession = Depends(async_session)):
    new_note = await crud.create_note(session, note)
    await app.state.redis.delete("notes_cache")
    return new_note


# ✅ Celery задача
@app.get("/send-email/")
async def trigger_email(email: str):
    task = send_email.delay(email)
    return {"message": f"Задача на отправку письма на {email} отправлена в очередь", "task_id": task.id}


# ✅ WebSocket endpoint
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


# ✅ Тестовая страница WebSocket
@app.get("/test", response_class=HTMLResponse)
async def websocket_test_page():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>WebSocket Test</title>
    </head>
    <body style="background:#111;color:white;font-family:sans-serif;">
      <h2>🔌 WebSocket Подключение</h2>

      <input type="text" id="messageInput" placeholder="Введите сообщение..." />
      <button onclick="sendMessage()">Отправить</button>

      <div id="chat" style="margin-top: 20px;"></div>

      <script>
        const socket = new WebSocket("ws://" + window.location.hostname + ":8000/ws");

        socket.onopen = () => {
          const chat = document.getElementById("chat");
          chat.innerHTML += "<p style='color:lightgreen;'>✅ Соединение установлено</p>";
        };

        socket.onmessage = (event) => {
          const chat = document.getElementById("chat");
          chat.innerHTML += `<p>📨 ${event.data}</p>`;
        };

        socket.onclose = () => {
          const chat = document.getElementById("chat");
          chat.innerHTML += "<p style='color:red;'>❌ Соединение закрыто</p>";
        };

        function sendMessage() {
          const input = document.getElementById("messageInput");
          socket.send(input.value);
          input.value = "";
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
