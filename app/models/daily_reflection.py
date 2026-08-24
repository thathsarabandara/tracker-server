import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DailyReflection(Base):
    __tablename__ = "daily_reflections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    schedule_id = Column(String(36), ForeignKey("daily_schedules.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_rating = Column(Integer, default=5)  # 1 to 5
    wins_notes = Column(Text, nullable=True)
    blockers_notes = Column(Text, nullable=True)
    general_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    schedule = relationship("DailySchedule", back_populates="reflection")
    user = relationship("User", backref="daily_reflections")

    @property
    def scheduleId(self) -> str:
        return self.schedule_id

    @property
    def userId(self) -> str:
        return self.user_id

    @property
    def dayRating(self) -> int:
        return self.day_rating or 5

    @property
    def winsNotes(self) -> Optional[str]:
        return self.wins_notes

    @property
    def blockersNotes(self) -> Optional[str]:
        return self.blockers_notes

    @property
    def generalNotes(self) -> Optional[str]:
        return self.general_notes

    @property
    def createdAt(self) -> datetime:
        return self.created_at
