import aioredis
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RedisCacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url="redis://redis:6379", ttl=60):
        super().__init__(app)
        self.redis_url = redis_url
        self.ttl = ttl
        self.redis = None

    async def dispatch(self, request: Request, call_next):
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

        if request.method == "GET" and request.url.path == "/notes":
            key = "notes:cache"
            cached = await self.redis.get(key)
            if cached:
                return JSONResponse(content=json.loads(cached))

            response = await call_next(request)
            body = [section async for section in response.body_iterator]
            content = b"".join(body).decode()
            await self.redis.set(key, content, ex=self.ttl)
            return Response(content=content, status_code=response.status_code, media_type="application/json")

        return await call_next(request)
