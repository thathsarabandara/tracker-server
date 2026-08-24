from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# 📌 1. TIME BLOCK CHECKLIST SCHEMAS
# ==========================================

class CreateTimeBlockChecklistItemInput(BaseModel):
    title: str = Field(..., example="Implement signal effect() hook")
    displayOrder: Optional[int] = Field(0, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class TimeBlockChecklistItemDTO(BaseModel):
    id: str
    blockId: Optional[str] = Field(None, alias="block_id")
    title: str
    completed: bool = False
    displayOrder: int = Field(0, alias="display_order")
    createdAt: Optional[datetime] = Field(None, alias="created_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 2. TIME BLOCK SCHEMAS
# ==========================================

class CreateTimeBlockRequest(BaseModel):
    title: str = Field(..., example="System Architecture Sync")
    description: Optional[str] = Field(None, example="Review backend service layers")
    category: Optional[str] = Field("Deep Work", example="Deep Work")  # Deep Work, Learning, Meeting, Exercise, Break, Personal
    color: Optional[str] = Field("#6366F1", example="#6366F1")
    startTime: str = Field(..., alias="start_time", example="09:00")
    endTime: str = Field(..., alias="end_time", example="10:30")
    durationMinutes: Optional[int] = Field(30, alias="duration_minutes", example=90)
    status: Optional[str] = Field("planned", example="planned")  # planned, in_progress, completed, skipped, carried_forward
    isCarryForward: Optional[bool] = Field(False, alias="is_carry_forward")
    linkedTopicId: Optional[str] = Field(None, alias="linked_topic_id")
    linkedTaskId: Optional[str] = Field(None, alias="linked_task_id")
    displayOrder: Optional[int] = Field(0, alias="display_order")
    checklist: Optional[List[Union[str, CreateTimeBlockChecklistItemInput]]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UpdateBlockStatusRequest(BaseModel):
    status: str = Field(..., example="completed")

    model_config = ConfigDict(populate_by_name=True)


class TimeBlockDTO(BaseModel):
    id: str
    scheduleId: Optional[str] = Field(None, alias="schedule_id")
    title: str
    description: Optional[str] = None
    category: str = "Deep Work"
    color: str = "#6366F1"
    startTime: str = Field(..., alias="start_time")
    endTime: str = Field(..., alias="end_time")
    durationMinutes: int = Field(30, alias="duration_minutes")
    status: str = "planned"
    isCarryForward: bool = Field(False, alias="is_carry_forward")
    linkedTopicId: Optional[str] = Field(None, alias="linked_topic_id")
    linkedTaskId: Optional[str] = Field(None, alias="linked_task_id")
    displayOrder: int = Field(0, alias="display_order")
    checklist: List[TimeBlockChecklistItemDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 3. DAILY ROUTINE SCHEMAS
# ==========================================

class CreateRoutineItemRequest(BaseModel):
    title: str = Field(..., example="Morning Hydration & Planning")
    routineType: Optional[str] = Field("morning", alias="routine_type", example="morning")  # morning, afternoon, evening
    displayOrder: Optional[int] = Field(0, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class RoutineItemDTO(BaseModel):
    id: str
    scheduleId: Optional[str] = Field(None, alias="schedule_id")
    title: str
    routineType: str = Field("morning", alias="routine_type")
    completed: bool = False
    displayOrder: int = Field(0, alias="display_order")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 4. DAILY REFLECTION SCHEMAS
# ==========================================

class SaveReflectionRequest(BaseModel):
    dayRating: Optional[int] = Field(5, alias="day_rating", example=5)  # 1 to 5
    winsNotes: Optional[str] = Field(None, alias="wins_notes", example="Completed initial backend implementation.")
    blockersNotes: Optional[str] = Field(None, alias="blockers_notes", example="None")
    generalNotes: Optional[str] = Field(None, alias="general_notes", example="Great focus day.")

    model_config = ConfigDict(populate_by_name=True)


class DailyReflectionDTO(BaseModel):
    id: str
    scheduleId: str = Field(..., alias="schedule_id")
    userId: str = Field(..., alias="user_id")
    dayRating: int = Field(5, alias="day_rating")
    winsNotes: Optional[str] = Field(None, alias="wins_notes")
    blockersNotes: Optional[str] = Field(None, alias="blockers_notes")
    generalNotes: Optional[str] = Field(None, alias="general_notes")
    createdAt: Optional[datetime] = Field(None, alias="created_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 5. DAILY SCHEDULE SCHEMAS
# ==========================================

class UpdateScheduleMetadataRequest(BaseModel):
    status: Optional[str] = None
    moodScore: Optional[int] = Field(None, alias="mood_score")
    energyLevel: Optional[int] = Field(None, alias="energy_level")
    focusGoalMinutes: Optional[int] = Field(None, alias="focus_goal_minutes")

    model_config = ConfigDict(populate_by_name=True)


class DailyScheduleDTO(BaseModel):
    id: str
    userId: str = Field(..., alias="user_id")
    scheduleDate: str = Field(..., alias="schedule_date")
    status: str = "active"
    moodScore: int = Field(3, alias="mood_score")
    energyLevel: int = Field(3, alias="energy_level")
    focusGoalMinutes: int = Field(180, alias="focus_goal_minutes")
    completedFocusMinutes: int = Field(0, alias="completed_focus_minutes")
    totalScheduledMinutes: int = Field(0, alias="total_scheduled_minutes")
    scheduleProgress: int = Field(0, alias="schedule_progress")
    routineProgress: int = Field(0, alias="routine_progress")
    timeBlocks: List[TimeBlockDTO] = Field(default_factory=list, alias="blocks")
    routines: List[RoutineItemDTO] = Field(default_factory=list)
    reflection: Optional[DailyReflectionDTO] = None
    createdAt: Optional[datetime] = Field(None, alias="created_at")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 6. ANALYTICS & DUAL-MODE RAW JSON SCHEMAS
# ==========================================

class WeeklyScheduleAnalyticsDTO(BaseModel):
    period: str
    totalFocusHours: float
    averageDailyFocusMinutes: int
    averageScheduleProgress: int
    averageRoutineProgress: int
    categoryBreakdown: Dict[str, float]
    dailyCompletionScores: List[Dict[str, Any]]


class RawScheduleJsonPayloadRequest(BaseModel):
    jsonPayload: Union[str, Dict[str, Any]] = Field(..., example={"moodScore": 4, "timeBlocks": []})
