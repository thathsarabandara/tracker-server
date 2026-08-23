import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import relationship
from app.config.database import Base



def generate_uuid() -> str:
    """Generate string representation of a UUID4."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    tier = Column(String(50), default="Pro Architect")
    job_title = Column(String(150), nullable=True)
    bio = Column(Text, nullable=True)
    is_email_verified = Column(Boolean, default=False)
    is_2fa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    otp_verifications = relationship("OtpVerification", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    two_factor_recovery_codes = relationship("TwoFactorRecoveryCode", back_populates="user", cascade="all, delete-orphan")

    @property
    def avatarUrl(self) -> Optional[str]:
        return self.avatar_url

    @property
    def jobTitle(self) -> Optional[str]:
        return self.job_title

    @property
    def emailVerified(self) -> bool:
        return self.is_email_verified or False

    @property
    def is2faEnabled(self) -> bool:
        return self.is_2fa_enabled or False

