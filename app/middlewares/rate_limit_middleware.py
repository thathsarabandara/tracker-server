import time
import logging
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.config import settings

logger = logging.getLogger("pulse.ratelimit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiting middleware per client IP address."""

    def __init__(self, app, requests_per_minute: int = None, burst: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.burst = burst or settings.RATE_LIMIT_BURST
        self.requests_history: Dict[str, List[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "127.0.0.1"

    def _clean_old_requests(self, client_ip: str, now: float):
        # Keep requests within 60 seconds
        window_start = now - 60.0
        self.requests_history[client_ip] = [
            ts for ts in self.requests_history[client_ip] if ts > window_start
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude documentation / static routes from strict rate limiting
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()

        self._clean_old_requests(client_ip, now)
        request_count = len(self.requests_history[client_ip])

        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip} on path {request.url.path}")
            retry_after = 60 - int(now - self.requests_history[client_ip][0]) if self.requests_history[client_ip] else 60
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "message": "Too Many Requests. Please slow down and try again later.",
                    "retry_after_seconds": max(1, retry_after)
                },
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )

        self.requests_history[client_ip].append(now)
        remaining = self.requests_per_minute - (request_count + 1)

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response
