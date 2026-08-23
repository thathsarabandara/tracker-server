import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LearningSubtopic(Base):
    __tablename__ = "learning_subtopics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic_id = Column(String(36), ForeignKey("learning_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    est_minutes = Column(Integer, default=30)
    completed = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    topic = relationship("LearningTopic", back_populates="subtopics")
    checklist_items = relationship("SubtopicChecklistItem", back_populates="subtopic", cascade="all, delete-orphan", order_by="SubtopicChecklistItem.display_order")
    session_logs = relationship("LearningSessionLog", back_populates="subtopic")
