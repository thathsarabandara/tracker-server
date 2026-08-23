import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LearningTopic(Base):
    __tablename__ = "learning_topics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="Software Engineering")
    icon = Column(String(50), default="BookOpen")
    progress = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    current_item_title = Column(String(255), nullable=True)
    est_minutes_remaining = Column(Integer, default=0)
    total_est_minutes = Column(Integer, default=0)
    is_carry_forward = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", backref="learning_topics")
    subtopics = relationship("LearningSubtopic", back_populates="topic", cascade="all, delete-orphan", order_by="LearningSubtopic.display_order")
    session_logs = relationship("LearningSessionLog", back_populates="topic", cascade="all, delete-orphan")


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
