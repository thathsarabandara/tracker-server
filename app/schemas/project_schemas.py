from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# 📌 1. CHECKLIST ITEM SCHEMAS
# ==========================================

class CreateChecklistItemInput(BaseModel):
    title: str = Field(..., example="Verify responsive layout")
    displayOrder: Optional[int] = Field(0, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class CreateChecklistItemRequest(BaseModel):
    title: str = Field(..., example="Verify responsive layout")
    displayOrder: Optional[int] = Field(0, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class UpdateChecklistItemRequest(BaseModel):
    title: str = Field(..., example="Verify responsive tablet layout")


class ChecklistItemDTO(BaseModel):
    id: str
    taskId: Optional[str] = Field(None, alias="task_id")
    title: str
    completed: bool = False
    displayOrder: int = Field(0, alias="display_order")
    createdAt: Optional[datetime] = Field(None, alias="created_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 2. TASK SCHEMAS
# ==========================================

class CreateTaskInput(BaseModel):
    title: str = Field(..., example="Implement API Spec")
    description: Optional[str] = Field(None, example="Draft full REST endpoint")
    milestoneId: Optional[str] = Field(None, alias="milestone_id")
    status: Optional[str] = Field("todo", example="todo")  # backlog, todo, in_progress, in_review, completed
    priority: Optional[str] = Field("medium", example="high")  # low, medium, high, urgent
    estHours: Optional[float] = Field(1.0, alias="est_hours", example=8.0)
    dueDate: Optional[datetime] = Field(None, alias="due_date")
    displayOrder: Optional[int] = Field(0, alias="display_order")
    checklist: Optional[List[Union[str, CreateChecklistItemInput]]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class CreateTaskRequest(CreateTaskInput):
    pass


class UpdateTaskStatusRequest(BaseModel):
    status: str = Field(..., example="completed")
    displayOrder: Optional[int] = Field(None, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class TaskSummaryDTO(BaseModel):
    id: str
    projectId: Optional[str] = Field(None, alias="project_id")
    milestoneId: Optional[str] = Field(None, alias="milestone_id")
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    estHours: float = Field(0.0, alias="est_hours")
    spentHours: float = Field(0.0, alias="spent_hours")
    dueDate: Optional[datetime] = Field(None, alias="due_date")
    displayOrder: int = Field(0, alias="display_order")
    checklistCount: int = Field(0, alias="checklist_count")
    completedChecklistCount: int = Field(0, alias="completed_checklist_count")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TaskDTO(BaseModel):
    id: str
    projectId: Optional[str] = Field(None, alias="project_id")
    milestoneId: Optional[str] = Field(None, alias="milestone_id")
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    estHours: float = Field(0.0, alias="est_hours")
    spentHours: float = Field(0.0, alias="spent_hours")
    dueDate: Optional[datetime] = Field(None, alias="due_date")
    displayOrder: int = Field(0, alias="display_order")
    checklist: List[ChecklistItemDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 3. MILESTONE SCHEMAS
# ==========================================

class CreateMilestoneInput(BaseModel):
    title: str = Field(..., example="MVP Launch")
    description: Optional[str] = Field(None, example="Initial public release")
    status: Optional[str] = Field("pending", example="pending")  # pending, in_progress, completed
    targetDate: Optional[datetime] = Field(None, alias="target_date")
    displayOrder: Optional[int] = Field(0, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class CreateMilestoneRequest(CreateMilestoneInput):
    pass


class UpdateMilestoneRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    targetDate: Optional[datetime] = Field(None, alias="target_date")
    displayOrder: Optional[int] = Field(None, alias="display_order")

    model_config = ConfigDict(populate_by_name=True)


class MilestoneDTO(BaseModel):
    id: str
    projectId: Optional[str] = Field(None, alias="project_id")
    title: str
    description: Optional[str] = None
    status: str = "pending"
    targetDate: Optional[datetime] = Field(None, alias="target_date")
    displayOrder: int = Field(0, alias="display_order")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 4. TIME LOG SCHEMAS
# ==========================================

class CreateTimeLogRequest(BaseModel):
    taskId: Optional[str] = Field(None, alias="task_id")
    durationHours: float = Field(..., alias="duration_hours", example=3.5)
    notes: Optional[str] = Field(None, example="Completed initial backend setup.")

    model_config = ConfigDict(populate_by_name=True)


class TimeLogDTO(BaseModel):
    id: str
    projectId: str = Field(..., alias="project_id")
    taskId: Optional[str] = Field(None, alias="task_id")
    userId: str = Field(..., alias="user_id")
    durationHours: float = Field(..., alias="duration_hours")
    notes: Optional[str] = None
    loggedAt: Optional[datetime] = Field(None, alias="logged_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 5. ATTACHMENT SCHEMAS
# ==========================================

class CreateAttachmentRequest(BaseModel):
    name: str = Field(..., example="Figma Design Specs")
    url: str = Field(..., example="https://figma.com/file/xyz")
    fileType: Optional[str] = Field("link", alias="file_type", example="link")
    fileSizeBytes: Optional[int] = Field(0, alias="file_size_bytes", example=1024)

    model_config = ConfigDict(populate_by_name=True)


class AttachmentDTO(BaseModel):
    id: str
    projectId: str = Field(..., alias="project_id")
    name: str
    url: str
    fileType: str = Field("link", alias="file_type")
    fileSizeBytes: int = Field(0, alias="file_size_bytes")
    uploadedAt: Optional[datetime] = Field(None, alias="uploaded_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 6. PROJECT SCHEMAS
# ==========================================

class CreateProjectRequest(BaseModel):
    title: str = Field(..., example="Pulse Focus Engine")
    description: Optional[str] = Field(None, example="Project management module")
    category: Optional[str] = Field("Software Engineering", example="Software Engineering")
    icon: Optional[str] = Field("Folder", example="Folder")
    color: Optional[str] = Field("#3B82F6", example="#3B82F6")
    priority: Optional[str] = Field("medium", example="high")
    startDate: Optional[datetime] = Field(None, alias="start_date")
    targetDate: Optional[datetime] = Field(None, alias="target_date")
    milestones: Optional[List[CreateMilestoneInput]] = Field(default_factory=list)
    tasks: Optional[List[CreateTaskInput]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UpdateProjectMetadataRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    startDate: Optional[datetime] = Field(None, alias="start_date")
    targetDate: Optional[datetime] = Field(None, alias="target_date")

    model_config = ConfigDict(populate_by_name=True)


class ProjectSummaryDTO(BaseModel):
    id: str
    userId: str = Field(..., alias="user_id")
    title: str
    description: Optional[str] = None
    category: str = "Software Engineering"
    icon: str = "Folder"
    color: str = "#3B82F6"
    status: str = "active"
    priority: str = "medium"
    progress: int = 0
    totalTasks: int = Field(0, alias="total_tasks")
    completedTasks: int = Field(0, alias="completed_tasks")
    totalEstHours: float = Field(0.0, alias="total_est_hours")
    spentHours: float = Field(0.0, alias="spent_hours")
    remainingHours: float = Field(0.0, alias="remaining_hours")
    startDate: Optional[datetime] = Field(None, alias="start_date")
    targetDate: Optional[datetime] = Field(None, alias="target_date")
    createdAt: Optional[datetime] = Field(None, alias="created_at")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectDetailDTO(ProjectSummaryDTO):
    milestones: List[MilestoneDTO] = Field(default_factory=list)
    tasks: List[TaskDTO] = Field(default_factory=list)
    timeLogs: List[TimeLogDTO] = Field(default_factory=list, alias="time_logs")
    attachments: List[AttachmentDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==========================================
# 📌 7. ANALYTICS & DUAL-MODE RAW JSON SCHEMAS
# ==========================================

class ProjectAnalyticsDTO(BaseModel):
    projectId: str
    overallProgress: int
    taskBreakdown: Dict[str, int]
    hoursSummary: Dict[str, float]
    overdueTaskCount: int


class RawJsonPayloadRequest(BaseModel):
    jsonPayload: Union[str, Dict[str, Any]] = Field(..., example={"title": "My Project", "tasks": []})
