import uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectAttachment(Base):
    __tablename__ = "project_attachments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    file_type = Column(String(50), default="link")
    file_size_bytes = Column(BigInteger, default=0)
    uploaded_at = Column(DateTime, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="attachments")

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def fileType(self) -> str:
        return self.file_type or "link"

    @property
    def fileSizeBytes(self) -> int:
        return self.file_size_bytes or 0

    @property
    def uploadedAt(self) -> datetime:
        return self.uploaded_at
