import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("tracker.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Custom middleware measuring execution time and logging incoming HTTP requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        response: Response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        
        logger.info(
            f"{request.method} {request.url.path} - Status: {response.status_code} - Process Time: {process_time:.4f}s"
        )
        
        return response
