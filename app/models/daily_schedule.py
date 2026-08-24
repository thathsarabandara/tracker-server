import uuid
from datetime import datetime, date, timezone
from typing import Optional
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DailySchedule(Base):
    __tablename__ = "daily_schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_date = Column(Date, nullable=False)
    status = Column(String(50), default="active")  # active, completed, skipped, archived
    mood_score = Column(Integer, default=3)  # 1 to 5
    energy_level = Column(Integer, default=3)  # 1 to 5
    focus_goal_minutes = Column(Integer, default=180)
    completed_focus_minutes = Column(Integer, default=0)
    total_scheduled_minutes = Column(Integer, default=0)
    schedule_progress = Column(Integer, default=0)
    routine_progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("user_id", "schedule_date", name="unique_user_schedule_date"),
    )

    # Relationships
    user = relationship("User", backref="daily_schedules")
    blocks = relationship("ScheduleTimeBlock", back_populates="schedule", cascade="all, delete-orphan", order_by="ScheduleTimeBlock.display_order")
    routines = relationship("DailyRoutineItem", back_populates="schedule", cascade="all, delete-orphan", order_by="DailyRoutineItem.display_order")
    reflection = relationship("DailyReflection", back_populates="schedule", uselist=False, cascade="all, delete-orphan")

    @property
    def userId(self) -> str:
        return self.user_id

    @property
    def scheduleDate(self) -> str:
        return self.schedule_date.isoformat() if isinstance(self.schedule_date, (date, datetime)) else str(self.schedule_date)

    @property
    def moodScore(self) -> int:
        return self.mood_score or 3

    @property
    def energyLevel(self) -> int:
        return self.energy_level or 3

    @property
    def focusGoalMinutes(self) -> int:
        return self.focus_goal_minutes or 180

    @property
    def completedFocusMinutes(self) -> int:
        return self.completed_focus_minutes or 0

    @property
    def totalScheduledMinutes(self) -> int:
        return self.total_scheduled_minutes or 0

    @property
    def scheduleProgress(self) -> int:
        return self.schedule_progress or 0

    @property
    def routineProgress(self) -> int:
        return self.routine_progress or 0

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
