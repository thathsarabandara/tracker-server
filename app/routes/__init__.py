from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.user_profile import router as user_profile_router
from app.routes.learning_roadmap import router as learning_router
from app.routes.project_management import router as project_router
from app.routes.daily_schedule import router as schedule_router

__all__ = [
    "auth_router",
    "health_router",
    "user_profile_router",
    "learning_router",
    "project_router",
    "schedule_router"
]


