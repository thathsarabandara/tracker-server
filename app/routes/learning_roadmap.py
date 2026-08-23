from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import User
from app.schemas import (
    CreateChecklistItemRequest,
    CreateRoadmapRequest,
    CreateSessionLogRequest,
    LearningSessionLogDTO,
    LearningSubtopicDTO,
    LearningTopicDetailDTO,
    LearningTopicSummaryDTO,
    RawJsonPayloadRequest,
    SubtopicChecklistItemDTO,
    UpdateChecklistItemRequest,
    UpdateRoadmapRequest,
    UpdateSubtopicRequest
)
from app.services.learning_service import learning_service
from app.utils.auth_utils import get_current_user
from app.utils.helpers import success_response

router = APIRouter(prefix="/learning/roadmaps", tags=["Learning Roadmap Engine"])


# ==========================================
# 📌 1. ROADMAP MANAGEMENT ENDPOINTS
# ==========================================

@router.get("", summary="Get User Learning Roadmaps")
def get_user_roadmaps(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all learning roadmaps belonging to authenticated user."""
    topics = learning_service.get_user_roadmaps(db=db, user_id=current_user.id, category=category)
    topics_dto = [LearningTopicSummaryDTO.model_validate(t).model_dump() for t in topics]
    return success_response(data=topics_dto, message="Learning roadmaps retrieved successfully.", count=len(topics_dto))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create Learning Roadmap (Visual Form)")
def create_roadmap(
    request_data: CreateRoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new user-scoped learning roadmap via visual form input."""
    topic = learning_service.create_roadmap(db=db, user_id=current_user.id, request_data=request_data)
    topic_dto = LearningTopicSummaryDTO.model_validate(topic).model_dump()
    return success_response(data=topic_dto, message="Learning roadmap created successfully.", status_code=status.HTTP_201_CREATED)


@router.get("/{id}", summary="Get Detailed Inner Roadmap Content")
def get_roadmap_detail(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches detailed inner roadmap structure, subtopics, micro-checklists, and session logs."""
    topic = learning_service.get_roadmap_detail(db=db, topic_id=id, user_id=current_user.id)
    topic_detail_dto = LearningTopicDetailDTO.model_validate(topic).model_dump()
    return success_response(data=topic_detail_dto, message="Roadmap details retrieved successfully.")


@router.put("/{id}", summary="Visual Edit Roadmap Metadata")
def update_roadmap(
    id: str,
    request_data: UpdateRoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates roadmap title, category, and icon via Visual Form."""
    topic = learning_service.update_roadmap(db=db, topic_id=id, user_id=current_user.id, request_data=request_data)
    topic_dto = LearningTopicSummaryDTO.model_validate(topic).model_dump()
    return success_response(data=topic_dto, message="Roadmap updated successfully.")


@router.put("/{id}/raw-json", summary="Raw JSON Format Overwrite / Import Mode")
def update_raw_json(
    id: str,
    request_data: RawJsonPayloadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Overwrites/Updates full inner roadmap structure using raw JSON string payload."""
    topic = learning_service.update_raw_json(
        db=db,
        topic_id=id,
        user_id=current_user.id,
        raw_json_str=request_data.jsonPayload
    )
    topic_dto = LearningTopicSummaryDTO.model_validate(topic).model_dump()
    return success_response(data=topic_dto, message="Roadmap structure updated via JSON payload.")


@router.delete("/{id}", summary="Delete Learning Roadmap")
def delete_roadmap(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a user roadmap and cascades deletion to all subtopics and micro-checklists."""
    learning_service.delete_roadmap(db=db, topic_id=id, user_id=current_user.id)
    return success_response(data=None, message="Learning roadmap deleted successfully.")


@router.get("/{id}/export-json", summary="Export Roadmap to JSON Format")
def export_roadmap_json(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports full inner roadmap hierarchy as a downloadable JSON object payload."""
    export_payload = learning_service.export_roadmap_json(db=db, topic_id=id, user_id=current_user.id)
    return export_payload


# ==========================================
# 📌 2. SUBTOPIC MODULE ENDPOINTS
# ==========================================

@router.patch("/{id}/subtopics/{subtopic_id}/toggle", summary="Toggle Subtopic Completion Status")
def toggle_subtopic(
    id: str,
    subtopic_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles completion state of a subtopic module and recalculates progress %."""
    subtopic = learning_service.toggle_subtopic(db=db, topic_id=id, subtopic_id=subtopic_id, user_id=current_user.id)
    subtopic_dto = LearningSubtopicDTO.model_validate(subtopic).model_dump()
    return success_response(data=subtopic_dto, message="Subtopic completion status toggled.")


@router.put("/{id}/subtopics/{subtopic_id}", summary="Update Subtopic Task (Visual Edit)")
def update_subtopic(
    id: str,
    subtopic_id: str,
    request_data: UpdateSubtopicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates subtopic title, description, and estimated minutes."""
    subtopic = learning_service.update_subtopic(
        db=db,
        topic_id=id,
        subtopic_id=subtopic_id,
        user_id=current_user.id,
        request_data=request_data
    )
    subtopic_dto = LearningSubtopicDTO.model_validate(subtopic).model_dump()
    return success_response(data=subtopic_dto, message="Subtopic updated successfully.")


@router.delete("/{id}/subtopics/{subtopic_id}", summary="Delete Subtopic Module")
def delete_subtopic(
    id: str,
    subtopic_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a subtopic module and its inner micro-checklist items."""
    learning_service.delete_subtopic(db=db, topic_id=id, subtopic_id=subtopic_id, user_id=current_user.id)
    return success_response(data=None, message="Subtopic deleted successfully.")


# ==========================================
# 📌 3. MICRO-CHECKLIST TASK ENDPOINTS
# ==========================================

@router.post("/{id}/subtopics/{subtopic_id}/checklist", status_code=status.HTTP_201_CREATED, summary="Add Micro-Checklist Task Item")
def add_checklist_item(
    id: str,
    subtopic_id: str,
    request_data: CreateChecklistItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a new micro-checklist requirement item under target subtopic."""
    item = learning_service.add_checklist_item(
        db=db,
        topic_id=id,
        subtopic_id=subtopic_id,
        user_id=current_user.id,
        title=request_data.title
    )
    item_dto = SubtopicChecklistItemDTO.model_validate(item).model_dump()
    return success_response(data=item_dto, message="Micro-checklist item created successfully.", status_code=status.HTTP_201_CREATED)


@router.patch("/{id}/subtopics/{subtopic_id}/checklist/{item_id}/toggle", summary="Toggle Micro-Checklist Task Status")
def toggle_checklist_item(
    id: str,
    subtopic_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles individual micro-checklist task status."""
    item = learning_service.toggle_checklist_item(
        db=db,
        topic_id=id,
        subtopic_id=subtopic_id,
        item_id=item_id,
        user_id=current_user.id
    )
    item_dto = SubtopicChecklistItemDTO.model_validate(item).model_dump()
    return success_response(data=item_dto, message="Micro-checklist status toggled.")


@router.put("/{id}/subtopics/{subtopic_id}/checklist/{item_id}", summary="Update Micro-Checklist Task Item")
def update_checklist_item(
    id: str,
    subtopic_id: str,
    item_id: str,
    request_data: UpdateChecklistItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates micro-checklist item title."""
    item = learning_service.update_checklist_item(
        db=db,
        topic_id=id,
        subtopic_id=subtopic_id,
        item_id=item_id,
        user_id=current_user.id,
        title=request_data.title
    )
    item_dto = SubtopicChecklistItemDTO.model_validate(item).model_dump()
    return success_response(data=item_dto, message="Micro-checklist item updated.")


@router.delete("/{id}/subtopics/{subtopic_id}/checklist/{item_id}", summary="Delete Micro-Checklist Task Item")
def delete_checklist_item(
    id: str,
    subtopic_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a specific micro-checklist requirement item."""
    learning_service.delete_checklist_item(
        db=db,
        topic_id=id,
        subtopic_id=subtopic_id,
        item_id=item_id,
        user_id=current_user.id
    )
    return success_response(data=None, message="Micro-checklist item deleted.")


# ==========================================
# 📌 4. LEARNING SESSION LOG ENDPOINTS
# ==========================================

@router.post("/{id}/sessions", status_code=status.HTTP_201_CREATED, summary="Log Focus Session")
def log_session(
    id: str,
    request_data: CreateSessionLogRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs a focus learning session duration and notes."""
    session_log = learning_service.log_session(
        db=db,
        topic_id=id,
        user_id=current_user.id,
        request_data=request_data
    )
    log_dto = LearningSessionLogDTO.model_validate(session_log).model_dump()
    return success_response(data=log_dto, message="Focus session logged successfully.", status_code=status.HTTP_201_CREATED)
