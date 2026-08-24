from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import User
from app.schemas.schedule_schemas import (
    CreateRoutineItemRequest,
    CreateTimeBlockRequest,
    DailyReflectionDTO,
    DailyScheduleDTO,
    RawScheduleJsonPayloadRequest,
    RoutineItemDTO,
    SaveReflectionRequest,
    TimeBlockDTO,
    UpdateBlockStatusRequest,
    UpdateScheduleMetadataRequest,
    WeeklyScheduleAnalyticsDTO
)
from app.services.schedule_service import schedule_service
from app.utils.auth_utils import get_current_user
from app.utils.helpers import success_response

router = APIRouter(prefix="/schedule", tags=["Daily Schedule Engine"])


# ==========================================
# 📌 1. SCHEDULE CORE ENDPOINTS
# ==========================================

@router.get("/today", summary="Get Today's Schedule (Auto-Initialize if missing)")
def get_today_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns today's schedule for current user, carrying forward uncompleted tasks from yesterday."""
    schedule = schedule_service.get_or_create_today_schedule(db=db, user_id=current_user.id)
    dto = DailyScheduleDTO.model_validate(schedule).model_dump()
    return success_response(data=dto, message="Today's schedule retrieved successfully.")


@router.get("/date/{date_str}", summary="Get Schedule for Specific Date")
def get_schedule_by_date(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns schedule content for specified date string (YYYY-MM-DD)."""
    try:
        parsed_date = date_type.fromisoformat(date_str)
    except ValueError:
        parsed_date = date_type.today()

    schedule = schedule_service.get_schedule_by_date(db=db, user_id=current_user.id, schedule_date=parsed_date)
    dto = DailyScheduleDTO.model_validate(schedule).model_dump()
    return success_response(data=dto, message="Schedule retrieved successfully.")


@router.put("/{id}", summary="Update Schedule Metadata")
def update_schedule_metadata(
    id: str,
    request_data: UpdateScheduleMetadataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates mood score, energy level, focus goal minutes, or status."""
    schedule = schedule_service.update_schedule_metadata(db=db, user_id=current_user.id, schedule_id=id, request_data=request_data)
    dto = DailyScheduleDTO.model_validate(schedule).model_dump()
    return success_response(data=dto, message="Schedule metadata updated.")


# ==========================================
# 📌 2. TIME BLOCK ENDPOINTS
# ==========================================

@router.post("/{id}/blocks", status_code=status.HTTP_201_CREATED, summary="Create Time Block")
def create_time_block(
    id: str,
    request_data: CreateTimeBlockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a new scheduled time slot to the day's schedule."""
    block = schedule_service.create_time_block(db=db, user_id=current_user.id, schedule_id=id, request_data=request_data)
    dto = TimeBlockDTO.model_validate(block).model_dump()
    return success_response(data=dto, message="Time block added to schedule.", status_code=status.HTTP_201_CREATED)


@router.patch("/{id}/blocks/{blockId}/status", summary="Update Time Block Status")
def update_time_block_status(
    id: str,
    blockId: str,
    request_data: UpdateBlockStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates execution status of a time block and recalculates schedule progress."""
    block = schedule_service.update_time_block_status(db=db, user_id=current_user.id, schedule_id=id, block_id=blockId, status_val=request_data.status)
    dto = TimeBlockDTO.model_validate(block).model_dump()
    return success_response(data=dto, message="Time block status updated.")


@router.post("/{id}/blocks/{blockId}/carry-forward", summary="Carry Forward Slot to Next Day")
def carry_forward_time_block(
    id: str,
    blockId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks time block as carried forward and copies it into tomorrow's schedule."""
    res = schedule_service.carry_forward_time_block(db=db, user_id=current_user.id, schedule_id=id, block_id=blockId)
    return res


@router.delete("/{id}/blocks/{blockId}", summary="Delete Time Block")
def delete_time_block(
    id: str,
    blockId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a time block from schedule."""
    schedule_service.delete_time_block(db=db, user_id=current_user.id, schedule_id=id, block_id=blockId)
    return success_response(data=None, message="Time block deleted.")


# ==========================================
# 📌 3. ROUTINE ENDPOINTS
# ==========================================

@router.post("/{id}/routines", status_code=status.HTTP_201_CREATED, summary="Add Routine Item")
def add_routine_item(
    id: str,
    request_data: CreateRoutineItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a new daily routine / habit checklist item."""
    routine = schedule_service.add_routine_item(db=db, user_id=current_user.id, schedule_id=id, request_data=request_data)
    dto = RoutineItemDTO.model_validate(routine).model_dump()
    return success_response(data=dto, message="Routine item added.", status_code=status.HTTP_201_CREATED)


@router.patch("/{id}/routines/{routineId}/toggle", summary="Toggle Routine Item")
def toggle_routine_item(
    id: str,
    routineId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles completed status of a daily routine item."""
    completed = schedule_service.toggle_routine_item(db=db, user_id=current_user.id, schedule_id=id, routine_id=routineId)
    return {"success": True, "completed": completed}


@router.delete("/{id}/routines/{routineId}", summary="Delete Routine Item")
def delete_routine_item(
    id: str,
    routineId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a daily routine item."""
    schedule_service.delete_routine_item(db=db, user_id=current_user.id, schedule_id=id, routine_id=routineId)
    return success_response(data=None, message="Routine item deleted.")


# ==========================================
# 📌 4. REFLECTION & ANALYTICS ENDPOINTS
# ==========================================

@router.post("/{id}/reflection", status_code=status.HTTP_201_CREATED, summary="Daily Reflection & Journaling")
def save_reflection(
    id: str,
    request_data: SaveReflectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves end-of-day summary, wins, blockers, and self-rating."""
    reflection = schedule_service.save_reflection(db=db, user_id=current_user.id, schedule_id=id, request_data=request_data)
    dto = DailyReflectionDTO.model_validate(reflection).model_dump()
    return success_response(data=dto, message="Daily reflection saved successfully.", status_code=status.HTTP_201_CREATED)


@router.get("/analytics/weekly", summary="Schedule Productivity Analytics")
def get_weekly_analytics(
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns 7-day productivity trends, focus hours, and completion scores."""
    s_date = date_type.fromisoformat(startDate) if startDate else None
    e_date = date_type.fromisoformat(endDate) if endDate else None

    analytics = schedule_service.get_weekly_analytics(db=db, user_id=current_user.id, start_date=s_date, end_date=e_date)
    return success_response(data=analytics, message="Analytics retrieved successfully.")


# ==========================================
# 📌 5. DUAL-MODE RAW JSON EDITING ENDPOINTS
# ==========================================

@router.put("/{id}/raw-json", summary="Raw JSON Overwrite / Import Mode")
def update_raw_json(
    id: str,
    request_data: RawScheduleJsonPayloadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Overwrites/updates full schedule hierarchy using raw JSON payload."""
    schedule = schedule_service.update_raw_json(db=db, user_id=current_user.id, schedule_id=id, request_data=request_data)
    dto = DailyScheduleDTO.model_validate(schedule).model_dump()
    return success_response(data=dto, message="Daily schedule updated via raw JSON payload.")


@router.get("/{id}/export-json", summary="Export Schedule to Standardized JSON Format")
def export_raw_json(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports full day schedule structure to downloadable JSON format."""
    return schedule_service.export_raw_json(db=db, user_id=current_user.id, schedule_id=id)
