import logging
import time
from typing import BinaryIO, Optional, Union
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from app.config import settings

logger = logging.getLogger("pulse.storage")


class StorageService:
    """Cloudflare R2 Object Storage Service utilizing boto3 S3-compatible client API."""

    @property
    def bucket_name(self) -> str:
        return settings.R2_BUCKET_NAME

    @property
    def public_domain(self) -> Optional[str]:
        return settings.R2_PUBLIC_CUSTOM_DOMAIN

    @property
    def endpoint_url(self) -> str:
        return settings.R2_RESOLVED_ENDPOINT_URL

    @property
    def access_key(self) -> str:
        return settings.R2_ACCESS_KEY_ID

    @property
    def secret_key(self) -> str:
        return settings.R2_SECRET_ACCESS_KEY

    def _get_client(self):
        """Instantiate S3 client configured for Cloudflare R2 endpoint."""
        return boto3.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto",
            config=Config(signature_version="s3v4")
        )

    def is_configured(self) -> bool:
        """Verify if non-placeholder Cloudflare R2 credentials are configured."""
        if not self.endpoint_url or not self.access_key or not self.secret_key:
            return False
        if "your_cloudflare_account_id" in self.endpoint_url or "your_r2_access_key" in self.access_key or "your_" in self.access_key or "your_" in self.secret_key:
            return False
        return True

    def upload_file(
        self,
        file_obj: Union[BinaryIO, bytes],
        object_name: str,
        content_type: Optional[str] = "application/octet-stream"
    ) -> str:
        """Upload file object or bytes to Cloudflare R2 bucket."""
        if not self.is_configured():
            raise RuntimeError("Cloudflare R2 storage credentials are not configured.")

        try:
            client = self._get_client()
            extra_args = {"ContentType": content_type} if content_type else {}
            
            if isinstance(file_obj, bytes):
                client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_obj,
                    **extra_args
                )
            else:
                client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    object_name,
                    ExtraArgs=extra_args
                )
            
            return self.get_public_url(object_name)
        except Exception as e:
            logger.error(f"Failed to upload file '{object_name}' to Cloudflare R2: {e}")
            raise RuntimeError(f"Cloudflare R2 upload failed: {e}")


    def upload_avatar(
        self,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
        user_id: str
    ) -> str:
        """Dedicated Cloudflare R2 object upload helper for user profile avatars."""
        ext = "jpg"
        if "." in original_filename:
            ext = original_filename.split(".")[-1].lower()
        
        timestamp = int(time.time())
        object_key = f"avatars/{user_id}-{timestamp}.{ext}"
        
        return self.upload_file(
            file_obj=file_bytes,
            object_name=object_key,
            content_type=content_type
        )

    def generate_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for downloading an object from Cloudflare R2."""
        if not self.is_configured():
            return self.get_public_url(object_name)
        try:
            client = self._get_client()
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for '{object_name}': {e}")
            return self.get_public_url(object_name)

    def delete_file(self, object_name: str) -> bool:
        """Delete an object from Cloudflare R2 bucket."""
        if not self.is_configured():
            return True
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete file '{object_name}' from Cloudflare R2: {e}")
            return True

    def get_file_bytes(self, object_name: str) -> tuple:
        """Fetch object bytes directly from Cloudflare R2 bucket."""
        client = self._get_client()
        response = client.get_object(Bucket=self.bucket_name, Key=object_name)
        content_type = response.get("ContentType", "image/jpeg")
        file_bytes = response["Body"].read()
        return file_bytes, content_type

    def get_public_url(self, object_name: str) -> str:
        """Get public URL for an object stored in R2 bucket."""
        if self.public_domain and "pub-<hash>" not in self.public_domain and "your_" not in self.public_domain:
            domain = self.public_domain.rstrip("/")
            return f"{domain}/{object_name.lstrip('/')}"
        
        # Return R2 media streaming endpoint URL to serve file directly from bucket
        return f"{settings.API_V1_PREFIX}/user/avatar-file/{object_name.lstrip('/')}"


storage_service = StorageService()

