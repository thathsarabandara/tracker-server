import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskChecklistItem(Base):
    __tablename__ = "task_checklist_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    task = relationship("ProjectTask", back_populates="checklist")

    @property
    def taskId(self) -> str:
        return self.task_id

    @property
    def displayOrder(self) -> int:
        return self.display_order or 0

    @property
    def createdAt(self) -> datetime:
        return self.created_at
