from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from starlette.responses import JSONResponse
from app.config import settings
import time
import logging

logger = logging.getLogger("uvicorn.error")

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_SECONDS

    async def dispatch(self, request: Request, call_next):
        try:
            redis_client = getattr(request.app.state, "redis", None)
            if not redis_client:
                logger.warning("Redis client is not initialized. Skipping rate limit.")
                return await call_next(request)

            client_ip = request.client.host
            key = f"ratelimit:{client_ip}"

            current_time = int(time.time())
            window_start = current_time - (current_time % self.window)
            redis_key = f"{key}:{window_start}"

            current = await redis_client.get(redis_key)
            if current is None:
                await redis_client.set(redis_key, 1, ex=self.window)
            elif int(current) < self.requests:
                await redis_client.incr(redis_key)
            else:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."}
                )

        except Exception as e:
            logger.error(f"RateLimiterMiddleware error: {e}")
            # Не мешаем работе приложения
            return await call_next(request)

        return await call_next(request)
