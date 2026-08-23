import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    LearningSessionLog,
    LearningSubtopic,
    LearningTopic,
    SubtopicChecklistItem
)
from app.schemas.learning_schemas import (
    CreateRoadmapRequest,
    CreateSessionLogRequest,
    CreateSubtopicSchema,
    RawJsonPayloadRequest,
    UpdateRoadmapRequest,
    UpdateSubtopicRequest
)

logger = logging.getLogger("pulse.learning_service")


class LearningService:
    """Service layer executing business logic for User-Scoped Learning Roadmaps."""

    def _get_topic_for_user(self, db: Session, topic_id: str, user_id: str) -> LearningTopic:
        """Fetch roadmap topic and verify user ownership authorization."""
        topic = db.query(LearningTopic).filter(
            LearningTopic.id == topic_id,
            LearningTopic.user_id == user_id
        ).first()

        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ROADMAP_NOT_FOUND", "message": "Learning roadmap not found or access denied."}
            )
        return topic

    def _get_subtopic_for_user(self, db: Session, topic_id: str, subtopic_id: str, user_id: str) -> LearningSubtopic:
        """Fetch subtopic module and verify parent roadmap user ownership authorization."""
        topic = self._get_topic_for_user(db, topic_id, user_id)
        subtopic = db.query(LearningSubtopic).filter(
            LearningSubtopic.id == subtopic_id,
            LearningSubtopic.topic_id == topic.id
        ).first()

        if not subtopic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SUBTOPIC_NOT_FOUND", "message": "Subtopic module not found."}
            )
        return subtopic

    def recalculate_topic_progress(self, db: Session, topic_id: str) -> None:
        """Recalculate topic progress %, estimated remaining time, and current item title."""
        topic = db.query(LearningTopic).filter(LearningTopic.id == topic_id).first()
        if not topic:
            return

        subtopics = db.query(LearningSubtopic).filter(LearningSubtopic.topic_id == topic_id).order_by(LearningSubtopic.display_order).all()
        total_items = len(subtopics)
        completed_items = sum(1 for s in subtopics if s.completed)
        progress = int((completed_items / total_items) * 100) if total_items > 0 else 0

        total_est_minutes = sum(s.est_minutes for s in subtopics)
        est_minutes_remaining = sum(s.est_minutes for s in subtopics if not s.completed)

        pending_subtopics = [s for s in subtopics if not s.completed]
        current_item_title = pending_subtopics[0].title if pending_subtopics else (subtopics[-1].title if subtopics else None)

        topic.total_items = total_items
        topic.completed_items = completed_items
        topic.progress = progress
        topic.total_est_minutes = total_est_minutes
        topic.est_minutes_remaining = est_minutes_remaining
        topic.current_item_title = current_item_title

        db.commit()

    def get_user_roadmaps(self, db: Session, user_id: str, category: Optional[str] = None) -> List[LearningTopic]:
        """Fetch all roadmaps for the authenticated user."""
        query = db.query(LearningTopic).filter(LearningTopic.user_id == user_id)
        if category:
            query = query.filter(LearningTopic.category == category)
        return query.order_by(LearningTopic.created_at.desc()).all()

    def create_roadmap(self, db: Session, user_id: str, request_data: CreateRoadmapRequest) -> LearningTopic:
        """Create new user-scoped learning roadmap via visual form input."""
        topic = LearningTopic(
            user_id=user_id,
            title=request_data.title,
            category=request_data.category or "Software Engineering",
            icon=request_data.icon or "BookOpen",
            progress=0,
            total_items=0,
            completed_items=0,
            est_minutes_remaining=0,
            total_est_minutes=0
        )
        db.add(topic)
        db.flush()

        if request_data.subtopics:
            for idx, sub_req in enumerate(request_data.subtopics):
                subtopic = LearningSubtopic(
                    topic_id=topic.id,
                    title=sub_req.title,
                    description=sub_req.description,
                    est_minutes=sub_req.estMinutes or 30,
                    completed=False,
                    display_order=idx
                )
                db.add(subtopic)
                db.flush()

                if sub_req.checklist:
                    for c_idx, chk_item in enumerate(sub_req.checklist):
                        chk_title = chk_item if isinstance(chk_item, str) else chk_item.title
                        checklist_record = SubtopicChecklistItem(
                            subtopic_id=subtopic.id,
                            title=chk_title,
                            completed=False,
                            display_order=c_idx
                        )
                        db.add(checklist_record)

        db.commit()
        self.recalculate_topic_progress(db, topic.id)
        db.refresh(topic)
        return topic

    def get_roadmap_detail(self, db: Session, topic_id: str, user_id: str) -> LearningTopic:
        """Get detailed inner roadmap content, subtopics, micro-checklists, and session logs."""
        topic = self._get_topic_for_user(db, topic_id, user_id)
        return topic

    def update_roadmap(self, db: Session, topic_id: str, user_id: str, request_data: UpdateRoadmapRequest) -> LearningTopic:
        """Visual Edit roadmap metadata (title, category, icon)."""
        topic = self._get_topic_for_user(db, topic_id, user_id)

        if request_data.title:
            topic.title = request_data.title
        if request_data.category:
            topic.category = request_data.category
        if request_data.icon:
            topic.icon = request_data.icon

        db.commit()
        db.refresh(topic)
        return topic

    def update_raw_json(self, db: Session, topic_id: str, user_id: str, raw_json_str: str) -> LearningTopic:
        """Overwrite/Import full inner roadmap structure using raw JSON string payload."""
        topic = self._get_topic_for_user(db, topic_id, user_id)

        try:
            payload = json.loads(raw_json_str)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_JSON_PAYLOAD", "message": f"Malformed raw JSON payload: {str(e)}"}
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_JSON_FORMAT", "message": "Raw JSON payload must be a JSON object."}
            )

        if "title" in payload and payload["title"]:
            topic.title = str(payload["title"])
        if "category" in payload and payload["category"]:
            topic.category = str(payload["category"])
        if "icon" in payload and payload["icon"]:
            topic.icon = str(payload["icon"])

        # Delete existing subtopics and inner checklist items
        db.query(LearningSubtopic).filter(LearningSubtopic.topic_id == topic.id).delete()
        db.flush()

        raw_subtopics = payload.get("subtopics", [])
        if isinstance(raw_subtopics, list):
            for idx, s_data in enumerate(raw_subtopics):
                if not isinstance(s_data, dict):
                    continue
                subtopic = LearningSubtopic(
                    topic_id=topic.id,
                    title=str(s_data.get("title", f"Subtopic {idx + 1}")),
                    description=str(s_data.get("description", "")) if s_data.get("description") else None,
                    est_minutes=int(s_data.get("estMinutes") or s_data.get("est_minutes") or 30),
                    completed=bool(s_data.get("completed", False)),
                    display_order=idx
                )
                db.add(subtopic)
                db.flush()

                raw_checklist = s_data.get("checklist", [])
                if isinstance(raw_checklist, list):
                    for c_idx, c_data in enumerate(raw_checklist):
                        if isinstance(c_data, str):
                            chk_title = c_data
                            chk_completed = False
                        elif isinstance(c_data, dict):
                            chk_title = str(c_data.get("title", f"Item {c_idx + 1}"))
                            chk_completed = bool(c_data.get("completed", False))
                        else:
                            continue

                        checklist_record = SubtopicChecklistItem(
                            subtopic_id=subtopic.id,
                            title=chk_title,
                            completed=chk_completed,
                            display_order=c_idx
                        )
                        db.add(checklist_record)

        db.commit()
        self.recalculate_topic_progress(db, topic.id)
        db.refresh(topic)
        return topic

    def delete_roadmap(self, db: Session, topic_id: str, user_id: str) -> None:
        """Delete user roadmap and cascade delete all subtopics and checklist items."""
        topic = self._get_topic_for_user(db, topic_id, user_id)
        db.delete(topic)
        db.commit()

    def export_roadmap_json(self, db: Session, topic_id: str, user_id: str) -> Dict[str, Any]:
        """Export full inner roadmap hierarchy as JSON payload object."""
        topic = self._get_topic_for_user(db, topic_id, user_id)
        subtopics_data = []

        for sub in topic.subtopics:
            checklist_data = [
                {"title": item.title, "completed": item.completed}
                for item in sub.checklist_items
            ]
            subtopics_data.append({
                "title": sub.title,
                "description": sub.description,
                "estMinutes": sub.est_minutes,
                "completed": sub.completed,
                "checklist": checklist_data
            })

        return {
            "title": topic.title,
            "category": topic.category,
            "icon": topic.icon,
            "progress": topic.progress,
            "estMinutesRemaining": topic.est_minutes_remaining,
            "totalEstMinutes": topic.total_est_minutes,
            "subtopics": subtopics_data
        }

    def toggle_subtopic(self, db: Session, topic_id: str, subtopic_id: str, user_id: str) -> LearningSubtopic:
        """Toggle completion state of a subtopic module and recalculate roadmap progress."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)
        subtopic.completed = not subtopic.completed

        # If subtopic completed, optionally mark all inner checklist items as completed
        if subtopic.completed:
            for chk in subtopic.checklist_items:
                chk.completed = True

        db.commit()
        self.recalculate_topic_progress(db, topic_id)
        db.refresh(subtopic)
        return subtopic

    def update_subtopic(self, db: Session, topic_id: str, subtopic_id: str, user_id: str, request_data: UpdateSubtopicRequest) -> LearningSubtopic:
        """Update subtopic title, description, and estimated minutes."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)

        if request_data.title is not None:
            subtopic.title = request_data.title
        if request_data.description is not None:
            subtopic.description = request_data.description
        if request_data.estMinutes is not None:
            subtopic.est_minutes = request_data.estMinutes

        db.commit()
        self.recalculate_topic_progress(db, topic_id)
        db.refresh(subtopic)
        return subtopic

    def delete_subtopic(self, db: Session, topic_id: str, subtopic_id: str, user_id: str) -> None:
        """Delete subtopic module and recalculate progress."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)
        db.delete(subtopic)
        db.commit()
        self.recalculate_topic_progress(db, topic_id)

    def add_checklist_item(self, db: Session, topic_id: str, subtopic_id: str, user_id: str, title: str) -> SubtopicChecklistItem:
        """Add new micro-checklist requirement item under target subtopic."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)

        max_order = len(subtopic.checklist_items)
        chk_item = SubtopicChecklistItem(
            subtopic_id=subtopic.id,
            title=title,
            completed=False,
            display_order=max_order
        )
        db.add(chk_item)
        db.commit()
        db.refresh(chk_item)
        return chk_item

    def toggle_checklist_item(self, db: Session, topic_id: str, subtopic_id: str, item_id: str, user_id: str) -> SubtopicChecklistItem:
        """Toggle completion status of micro-checklist item."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)
        chk_item = db.query(SubtopicChecklistItem).filter(
            SubtopicChecklistItem.id == item_id,
            SubtopicChecklistItem.subtopic_id == subtopic.id
        ).first()

        if not chk_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CHECKLIST_ITEM_NOT_FOUND", "message": "Micro-checklist item not found."}
            )

        chk_item.completed = not chk_item.completed
        db.commit()
        db.refresh(chk_item)
        return chk_item

    def update_checklist_item(self, db: Session, topic_id: str, subtopic_id: str, item_id: str, user_id: str, title: str) -> SubtopicChecklistItem:
        """Update micro-checklist item title."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)
        chk_item = db.query(SubtopicChecklistItem).filter(
            SubtopicChecklistItem.id == item_id,
            SubtopicChecklistItem.subtopic_id == subtopic.id
        ).first()

        if not chk_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CHECKLIST_ITEM_NOT_FOUND", "message": "Micro-checklist item not found."}
            )

        chk_item.title = title
        db.commit()
        db.refresh(chk_item)
        return chk_item

    def delete_checklist_item(self, db: Session, topic_id: str, subtopic_id: str, item_id: str, user_id: str) -> None:
        """Delete micro-checklist requirement item."""
        subtopic = self._get_subtopic_for_user(db, topic_id, subtopic_id, user_id)
        chk_item = db.query(SubtopicChecklistItem).filter(
            SubtopicChecklistItem.id == item_id,
            SubtopicChecklistItem.subtopic_id == subtopic.id
        ).first()

        if chk_item:
            db.delete(chk_item)
            db.commit()

    def log_session(self, db: Session, topic_id: str, user_id: str, request_data: CreateSessionLogRequest) -> LearningSessionLog:
        """Log focus session for a learning roadmap."""
        topic = self._get_topic_for_user(db, topic_id, user_id)

        session_log = LearningSessionLog(
            user_id=user_id,
            topic_id=topic.id,
            subtopic_id=request_data.subtopicId,
            duration_minutes=request_data.durationMinutes,
            notes=request_data.notes
        )
        db.add(session_log)
        db.commit()
        db.refresh(session_log)
        return session_log


learning_service = LearningService()
