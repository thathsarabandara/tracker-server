from fastapi import APIRouter
from app.config import settings, check_db_connection
from app.services.storage_service import storage_service
from app.services.email_service import email_service
from app.utils.helpers import format_utc_now

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Perform System Health Check")
def health_check():
    db_ok = check_db_connection()
    r2_configured = storage_service.is_configured()
    smtp_configured = email_service.is_configured()

    return {
        "status": "healthy" if db_ok else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": format_utc_now(),
        "services": {
            "mysql_database": {
                "connected": db_ok,
                "host": settings.MYSQL_HOST,
                "port": settings.MYSQL_PORT,
                "database": settings.MYSQL_DATABASE
            },
            "cloudflare_r2": {
                "configured": r2_configured,
                "bucket": settings.R2_BUCKET_NAME,
                "endpoint": settings.R2_RESOLVED_ENDPOINT_URL or "Not set"
            },
            "smtp_email": {
                "configured": smtp_configured,
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "from_email": settings.SMTP_FROM_EMAIL
            }
        }
    }
