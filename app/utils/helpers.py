from datetime import datetime, timezone
from typing import Any, Dict, Optional


def format_utc_now() -> str:
    """Return ISO 8601 formatted UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def success_response(
    data: Any,
    message: str = "Success",
    status_code: int = 200,
    count: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """Standardized API response envelope matching Pulse REST API Specification."""
    response = {
        "success": True,
        "message": message,
        "timestamp": format_utc_now()
    }
    if count is not None:
        response["count"] = count
    if data is not None:
        response["data"] = data
    for k, v in kwargs.items():
        if v is not None:
            response[k] = v
    return response
