import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config.settings import settings

logger = logging.getLogger("pulse.database")

# Create SQLAlchemy engine with connection pool recycling
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Session factory for DB interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarative class for database models."""
    pass


def init_db():
    """Auto-create all SQL tables on server startup."""
    try:
        # Import models so Base registered all schemas
        from app.models import (  # noqa
            User, OtpVerification, RefreshToken, UserSession, TwoFactorRecoveryCode,
            LearningTopic, LearningSubtopic, SubtopicChecklistItem, LearningSessionLog,
            Project, ProjectMilestone, ProjectTask, TaskChecklistItem, ProjectTimeLog, ProjectAttachment,
            DailySchedule, ScheduleTimeBlock, TimeBlockChecklistItem, DailyRoutineItem, DailyReflection
        )
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization deferred/failed: {e}")



def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check database health connectivity."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"MySQL/TiDB connection check failed: {e}")
        return False
