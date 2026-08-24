from datetime import datetime
from typing import List, Optional, Union
from pydantic import AliasChoices, BaseModel, Field


# --- Subtopic & Checklist Create Schemas ---

class CreateChecklistItemSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class CreateSubtopicSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    estMinutes: int = Field(30, ge=1, validation_alias=AliasChoices('estMinutes', 'est_minutes'))
    checklist: Optional[List[Union[str, CreateChecklistItemSchema]]] = []


# --- Roadmap Create & Update Schemas ---

class CreateRoadmapRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field("Software Engineering", max_length=100)
    icon: Optional[str] = "BookOpen"
    subtopics: Optional[List[CreateSubtopicSchema]] = []


class UpdateRoadmapRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = None


class RawJsonPayloadRequest(BaseModel):
    jsonPayload: str = Field(..., min_length=2, description="Raw JSON string representing the full roadmap hierarchy.")


# --- Subtopic & Checklist Update Schemas ---

class UpdateSubtopicRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    estMinutes: Optional[int] = Field(None, ge=1, validation_alias=AliasChoices('estMinutes', 'est_minutes'))


class CreateChecklistItemRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class UpdateChecklistItemRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class CreateSessionLogRequest(BaseModel):
    subtopicId: Optional[str] = Field(None, validation_alias=AliasChoices('subtopicId', 'subtopic_id'))
    durationMinutes: int = Field(..., ge=1, validation_alias=AliasChoices('durationMinutes', 'duration_minutes'))
    notes: Optional[str] = None


# --- Response DTOs ---

class SubtopicChecklistItemDTO(BaseModel):
    id: str
    subtopicId: str = Field(..., validation_alias=AliasChoices('subtopicId', 'subtopic_id'))
    title: str
    completed: bool = False
    displayOrder: int = Field(0, validation_alias=AliasChoices('displayOrder', 'display_order'))

    class Config:
        from_attributes = True


class LearningSubtopicSummaryDTO(BaseModel):
    id: str
    topicId: str = Field(..., validation_alias=AliasChoices('topicId', 'topic_id'))
    title: str
    description: Optional[str] = None
    estMinutes: int = Field(30, validation_alias=AliasChoices('estMinutes', 'est_minutes'))
    completed: bool = False
    displayOrder: int = Field(0, validation_alias=AliasChoices('displayOrder', 'display_order'))
    checklistCount: int = Field(0, validation_alias=AliasChoices('checklistCount', 'checklist_count'))
    completedChecklistCount: int = Field(0, validation_alias=AliasChoices('completedChecklistCount', 'completed_checklist_count'))

    class Config:
        from_attributes = True


class LearningSubtopicDTO(BaseModel):
    id: str
    topicId: str = Field(..., validation_alias=AliasChoices('topicId', 'topic_id'))
    title: str
    description: Optional[str] = None
    estMinutes: int = Field(30, validation_alias=AliasChoices('estMinutes', 'est_minutes'))
    completed: bool = False
    displayOrder: int = Field(0, validation_alias=AliasChoices('displayOrder', 'display_order'))
    checklist: List[SubtopicChecklistItemDTO] = Field([], validation_alias=AliasChoices('checklist', 'checklist_items'))

    class Config:
        from_attributes = True


class LearningSessionLogDTO(BaseModel):
    id: str
    userId: str = Field(..., validation_alias=AliasChoices('userId', 'user_id'))
    topicId: str = Field(..., validation_alias=AliasChoices('topicId', 'topic_id'))
    subtopicId: Optional[str] = Field(None, validation_alias=AliasChoices('subtopicId', 'subtopic_id'))
    durationMinutes: int = Field(..., validation_alias=AliasChoices('durationMinutes', 'duration_minutes'))
    notes: Optional[str] = None
    completedAt: datetime = Field(..., validation_alias=AliasChoices('completedAt', 'completed_at'))

    class Config:
        from_attributes = True


class LearningTopicSummaryDTO(BaseModel):
    id: str
    userId: str = Field(..., validation_alias=AliasChoices('userId', 'user_id'))
    title: str
    category: str
    icon: str = "BookOpen"
    progress: int = 0
    totalItems: int = Field(0, validation_alias=AliasChoices('totalItems', 'total_items'))
    completedItems: int = Field(0, validation_alias=AliasChoices('completedItems', 'completed_items'))
    currentItemTitle: Optional[str] = Field(None, validation_alias=AliasChoices('currentItemTitle', 'current_item_title'))
    estMinutesRemaining: int = Field(0, validation_alias=AliasChoices('estMinutesRemaining', 'est_minutes_remaining'))
    totalEstMinutes: int = Field(0, validation_alias=AliasChoices('totalEstMinutes', 'total_est_minutes'))
    isCarryForward: bool = Field(False, validation_alias=AliasChoices('isCarryForward', 'is_carry_forward'))

    class Config:
        from_attributes = True


class LearningTopicDetailDTO(LearningTopicSummaryDTO):
    subtopics: List[LearningSubtopicDTO] = []
    sessionLogs: List[LearningSessionLogDTO] = Field([], validation_alias=AliasChoices('sessionLogs', 'session_logs'))

    class Config:
        from_attributes = True
