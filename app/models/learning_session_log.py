import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LearningSessionLog(Base):
    __tablename__ = "learning_session_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String(36), ForeignKey("learning_topics.id", ondelete="CASCADE"), nullable=False)
    subtopic_id = Column(String(36), ForeignKey("learning_subtopics.id", ondelete="SET NULL"), nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User")
    topic = relationship("LearningTopic", back_populates="session_logs")
    subtopic = relationship("LearningSubtopic", back_populates="session_logs")
