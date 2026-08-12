import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Pulse Server API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:4200"
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:4200", "http://localhost:8000"]

    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Security & JWT Configuration
    JWT_SECRET_KEY: str = "pulse_super_secret_jwt_token_key_change_in_prod_12345"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting Configuration
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100

    # Cloudflare R2 Upload Validation Configuration
    MAX_UPLOAD_SIZE_BYTES: int = 10485760  # 10 MB
    ALLOWED_UPLOAD_MIME_TYPES: Union[List[str], str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
        "application/zip"
    ]

    # MySQL Configuration
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "tracker_user"
    MYSQL_PASSWORD: str = "tracker_password"
    MYSQL_DATABASE: str = "tracker_db"

    # Cloudflare R2 Object Storage Configuration
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "tracker-bucket"
    R2_ENDPOINT_URL: str = ""
    R2_PUBLIC_CUSTOM_DOMAIN: Optional[str] = None

    # SMTP Email Configuration (Pulse branding default)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@pulse.io"
    SMTP_FROM_NAME: str = "Pulse"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_UPLOAD_MIME_TYPES", mode="before")
    def parse_list_fields(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """Construct SQLAlchemy MySQL database URL."""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def R2_RESOLVED_ENDPOINT_URL(self) -> str:
        """Construct Cloudflare R2 endpoint URL if account ID is provided."""
        if self.R2_ENDPOINT_URL:
            return self.R2_ENDPOINT_URL
        if self.R2_ACCOUNT_ID:
            return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        return ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
