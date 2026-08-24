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


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, in_progress, completed
    target_date = Column(DateTime, nullable=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="milestones")
    tasks = relationship("ProjectTask", back_populates="milestone")

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def targetDate(self) -> Optional[datetime]:
        return self.target_date

    @property
    def displayOrder(self) -> int:
        return self.display_order or 0

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
