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


class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id = Column(String(36), ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="todo")  # backlog, todo, in_progress, in_review, completed
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    est_hours = Column(Float, default=1.0)
    spent_hours = Column(Float, default=0.0)
    due_date = Column(DateTime, nullable=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    milestone = relationship("ProjectMilestone", back_populates="tasks")
    checklist = relationship("TaskChecklistItem", back_populates="task", cascade="all, delete-orphan", order_by="TaskChecklistItem.display_order")
    time_logs = relationship("ProjectTimeLog", back_populates="task")

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def milestoneId(self) -> Optional[str]:
        return self.milestone_id

    @property
    def estHours(self) -> float:
        return float(self.est_hours or 0.0)

    @property
    def spentHours(self) -> float:
        return float(self.spent_hours or 0.0)

    @property
    def dueDate(self) -> Optional[datetime]:
        return self.due_date

    @property
    def displayOrder(self) -> int:
        return self.display_order or 0

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
