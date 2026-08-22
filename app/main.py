import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import init_db, settings
from app.middlewares import LoggingMiddleware, RateLimitMiddleware
from app.routes import (
    auth_router,
    health_router,
    user_profile_router
)

from app.utils.exception_handlers import (
    custom_http_exception_handler,
    custom_validation_exception_handler
)

# Setup logger configuration
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pulse.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    # Power Up DB Table Auto Creation (TiDB & MySQL compatible)
    init_db()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Register Exception Handlers for Standard JSON Error Envelope Format
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)

    # Mount CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else [settings.ALLOWED_ORIGINS],
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Mount Custom Request Process Time Logging Middleware
    app.add_middleware(LoggingMiddleware)

    # Mount Rate Limiting Middleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        burst=settings.RATE_LIMIT_BURST
    )

    # Register API Routers under /api/v1
    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(user_profile_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    def root():
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "docs": "/docs",
            "health": "/health",
            "api_version": settings.API_V1_PREFIX,
            "sender": f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        }

    return app


app = create_app()
