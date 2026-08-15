from datetime import datetime, timezone
from typing import Any, Dict


def format_utc_now() -> str:
    """Return ISO 8601 formatted UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Standardized API response envelope matching Pulse REST API Specification."""
    response = {
        "success": True,
        "message": message,
        "timestamp": format_utc_now()
    }
    if data is not None:
        response["data"] = data
    return response
