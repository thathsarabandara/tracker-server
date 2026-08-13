import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from app.config.database import Base


def generate_uuid() -> str:
    """Generate string representation of a UUID4."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_name = Column(String(150), nullable=False)
    browser = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    location = Column(String(150), nullable=True)
    last_active_at = Column(DateTime, default=utc_now)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="user_sessions")

    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
    )
