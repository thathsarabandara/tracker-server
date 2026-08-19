import re
import uuid
import logging
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from app.config import settings

logger = logging.getLogger("pulse.upload_middleware")


class R2UploadValidator:
    """Validator & sanitizer middleware helper for Cloudflare R2 Object Storage file uploads."""

    def __init__(
        self,
        max_file_size: int = None,
        allowed_mime_types: list = None
    ):
        self.max_file_size = max_file_size or settings.MAX_UPLOAD_SIZE_BYTES
        self.allowed_mime_types = allowed_mime_types or settings.ALLOWED_UPLOAD_MIME_TYPES

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and ensure safe Object Storage keys."""
        cleaned = re.sub(r"[^\w\.-]", "_", filename)
        ext = ""
        if "." in cleaned:
            ext = cleaned[cleaned.rfind("."):]
            name = cleaned[:cleaned.rfind(".")]
        else:
            name = cleaned

        unique_prefix = uuid.uuid4().hex[:8]
        return f"{name}_{unique_prefix}{ext}".lower()

    async def validate_upload(self, file: UploadFile) -> Tuple[bytes, str, str]:
        """
        Validate file content size, MIME type, and return sanitized key name with file content bytes.
        """
        # Validate MIME type
        content_type = file.content_type or "application/octet-stream"
        if self.allowed_mime_types and content_type.lower() not in [m.lower() for m in self.allowed_mime_types]:
            logger.warning(f"Upload rejected: MIME type '{content_type}' is not allowed.")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{content_type}'. Allowed types: {', '.join(self.allowed_mime_types)}"
            )

        # Read file content & validate size
        contents = await file.read()
        file_size = len(contents)

        if file_size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            logger.warning(f"Upload rejected: File size {file_size} bytes exceeds limit of {self.max_file_size} bytes.")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed limit of {max_mb:.1f} MB."
            )

        sanitized_key = self.sanitize_filename(file.filename or "upload.bin")
        return contents, sanitized_key, content_type


r2_upload_validator = R2UploadValidator()
