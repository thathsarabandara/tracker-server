import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    DailyReflection,
    DailyRoutineItem,
    DailySchedule,
    ScheduleTimeBlock,
    TimeBlockChecklistItem
)
from app.schemas.schedule_schemas import (
    CreateRoutineItemRequest,
    CreateTimeBlockChecklistItemInput,
    CreateTimeBlockRequest,
    RawScheduleJsonPayloadRequest,
    SaveReflectionRequest,
    UpdateBlockStatusRequest,
    UpdateScheduleMetadataRequest
)

logger = logging.getLogger("pulse.services.schedule")


class ScheduleService:

    # ==========================================
    # 📌 HELPER METHODS
    # ==========================================

    def get_user_schedule_or_404(self, db: Session, user_id: str, schedule_id: str) -> DailySchedule:
        """Fetch daily schedule belonging to user or raise HTTP 404."""
        schedule = db.query(DailySchedule).filter(DailySchedule.id == schedule_id, DailySchedule.user_id == user_id).first()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SCHEDULE_NOT_FOUND", "message": "The requested daily schedule does not exist or does not belong to you."}
            )
        return schedule

    def recalculate_schedule_metrics(self, db: Session, schedule: DailySchedule) -> None:
        """Recalculate schedule metrics (schedule_progress, routine_progress, focus minutes)."""
        blocks = db.query(ScheduleTimeBlock).filter(ScheduleTimeBlock.schedule_id == schedule.id).all()
        total_blocks = len(blocks)
        completed_blocks = sum(1 for b in blocks if b.status == "completed")
        schedule_progress = int(round((completed_blocks / total_blocks) * 100)) if total_blocks > 0 else 0
        total_scheduled = sum(b.duration_minutes or 0 for b in blocks)
        completed_focus = sum(b.duration_minutes or 0 for b in blocks if b.status == "completed")

        routines = db.query(DailyRoutineItem).filter(DailyRoutineItem.schedule_id == schedule.id).all()
        total_routines = len(routines)
        completed_routines = sum(1 for r in routines if r.completed)
        routine_progress = int(round((completed_routines / total_routines) * 100)) if total_routines > 0 else 0

        schedule.total_scheduled_minutes = total_scheduled
        schedule.completed_focus_minutes = completed_focus
        schedule.schedule_progress = schedule_progress
        schedule.routine_progress = routine_progress

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

    # ==========================================
    # 📌 1. SCHEDULE CORE OPERATIONS
    # ==========================================

    def get_or_create_today_schedule(self, db: Session, user_id: str) -> DailySchedule:
        today_date = date.today()
        schedule = db.query(DailySchedule).filter(
            DailySchedule.user_id == user_id,
            DailySchedule.schedule_date == today_date
        ).first()

        if not schedule:
            schedule = DailySchedule(
                user_id=user_id,
                schedule_date=today_date,
                status="active",
                mood_score=4,
                energy_level=4,
                focus_goal_minutes=240
            )
            db.add(schedule)
            db.flush()

            # Carry over uncompleted blocks from yesterday's schedule
            yesterday_date = today_date - timedelta(days=1)
            yesterday_schedule = db.query(DailySchedule).filter(
                DailySchedule.user_id == user_id,
                DailySchedule.schedule_date == yesterday_date
            ).first()

            if yesterday_schedule:
                uncompleted_blocks = db.query(ScheduleTimeBlock).filter(
                    ScheduleTimeBlock.schedule_id == yesterday_schedule.id,
                    ScheduleTimeBlock.status.in_(["planned", "in_progress", "carried_forward"])
                ).all()

                for b in uncompleted_blocks:
                    new_block = ScheduleTimeBlock(
                        schedule_id=schedule.id,
                        title=b.title,
                        description=b.description,
                        category=b.category,
                        color=b.color,
                        start_time=b.start_time,
                        end_time=b.end_time,
                        duration_minutes=b.duration_minutes,
                        status="planned",
                        is_carry_forward=True,
                        linked_topic_id=b.linked_topic_id,
                        linked_task_id=b.linked_task_id,
                        display_order=b.display_order
                    )
                    db.add(new_block)
                    db.flush()

                    for c in b.checklist:
                        new_chk = TimeBlockChecklistItem(
                            block_id=new_block.id,
                            title=c.title,
                            completed=c.completed,
                            display_order=c.display_order
                        )
                        db.add(new_chk)

            # Add default daily routine checklist items
            default_routines = [
                ("Morning Hydration & Planning", "morning", 0),
                ("30-min Reading / Tech Article", "morning", 1),
                ("Evening Code Review & Journaling", "evening", 2),
            ]
            for r_title, r_type, r_order in default_routines:
                r_item = DailyRoutineItem(
                    schedule_id=schedule.id,
                    title=r_title,
                    routine_type=r_type,
                    completed=False,
                    display_order=r_order
                )
                db.add(r_item)

            db.commit()
            db.refresh(schedule)

        self.recalculate_schedule_metrics(db, schedule)
        return schedule

    def get_schedule_by_date(self, db: Session, user_id: str, schedule_date: date) -> DailySchedule:
        schedule = db.query(DailySchedule).filter(
            DailySchedule.user_id == user_id,
            DailySchedule.schedule_date == schedule_date
        ).first()

        if not schedule:
            # Auto create schedule entry if accessing a future/past date
            schedule = DailySchedule(
                user_id=user_id,
                schedule_date=schedule_date,
                status="active"
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)

        self.recalculate_schedule_metrics(db, schedule)
        return schedule

    def update_schedule_metadata(self, db: Session, user_id: str, schedule_id: str, request_data: UpdateScheduleMetadataRequest) -> DailySchedule:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        if request_data.status is not None:
            schedule.status = request_data.status
        if request_data.moodScore is not None:
            schedule.mood_score = request_data.moodScore
        if request_data.energyLevel is not None:
            schedule.energy_level = request_data.energyLevel
        if request_data.focusGoalMinutes is not None:
            schedule.focus_goal_minutes = request_data.focusGoalMinutes

        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    # ==========================================
    # 📌 2. TIME BLOCK OPERATIONS
    # ==========================================

    def create_time_block(self, db: Session, user_id: str, schedule_id: str, request_data: CreateTimeBlockRequest) -> ScheduleTimeBlock:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        block = ScheduleTimeBlock(
            schedule_id=schedule.id,
            title=request_data.title,
            description=request_data.description,
            category=request_data.category or "Deep Work",
            color=request_data.color or "#6366F1",
            start_time=request_data.startTime,
            end_time=request_data.endTime,
            duration_minutes=request_data.durationMinutes if request_data.durationMinutes is not None else 30,
            status=request_data.status or "planned",
            is_carry_forward=request_data.isCarryForward or False,
            linked_topic_id=request_data.linkedTopicId,
            linked_task_id=request_data.linkedTaskId,
            display_order=request_data.displayOrder or 0
        )
        db.add(block)
        db.flush()

        if request_data.checklist:
            for idx, chk in enumerate(request_data.checklist):
                c_title = chk if isinstance(chk, str) else chk.title
                c_order = idx if isinstance(chk, str) else (chk.displayOrder or idx)
                item = TimeBlockChecklistItem(
                    block_id=block.id,
                    title=c_title,
                    display_order=c_order
                )
                db.add(item)

        db.commit()
        db.refresh(block)
        self.recalculate_schedule_metrics(db, schedule)
        return block

    def update_time_block_status(self, db: Session, user_id: str, schedule_id: str, block_id: str, status_val: str) -> ScheduleTimeBlock:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        block = db.query(ScheduleTimeBlock).filter(ScheduleTimeBlock.id == block_id, ScheduleTimeBlock.schedule_id == schedule_id).first()
        if not block:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BLOCK_NOT_FOUND", "message": "Time block not found."})

        block.status = status_val
        db.add(block)
        db.commit()
        db.refresh(block)
        self.recalculate_schedule_metrics(db, schedule)
        return block

    def carry_forward_time_block(self, db: Session, user_id: str, schedule_id: str, block_id: str) -> Dict[str, Any]:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        block = db.query(ScheduleTimeBlock).filter(ScheduleTimeBlock.id == block_id, ScheduleTimeBlock.schedule_id == schedule_id).first()
        if not block:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BLOCK_NOT_FOUND", "message": "Time block not found."})

        block.status = "carried_forward"
        db.add(block)

        # Get or create tomorrow's schedule
        tomorrow_date = schedule.schedule_date + timedelta(days=1)
        tomorrow_schedule = db.query(DailySchedule).filter(
            DailySchedule.user_id == user_id,
            DailySchedule.schedule_date == tomorrow_date
        ).first()

        if not tomorrow_schedule:
            tomorrow_schedule = DailySchedule(
                user_id=user_id,
                schedule_date=tomorrow_date,
                status="active"
            )
            db.add(tomorrow_schedule)
            db.flush()

        new_block = ScheduleTimeBlock(
            schedule_id=tomorrow_schedule.id,
            title=block.title,
            description=block.description,
            category=block.category,
            color=block.color,
            start_time=block.start_time,
            end_time=block.end_time,
            duration_minutes=block.duration_minutes,
            status="planned",
            is_carry_forward=True,
            linked_topic_id=block.linked_topic_id,
            linked_task_id=block.linked_task_id,
            display_order=block.display_order
        )
        db.add(new_block)
        db.flush()

        for c in block.checklist:
            new_chk = TimeBlockChecklistItem(
                block_id=new_block.id,
                title=c.title,
                completed=False,
                display_order=c.display_order
            )
            db.add(new_chk)

        db.commit()
        self.recalculate_schedule_metrics(db, schedule)
        self.recalculate_schedule_metrics(db, tomorrow_schedule)

        return {
            "success": True,
            "message": "Time block carried forward to tomorrow's schedule.",
            "targetScheduleDate": tomorrow_date.isoformat()
        }

    def delete_time_block(self, db: Session, user_id: str, schedule_id: str, block_id: str) -> bool:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        block = db.query(ScheduleTimeBlock).filter(ScheduleTimeBlock.id == block_id, ScheduleTimeBlock.schedule_id == schedule_id).first()
        if not block:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BLOCK_NOT_FOUND", "message": "Time block not found."})

        db.delete(block)
        db.commit()
        self.recalculate_schedule_metrics(db, schedule)
        return True

    # ==========================================
    # 📌 3. ROUTINE OPERATIONS
    # ==========================================

    def add_routine_item(self, db: Session, user_id: str, schedule_id: str, request_data: CreateRoutineItemRequest) -> DailyRoutineItem:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        item = DailyRoutineItem(
            schedule_id=schedule.id,
            title=request_data.title,
            routine_type=request_data.routineType or "morning",
            display_order=request_data.displayOrder or 0
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        self.recalculate_schedule_metrics(db, schedule)
        return item

    def toggle_routine_item(self, db: Session, user_id: str, schedule_id: str, routine_id: str) -> bool:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        item = db.query(DailyRoutineItem).filter(DailyRoutineItem.id == routine_id, DailyRoutineItem.schedule_id == schedule_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "ROUTINE_NOT_FOUND", "message": "Routine item not found."})

        item.completed = not item.completed
        db.add(item)
        db.commit()
        self.recalculate_schedule_metrics(db, schedule)
        return item.completed

    def delete_routine_item(self, db: Session, user_id: str, schedule_id: str, routine_id: str) -> bool:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        item = db.query(DailyRoutineItem).filter(DailyRoutineItem.id == routine_id, DailyRoutineItem.schedule_id == schedule_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "ROUTINE_NOT_FOUND", "message": "Routine item not found."})

        db.delete(item)
        db.commit()
        self.recalculate_schedule_metrics(db, schedule)
        return True

    # ==========================================
    # 📌 4. REFLECTION OPERATIONS
    # ==========================================

    def save_reflection(self, db: Session, user_id: str, schedule_id: str, request_data: SaveReflectionRequest) -> DailyReflection:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        reflection = db.query(DailyReflection).filter(DailyReflection.schedule_id == schedule_id).first()

        if not reflection:
            reflection = DailyReflection(
                schedule_id=schedule.id,
                user_id=user_id,
                day_rating=request_data.dayRating or 5,
                wins_notes=request_data.winsNotes,
                blockers_notes=request_data.blockersNotes,
                general_notes=request_data.generalNotes
            )
        else:
            if request_data.dayRating is not None:
                reflection.day_rating = request_data.dayRating
            if request_data.winsNotes is not None:
                reflection.wins_notes = request_data.winsNotes
            if request_data.blockersNotes is not None:
                reflection.blockers_notes = request_data.blockersNotes
            if request_data.generalNotes is not None:
                reflection.general_notes = request_data.generalNotes

        db.add(reflection)
        db.commit()
        db.refresh(reflection)
        return reflection

    # ==========================================
    # 📌 5. ANALYTICS
    # ==========================================

    def get_weekly_analytics(self, db: Session, user_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=6)

        schedules = db.query(DailySchedule).filter(
            DailySchedule.user_id == user_id,
            DailySchedule.schedule_date >= start_date,
            DailySchedule.schedule_date <= end_date
        ).all()

        total_focus_mins = sum(s.completed_focus_minutes or 0 for s in schedules)
        avg_focus_mins = int(round(total_focus_mins / len(schedules))) if len(schedules) > 0 else 0
        avg_sched_progress = int(round(sum(s.schedule_progress or 0 for s in schedules) / len(schedules))) if len(schedules) > 0 else 0
        avg_rout_progress = int(round(sum(s.routine_progress or 0 for s in schedules) / len(schedules))) if len(schedules) > 0 else 0

        # Category breakdown of completed focus blocks
        category_mins: Dict[str, float] = {}
        schedule_ids = [s.id for s in schedules]
        if schedule_ids:
            blocks = db.query(ScheduleTimeBlock).filter(
                ScheduleTimeBlock.schedule_id.in_(schedule_ids),
                ScheduleTimeBlock.status == "completed"
            ).all()

            for b in blocks:
                cat = b.category or "Deep Work"
                category_mins[cat] = category_mins.get(cat, 0.0) + ((b.duration_minutes or 0) / 60.0)

        daily_scores = [
            {
                "date": s.schedule_date.isoformat(),
                "focusMinutes": s.completed_focus_minutes,
                "progress": s.schedule_progress
            }
            for s in schedules
        ]

        return {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "totalFocusHours": round(total_focus_mins / 60.0, 1),
            "averageDailyFocusMinutes": avg_focus_mins,
            "averageScheduleProgress": avg_sched_progress,
            "averageRoutineProgress": avg_rout_progress,
            "categoryBreakdown": category_mins,
            "dailyCompletionScores": daily_scores
        }

    # ==========================================
    # 📌 6. DUAL-MODE RAW JSON OVERWRITE & EXPORT
    # ==========================================

    def update_raw_json(self, db: Session, user_id: str, schedule_id: str, request_data: RawScheduleJsonPayloadRequest) -> DailySchedule:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        raw = request_data.jsonPayload

        if isinstance(raw, str):
            try:
                raw_dict = json.loads(raw)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "INVALID_PAYLOAD", "message": f"Malformed JSON payload: {str(e)}"}
                )
        elif isinstance(raw, dict):
            raw_dict = raw
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PAYLOAD", "message": "Payload must be a JSON string or object."}
            )

        if "moodScore" in raw_dict:
            schedule.mood_score = raw_dict.get("moodScore", 3)
        if "energyLevel" in raw_dict:
            schedule.energy_level = raw_dict.get("energyLevel", 3)
        if "focusGoalMinutes" in raw_dict:
            schedule.focus_goal_minutes = raw_dict.get("focusGoalMinutes", 180)

        db.add(schedule)

        # Overwrite time blocks & routines if provided in raw payload
        if "timeBlocks" in raw_dict:
            db.query(ScheduleTimeBlock).filter(ScheduleTimeBlock.schedule_id == schedule.id).delete(synchronize_session=False)
            for idx, b_item in enumerate(raw_dict["timeBlocks"]):
                block = ScheduleTimeBlock(
                    schedule_id=schedule.id,
                    title=b_item.get("title", f"Time Block {idx+1}"),
                    description=b_item.get("description"),
                    category=b_item.get("category", "Deep Work"),
                    color=b_item.get("color", "#6366F1"),
                    start_time=b_item.get("startTime", "09:00"),
                    end_time=b_item.get("endTime", "10:00"),
                    duration_minutes=int(b_item.get("durationMinutes", 60)),
                    status=b_item.get("status", "planned"),
                    is_carry_forward=b_item.get("isCarryForward", False),
                    display_order=b_item.get("displayOrder", idx)
                )
                db.add(block)
                db.flush()

                chk_list = b_item.get("checklist", [])
                if isinstance(chk_list, list):
                    for chk_idx, c_el in enumerate(chk_list):
                        c_title = c_el if isinstance(c_el, str) else c_el.get("title", f"Task {chk_idx+1}")
                        c_completed = False if isinstance(c_el, str) else c_el.get("completed", False)
                        chk_obj = TimeBlockChecklistItem(
                            block_id=block.id,
                            title=c_title,
                            completed=c_completed,
                            display_order=chk_idx
                        )
                        db.add(chk_obj)

        if "routines" in raw_dict:
            db.query(DailyRoutineItem).filter(DailyRoutineItem.schedule_id == schedule.id).delete(synchronize_session=False)
            for idx, r_item in enumerate(raw_dict["routines"]):
                r_obj = DailyRoutineItem(
                    schedule_id=schedule.id,
                    title=r_item.get("title", f"Routine {idx+1}"),
                    routine_type=r_item.get("routineType", "morning"),
                    completed=r_item.get("completed", False),
                    display_order=r_item.get("displayOrder", idx)
                )
                db.add(r_obj)

        db.commit()
        db.refresh(schedule)
        self.recalculate_schedule_metrics(db, schedule)
        return schedule

    def export_raw_json(self, db: Session, user_id: str, schedule_id: str) -> Dict[str, Any]:
        schedule = self.get_user_schedule_or_404(db, user_id, schedule_id)
        self.recalculate_schedule_metrics(db, schedule)

        blocks = db.query(ScheduleTimeBlock).filter(ScheduleTimeBlock.schedule_id == schedule.id).order_by(ScheduleTimeBlock.start_time).all()
        routines = db.query(DailyRoutineItem).filter(DailyRoutineItem.schedule_id == schedule.id).order_by(DailyRoutineItem.display_order).all()

        blocks_export = [
            {
                "title": b.title,
                "category": b.category,
                "startTime": b.start_time,
                "endTime": b.end_time,
                "durationMinutes": b.duration_minutes,
                "status": b.status,
                "checklist": [{"title": c.title, "completed": c.completed} for c in b.checklist]
            }
            for b in blocks
        ]

        routines_export = [
            {
                "title": r.title,
                "routineType": r.routine_type,
                "completed": r.completed
            }
            for r in routines
        ]

        return {
            "scheduleDate": schedule.schedule_date.isoformat(),
            "moodScore": schedule.mood_score,
            "energyLevel": schedule.energy_level,
            "focusGoalMinutes": schedule.focus_goal_minutes,
            "completedFocusMinutes": schedule.completed_focus_minutes,
            "timeBlocks": blocks_export,
            "routines": routines_export
        }


schedule_service = ScheduleService()
