from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import User
from app.schemas.project_schemas import (
    AttachmentDTO,
    ChecklistItemDTO,
    CreateAttachmentRequest,
    CreateChecklistItemRequest,
    CreateMilestoneRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    CreateTimeLogRequest,
    MilestoneDTO,
    ProjectAnalyticsDTO,
    ProjectDetailDTO,
    ProjectSummaryDTO,
    RawJsonPayloadRequest,
    TaskDTO,
    TimeLogDTO,
    UpdateChecklistItemRequest,
    UpdateMilestoneRequest,
    UpdateProjectMetadataRequest,
    UpdateTaskStatusRequest
)
from app.services.project_service import project_service
from app.utils.auth_utils import get_current_user
from app.utils.helpers import success_response

router = APIRouter(prefix="/projects", tags=["Personal Project Management"])


# ==========================================
# 📌 1. PROJECT MANAGEMENT ENDPOINTS
# ==========================================

@router.get("", summary="Get User Personal Projects")
def get_user_projects(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, on_hold, completed, archived)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, urgent)"),
    search: Optional[str] = Query(None, description="Search query string"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all personal projects belonging to authenticated user."""
    projects = project_service.get_user_projects(
        db=db,
        user_id=current_user.id,
        status_filter=status_filter,
        category=category,
        priority=priority,
        search=search
    )
    dtos = [ProjectSummaryDTO.model_validate(p).model_dump() for p in projects]
    return success_response(data=dtos, message="Projects retrieved successfully.", count=len(dtos))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create Personal Project (Visual Form)")
def create_project(
    request_data: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new personal project with optional initial milestones and tasks."""
    project = project_service.create_project(db=db, user_id=current_user.id, request_data=request_data)
    dto = ProjectSummaryDTO.model_validate(project).model_dump()
    return success_response(data=dto, message="Project created successfully.", status_code=status.HTTP_201_CREATED)


@router.get("/{id}", summary="Get Detailed Inner Project Content")
def get_project_detail(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns detailed inner project structure, milestones, tasks, checklists, time logs, and attachments."""
    project = project_service.get_project_detail(db=db, user_id=current_user.id, project_id=id)
    dto = ProjectDetailDTO.model_validate(project).model_dump()
    return success_response(data=dto, message="Project details retrieved successfully.")


@router.get("/{id}/card", summary="Get Project Card Summary (Lightweight)")
def get_project_card_summary(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches lightweight top-level card summary details for a project without nested milestones/tasks."""
    project = project_service.get_project_card_summary(db=db, user_id=current_user.id, project_id=id)
    dto = ProjectSummaryDTO.model_validate(project).model_dump()
    return success_response(data=dto, message="Project card summary retrieved successfully.")


@router.get("/{id}/milestones", summary="Get Project Milestones List (Non-Detailed)")
def get_project_milestones(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches project milestones list without heavy task micro-checklist arrays."""
    milestones = project_service.get_project_milestones_summary(db=db, user_id=current_user.id, project_id=id)
    dtos = [MilestoneDTO.model_validate(m).model_dump() for m in milestones]
    return success_response(data=dtos, message="Project milestones retrieved successfully.", count=len(dtos))


@router.get("/{id}/tasks/{task_id}/checklist", summary="Get Task Micro-Checklist Items (Lazy Loaded)")
def get_task_checklist(
    id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lazy fetches micro-checklist items when expanding a collapsible task row/card."""
    items = project_service.get_task_checklist(db=db, user_id=current_user.id, project_id=id, task_id=task_id)
    dtos = [ChecklistItemDTO.model_validate(item).model_dump() for item in items]
    return success_response(data=dtos, message="Task checklist items retrieved successfully.", count=len(dtos))


@router.put("/{id}", summary="Update Project Metadata")
def update_project_metadata(
    id: str,
    request_data: UpdateProjectMetadataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates personal project metadata like title, description, category, color, priority, or status."""
    project_service.update_project_metadata(db=db, user_id=current_user.id, project_id=id, request_data=request_data)
    return success_response(data=None, message="Project metadata updated successfully.")


@router.delete("/{id}", summary="Delete Personal Project")
def delete_project(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a personal project and cascades deletion to all child resources."""
    project_service.delete_project(db=db, user_id=current_user.id, project_id=id)
    return success_response(data=None, message="Project deleted successfully.")


# ==========================================
# 📌 2. MILESTONE MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/{id}/milestones", status_code=status.HTTP_201_CREATED, summary="Create Milestone")
def create_milestone(
    id: str,
    request_data: CreateMilestoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new milestone within the project."""
    milestone = project_service.create_milestone(db=db, user_id=current_user.id, project_id=id, request_data=request_data)
    dto = MilestoneDTO.model_validate(milestone).model_dump()
    return success_response(data=dto, message="Milestone created successfully.", status_code=status.HTTP_201_CREATED)


@router.put("/{id}/milestones/{milestoneId}", summary="Update Milestone")
def update_milestone(
    id: str,
    milestoneId: str,
    request_data: UpdateMilestoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates milestone title, description, status, or target date."""
    project_service.update_milestone(db=db, user_id=current_user.id, project_id=id, milestone_id=milestoneId, request_data=request_data)
    return success_response(data=None, message="Milestone updated.")


@router.delete("/{id}/milestones/{milestoneId}", summary="Delete Milestone")
def delete_milestone(
    id: str,
    milestoneId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a milestone."""
    project_service.delete_milestone(db=db, user_id=current_user.id, project_id=id, milestone_id=milestoneId)
    return success_response(data=None, message="Milestone deleted.")


# ==========================================
# 📌 3. KANBAN TASK MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/{id}/tasks", status_code=status.HTTP_201_CREATED, summary="Create Project Task")
def create_task(
    id: str,
    request_data: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new Kanban task under the project."""
    task = project_service.create_task(db=db, user_id=current_user.id, project_id=id, request_data=request_data)
    dto = TaskDTO.model_validate(task).model_dump()
    return success_response(data=dto, message="Task created successfully.", status_code=status.HTTP_201_CREATED)


@router.patch("/{id}/tasks/{taskId}/status", summary="Update Task Status (Drag & Drop Kanban Move)")
def update_task_status(
    id: str,
    taskId: str,
    request_data: UpdateTaskStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates task status and display order, recalculating project progress metrics."""
    project_service.update_task_status(db=db, user_id=current_user.id, project_id=id, task_id=taskId, request_data=request_data)
    return success_response(data=None, message="Task status updated.")


@router.delete("/{id}/tasks/{taskId}", summary="Delete Task")
def delete_task(
    id: str,
    taskId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a task and recalculates project metrics."""
    project_service.delete_task(db=db, user_id=current_user.id, project_id=id, task_id=taskId)
    return success_response(data=None, message="Task deleted.")


# ==========================================
# 📌 4. TASK MICRO-CHECKLIST ITEM ENDPOINTS
# ==========================================

@router.post("/{id}/tasks/{taskId}/checklist", status_code=status.HTTP_201_CREATED, summary="Add Checklist Item")
def add_checklist_item(
    id: str,
    taskId: str,
    request_data: CreateChecklistItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a micro-checklist item to a task."""
    item = project_service.add_checklist_item(db=db, user_id=current_user.id, project_id=id, task_id=taskId, request_data=request_data)
    dto = ChecklistItemDTO.model_validate(item).model_dump()
    return success_response(data=dto, message="Checklist item created.", status_code=status.HTTP_201_CREATED)


@router.patch("/{id}/tasks/{taskId}/checklist/{itemId}/toggle", summary="Toggle Checklist Item Completion")
def toggle_checklist_item(
    id: str,
    taskId: str,
    itemId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles completed status of a checklist item."""
    completed = project_service.toggle_checklist_item(db=db, user_id=current_user.id, project_id=id, task_id=taskId, item_id=itemId)
    return {"success": True, "completed": completed}


@router.put("/{id}/tasks/{taskId}/checklist/{itemId}", summary="Update Checklist Item Title")
def update_checklist_item(
    id: str,
    taskId: str,
    itemId: str,
    request_data: UpdateChecklistItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates checklist item title."""
    project_service.update_checklist_item(db=db, user_id=current_user.id, project_id=id, task_id=taskId, item_id=itemId, request_data=request_data)
    return success_response(data=None, message="Checklist item updated.")


@router.delete("/{id}/tasks/{taskId}/checklist/{itemId}", summary="Delete Checklist Item")
def delete_checklist_item(
    id: str,
    taskId: str,
    itemId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a micro-checklist item."""
    project_service.delete_checklist_item(db=db, user_id=current_user.id, project_id=id, task_id=taskId, item_id=itemId)
    return success_response(data=None, message="Checklist item deleted.")


# ==========================================
# 📌 5. TIME SESSION LOGGING ENDPOINTS
# ==========================================

@router.post("/{id}/time-logs", status_code=status.HTTP_201_CREATED, summary="Log Spent Work Hours")
def log_time(
    id: str,
    request_data: CreateTimeLogRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs spent work session hours for project/task."""
    time_log = project_service.log_time(db=db, user_id=current_user.id, project_id=id, request_data=request_data)
    dto = TimeLogDTO.model_validate(time_log).model_dump()
    return success_response(data=dto, message="Work hours logged successfully.", status_code=status.HTTP_201_CREATED)


@router.get("/{id}/time-logs", summary="Get Project Time Logs")
def get_time_logs(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns list of recorded work session logs for the project."""
    time_logs = project_service.get_time_logs(db=db, user_id=current_user.id, project_id=id)
    dtos = [TimeLogDTO.model_validate(log).model_dump() for log in time_logs]
    return success_response(data=dtos, message="Time logs retrieved successfully.", count=len(dtos))


# ==========================================
# 📌 6. ATTACHMENT ENDPOINTS
# ==========================================

@router.post("/{id}/attachments", status_code=status.HTTP_201_CREATED, summary="Add Attachment or Link")
def add_attachment(
    id: str,
    request_data: CreateAttachmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds reference attachment or URL link to project."""
    attachment = project_service.add_attachment(db=db, user_id=current_user.id, project_id=id, request_data=request_data)
    dto = AttachmentDTO.model_validate(attachment).model_dump()
    return success_response(data=dto, message="Attachment added successfully.", status_code=status.HTTP_201_CREATED)


@router.delete("/{id}/attachments/{attachmentId}", summary="Delete Attachment")
def delete_attachment(
    id: str,
    attachmentId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes attachment from project."""
    project_service.delete_attachment(db=db, user_id=current_user.id, project_id=id, attachment_id=attachmentId)
    return success_response(data=None, message="Attachment deleted.")


# ==========================================
# 📌 7. ANALYTICS & DUAL-MODE EDITING ENDPOINTS
# ==========================================

@router.get("/{id}/analytics", summary="Personal Project Analytics Dashboard")
def get_analytics(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns aggregated metrics, task status breakdown, and time spent summaries."""
    analytics_data = project_service.get_analytics(db=db, user_id=current_user.id, project_id=id)
    return success_response(data=analytics_data, message="Analytics retrieved successfully.")


@router.put("/{id}/raw-json", summary="Raw JSON Overwrite / Bulk Import Mode")
def update_raw_json(
    id: str,
    request_data: RawJsonPayloadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Overwrites/bulk updates the entire project hierarchy via a structured JSON string or payload."""
    project = project_service.update_raw_json(db=db, user_id=current_user.id, project_id=id, request_data=request_data)
    dto = ProjectSummaryDTO.model_validate(project).model_dump()
    return success_response(data=dto, message="Project hierarchy updated via raw JSON payload.")


@router.get("/{id}/export-json", summary="Export Personal Project to Standardized JSON Format")
def export_raw_json(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports full project data structure for backup, file download, or migration."""
    return project_service.export_raw_json(db=db, user_id=current_user.id, project_id=id)
