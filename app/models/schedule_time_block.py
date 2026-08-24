import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleTimeBlock(Base):
    __tablename__ = "schedule_time_blocks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    schedule_id = Column(String(36), ForeignKey("daily_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="Deep Work")  # Deep Work, Learning, Meeting, Exercise, Break, Personal
    color = Column(String(20), default="#6366F1")
    start_time = Column(String(10), nullable=False)  # "09:00"
    end_time = Column(String(10), nullable=False)    # "10:30"
    duration_minutes = Column(Integer, default=30)
    status = Column(String(50), default="planned")   # planned, in_progress, completed, skipped, carried_forward
    is_carry_forward = Column(Boolean, default=False)
    linked_topic_id = Column(String(36), nullable=True)
    linked_task_id = Column(String(36), nullable=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    schedule = relationship("DailySchedule", back_populates="blocks")
    checklist = relationship("TimeBlockChecklistItem", back_populates="block", cascade="all, delete-orphan", order_by="TimeBlockChecklistItem.display_order")

    @property
    def scheduleId(self) -> str:
        return self.schedule_id

    @property
    def startTime(self) -> str:
        return self.start_time

    @property
    def endTime(self) -> str:
        return self.end_time

    @property
    def durationMinutes(self) -> int:
        return self.duration_minutes or 30

    @property
    def isCarryForward(self) -> bool:
        return self.is_carry_forward or False

    @property
    def linkedTopicId(self) -> Optional[str]:
        return self.linked_topic_id

    @property
    def linkedTaskId(self) -> Optional[str]:
        return self.linked_task_id

    @property
    def displayOrder(self) -> int:
        return self.display_order or 0

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
