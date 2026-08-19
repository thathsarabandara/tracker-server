import logging
from datetime import datetime, timezone
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

logger = logging.getLogger("pulse.exceptions")


def format_error_code(status_code: int, detail: str) -> str:
    """Format human-readable error code string."""
    if status_code == 401:
        return "UNAUTHORIZED"
    elif status_code == 403:
        return "FORBIDDEN"
    elif status_code == 404:
        return "NOT_FOUND"
    elif status_code == 422:
        return "VALIDATION_FAILED"
    elif status_code == 429:
        return "RATE_LIMIT_EXCEEDED"
    elif status_code == 400:
        return "BAD_REQUEST"
    return "INTERNAL_SERVER_ERROR"


async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardized HTTP Exception Handler producing Pulse API error envelope."""
    error_code = format_error_code(exc.status_code, str(exc.detail))
    
    # If detail is already a dict, extract code/message
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "An error occurred")
        code = exc.detail.get("code", error_code)
    else:
        message = str(exc.detail)
        code = error_code

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "statusCode": exc.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        },
        headers=getattr(exc, "headers", None)
    )


async def custom_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardized Request Validation Exception Handler."""
    errors = exc.errors()
    first_error_msg = errors[0]["msg"] if errors else "Validation failed for input payload"
    field_name = errors[0]["loc"][-1] if errors and len(errors[0]["loc"]) > 0 else ""
    
    detailed_message = f"Validation failed: {field_name} - {first_error_msg}" if field_name else first_error_msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": detailed_message,
                "statusCode": 422,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )
