import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SubtopicChecklistItem(Base):
    __tablename__ = "subtopic_checklist_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subtopic_id = Column(String(36), ForeignKey("learning_subtopics.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    subtopic = relationship("LearningSubtopic", back_populates="checklist_items")
