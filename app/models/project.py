import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, default="Software Engineering", index=True)
    icon = Column(String(50), default="Folder")
    color = Column(String(20), default="#3B82F6")
    status = Column(String(50), default="active", index=True)  # active, on_hold, completed, archived
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    progress = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    total_est_hours = Column(Float, default=0.0)
    spent_hours = Column(Float, default=0.0)
    remaining_hours = Column(Float, default=0.0)
    start_date = Column(DateTime, nullable=True)
    target_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", backref="projects")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan", order_by="ProjectMilestone.display_order")
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan", order_by="ProjectTask.display_order")
    time_logs = relationship("ProjectTimeLog", back_populates="project", cascade="all, delete-orphan")
    attachments = relationship("ProjectAttachment", back_populates="project", cascade="all, delete-orphan")

    @property
    def userId(self) -> str:
        return self.user_id

    @property
    def totalTasks(self) -> int:
        return self.total_tasks or 0

    @property
    def completedTasks(self) -> int:
        return self.completed_tasks or 0

    @property
    def totalEstHours(self) -> float:
        return float(self.total_est_hours or 0.0)

    @property
    def spentHours(self) -> float:
        return float(self.spent_hours or 0.0)

    @property
    def remainingHours(self) -> float:
        return float(self.remaining_hours or 0.0)

    @property
    def startDate(self) -> Optional[datetime]:
        return self.start_date

    @property
    def targetDate(self) -> Optional[datetime]:
        return self.target_date

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
