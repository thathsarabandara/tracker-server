import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectTimeLog(Base):
    __tablename__ = "project_time_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    duration_hours = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="time_logs")
    task = relationship("ProjectTask", back_populates="time_logs")
    user = relationship("User", backref="project_time_logs")

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def taskId(self) -> Optional[str]:
        return self.task_id

    @property
    def userId(self) -> str:
        return self.user_id

    @property
    def durationHours(self) -> float:
        return float(self.duration_hours or 0.0)

    @property
    def loggedAt(self) -> datetime:
        return self.logged_at
