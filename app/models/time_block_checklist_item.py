import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimeBlockChecklistItem(Base):
    __tablename__ = "time_block_checklist_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    block_id = Column(String(36), ForeignKey("schedule_time_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    block = relationship("ScheduleTimeBlock", back_populates="checklist")

    @property
    def blockId(self) -> str:
        return self.block_id

    @property
    def displayOrder(self) -> int:
        return self.display_order or 0

    @property
    def createdAt(self) -> datetime:
        return self.created_at
