import json
import time
import logging
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

logger = logging.getLogger("AgentForge.RateLimiter")

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # In-memory token bucket mapping: client_ip -> (current_tokens, last_refill_timestamp)
        self.buckets = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Bypass rate limits on health, static, and metrics checks, or during automated test suites
        import os
        if os.getenv("TESTING") == "true" and not request.headers.get("x-force-rate-limit"):
            return await call_next(request)

        if request.url.path in ["/", "/api/v1/health", "/api/v1/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown-client"
        now = time.time()
        
        limit = float(settings.RATE_LIMIT_LIMIT)
        window = float(settings.RATE_LIMIT_WINDOW_SECONDS)

        # Initialize bucket for IP if new
        if client_ip not in self.buckets:
            self.buckets[client_ip] = (limit, now)

        tokens, last_update = self.buckets[client_ip]
        
        # Calculate tokens to add based on time elapsed
        elapsed = now - last_update
        tokens_to_add = elapsed * (limit / window)
        new_tokens = min(limit, tokens + tokens_to_add)

        # Check if enough tokens exist
        if new_tokens < 1.0:
            self.buckets[client_ip] = (new_tokens, now)
            logger.warning(f"Rate limit exceeded for client: {client_ip}")
            return Response(
                content=json.dumps({
                    "detail": "Rate limit exceeded. Too many requests.",
                    "type": "RateLimitExceeded",
                    "status_code": 429
                }),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )

        # Consume 1 token
        self.buckets[client_ip] = (new_tokens - 1.0, now)
        return await call_next(request)
