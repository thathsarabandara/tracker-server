from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.user_profile import router as user_profile_router

__all__ = [
    "auth_router",
    "health_router",
    "user_profile_router"
]
