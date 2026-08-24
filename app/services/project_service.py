import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Project,
    ProjectAttachment,
    ProjectMilestone,
    ProjectTask,
    ProjectTimeLog,
    TaskChecklistItem
)
from app.schemas.project_schemas import (
    CreateAttachmentRequest,
    CreateChecklistItemInput,
    CreateChecklistItemRequest,
    CreateMilestoneRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    CreateTimeLogRequest,
    RawJsonPayloadRequest,
    UpdateChecklistItemRequest,
    UpdateMilestoneRequest,
    UpdateProjectMetadataRequest,
    UpdateTaskStatusRequest
)

logger = logging.getLogger("pulse.services.project")


class ProjectService:

    # ==========================================
    # 📌 HELPER METHODS
    # ==========================================

    def get_user_project_or_404(self, db: Session, user_id: str, project_id: str) -> Project:
        """Fetch project belonging to user or raise HTTP 404."""
        project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROJECT_NOT_FOUND", "message": "The requested project ID does not exist or does not belong to you."}
            )
        return project

    def recalculate_project_metrics(self, db: Session, project: Project) -> None:
        """Recalculate project aggregated fields (progress, total_tasks, completed_tasks, hours)."""
        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.id).all()
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == "completed")
        progress = int(round((completed_tasks / total_tasks) * 100)) if total_tasks > 0 else 0
        total_est_hours = sum(t.est_hours or 0.0 for t in tasks)

        # Calculate total spent hours from project_time_logs
        spent_hours_query = db.query(func.sum(ProjectTimeLog.duration_hours)).filter(ProjectTimeLog.project_id == project.id).scalar()
        spent_hours = float(spent_hours_query or 0.0)
        remaining_hours = max(0.0, total_est_hours - spent_hours)

        project.total_tasks = total_tasks
        project.completed_tasks = completed_tasks
        project.progress = progress
        project.total_est_hours = total_est_hours
        project.spent_hours = spent_hours
        project.remaining_hours = remaining_hours
        db.add(project)
        db.commit()
        db.refresh(project)

    # ==========================================
    # 📌 1. PROJECT CRUD operations
    # ==========================================

    def get_user_projects(
        self,
        db: Session,
        user_id: str,
        status_filter: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Project]:
        query = db.query(Project).filter(Project.user_id == user_id)
        if status_filter:
            query = query.filter(Project.status == status_filter)
        if category:
            query = query.filter(Project.category == category)
        if priority:
            query = query.filter(Project.priority == priority)
        if search:
            query = query.filter(
                (Project.title.ilike(f"%{search}%")) | (Project.description.ilike(f"%{search}%"))
            )
        return query.order_by(Project.created_at.desc()).all()

    def create_project(self, db: Session, user_id: str, request_data: CreateProjectRequest) -> Project:
        project = Project(
            user_id=user_id,
            title=request_data.title,
            description=request_data.description,
            category=request_data.category or "Software Engineering",
            icon=request_data.icon or "Folder",
            color=request_data.color or "#3B82F6",
            priority=request_data.priority or "medium",
            start_date=request_data.startDate,
            target_date=request_data.targetDate
        )
        db.add(project)
        db.flush()

        milestone_map = {}
        if request_data.milestones:
            for idx, ms_input in enumerate(request_data.milestones):
                ms = ProjectMilestone(
                    project_id=project.id,
                    title=ms_input.title,
                    description=ms_input.description,
                    status=ms_input.status or "pending",
                    target_date=ms_input.targetDate,
                    display_order=ms_input.displayOrder if ms_input.displayOrder is not None else idx
                )
                db.add(ms)
                db.flush()
                milestone_map[ms_input.title] = ms.id

        if request_data.tasks:
            for idx, task_input in enumerate(request_data.tasks):
                milestone_id = task_input.milestoneId
                if not milestone_id:
                    if task_input.milestoneTitle and task_input.milestoneTitle in milestone_map:
                        milestone_id = milestone_map[task_input.milestoneTitle]
                    elif task_input.title in milestone_map:
                        milestone_id = milestone_map[task_input.title]

                task = ProjectTask(
                    project_id=project.id,
                    milestone_id=milestone_id,
                    title=task_input.title,
                    description=task_input.description,
                    status=task_input.status or "todo",
                    priority=task_input.priority or "medium",
                    est_hours=task_input.estHours if task_input.estHours is not None else 1.0,
                    due_date=task_input.dueDate,
                    display_order=task_input.displayOrder if task_input.displayOrder is not None else idx
                )
                db.add(task)
                db.flush()

                if task_input.checklist:
                    for chk_idx, chk_item in enumerate(task_input.checklist):
                        chk_title = chk_item if isinstance(chk_item, str) else chk_item.title
                        chk_order = chk_idx if isinstance(chk_item, str) else (chk_item.displayOrder or chk_idx)
                        item = TaskChecklistItem(
                            task_id=task.id,
                            title=chk_title,
                            display_order=chk_order
                        )
                        db.add(item)

        db.commit()
        db.refresh(project)
        self.recalculate_project_metrics(db, project)
        return project

    def get_project_detail(self, db: Session, user_id: str, project_id: str) -> Project:
        project = self.get_user_project_or_404(db, user_id, project_id)
        self.recalculate_project_metrics(db, project)
        return project

    def get_project_card_summary(self, db: Session, user_id: str, project_id: str) -> Project:
        """Fetch lightweight top-level project card summary metadata."""
        project = self.get_user_project_or_404(db, user_id, project_id)
        self.recalculate_project_metrics(db, project)
        return project

    def get_project_milestones_summary(self, db: Session, user_id: str, project_id: str) -> List[ProjectMilestone]:
        """Fetch project milestones without heavy task checklist details."""
        project = self.get_user_project_or_404(db, user_id, project_id)
        return db.query(ProjectMilestone).filter(
            ProjectMilestone.project_id == project.id
        ).order_by(ProjectMilestone.display_order).all()

    def get_task_checklist(self, db: Session, user_id: str, project_id: str, task_id: str) -> List[TaskChecklistItem]:
        """Lazy fetch micro-checklist items for a project task."""
        project = self.get_user_project_or_404(db, user_id, project_id)
        task = db.query(ProjectTask).filter(
            ProjectTask.id == task_id,
            ProjectTask.project_id == project.id
        ).first()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TASK_NOT_FOUND", "message": "Project task not found."}
            )
        return db.query(TaskChecklistItem).filter(
            TaskChecklistItem.task_id == task.id
        ).order_by(TaskChecklistItem.display_order).all()

    def update_project_metadata(self, db: Session, user_id: str, project_id: str, request_data: UpdateProjectMetadataRequest) -> Project:
        project = self.get_user_project_or_404(db, user_id, project_id)
        if request_data.title is not None:
            project.title = request_data.title
        if request_data.description is not None:
            project.description = request_data.description
        if request_data.category is not None:
            project.category = request_data.category
        if request_data.icon is not None:
            project.icon = request_data.icon
        if request_data.color is not None:
            project.color = request_data.color
        if request_data.status is not None:
            project.status = request_data.status
        if request_data.priority is not None:
            project.priority = request_data.priority
        if request_data.startDate is not None:
            project.start_date = request_data.startDate
        if request_data.targetDate is not None:
            project.target_date = request_data.targetDate

        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    def delete_project(self, db: Session, user_id: str, project_id: str) -> bool:
        project = self.get_user_project_or_404(db, user_id, project_id)
        db.delete(project)
        db.commit()
        return True

    # ==========================================
    # 📌 2. MILESTONE OPERATIONS
    # ==========================================

    def create_milestone(self, db: Session, user_id: str, project_id: str, request_data: CreateMilestoneRequest) -> ProjectMilestone:
        project = self.get_user_project_or_404(db, user_id, project_id)
        milestone = ProjectMilestone(
            project_id=project.id,
            title=request_data.title,
            description=request_data.description,
            status=request_data.status or "pending",
            target_date=request_data.targetDate,
            display_order=request_data.displayOrder or 0
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone

    def update_milestone(self, db: Session, user_id: str, project_id: str, milestone_id: str, request_data: UpdateMilestoneRequest) -> ProjectMilestone:
        self.get_user_project_or_404(db, user_id, project_id)
        milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id, ProjectMilestone.project_id == project_id).first()
        if not milestone:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "MILESTONE_NOT_FOUND", "message": "Milestone not found."})

        if request_data.title is not None:
            milestone.title = request_data.title
        if request_data.description is not None:
            milestone.description = request_data.description
        if request_data.status is not None:
            milestone.status = request_data.status
        if request_data.targetDate is not None:
            milestone.target_date = request_data.targetDate
        if request_data.displayOrder is not None:
            milestone.display_order = request_data.displayOrder

        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone

    def delete_milestone(self, db: Session, user_id: str, project_id: str, milestone_id: str) -> bool:
        self.get_user_project_or_404(db, user_id, project_id)
        milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id, ProjectMilestone.project_id == project_id).first()
        if not milestone:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "MILESTONE_NOT_FOUND", "message": "Milestone not found."})

        db.delete(milestone)
        db.commit()
        return True

    # ==========================================
    # 📌 3. TASK OPERATIONS
    # ==========================================

    def create_task(self, db: Session, user_id: str, project_id: str, request_data: CreateTaskRequest) -> ProjectTask:
        project = self.get_user_project_or_404(db, user_id, project_id)
        task = ProjectTask(
            project_id=project.id,
            milestone_id=request_data.milestoneId,
            title=request_data.title,
            description=request_data.description,
            status=request_data.status or "todo",
            priority=request_data.priority or "medium",
            est_hours=request_data.estHours if request_data.estHours is not None else 1.0,
            due_date=request_data.dueDate,
            display_order=request_data.displayOrder or 0
        )
        db.add(task)
        db.flush()

        if request_data.checklist:
            for idx, chk in enumerate(request_data.checklist):
                chk_title = chk if isinstance(chk, str) else chk.title
                chk_order = idx if isinstance(chk, str) else (chk.displayOrder or idx)
                item = TaskChecklistItem(
                    task_id=task.id,
                    title=chk_title,
                    display_order=chk_order
                )
                db.add(item)

        db.commit()
        db.refresh(task)
        self.recalculate_project_metrics(db, project)
        return task

    def update_task_status(self, db: Session, user_id: str, project_id: str, task_id: str, request_data: UpdateTaskStatusRequest) -> ProjectTask:
        project = self.get_user_project_or_404(db, user_id, project_id)
        task = db.query(ProjectTask).filter(ProjectTask.id == task_id, ProjectTask.project_id == project_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "TASK_NOT_FOUND", "message": "Task not found."})

        task.status = request_data.status
        if request_data.displayOrder is not None:
            task.display_order = request_data.displayOrder

        db.add(task)
        db.commit()
        db.refresh(task)
        self.recalculate_project_metrics(db, project)
        return task

    def delete_task(self, db: Session, user_id: str, project_id: str, task_id: str) -> bool:
        project = self.get_user_project_or_404(db, user_id, project_id)
        task = db.query(ProjectTask).filter(ProjectTask.id == task_id, ProjectTask.project_id == project_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "TASK_NOT_FOUND", "message": "Task not found."})

        db.delete(task)
        db.commit()
        self.recalculate_project_metrics(db, project)
        return True

    # ==========================================
    # 📌 4. CHECKLIST OPERATIONS
    # ==========================================

    def add_checklist_item(self, db: Session, user_id: str, project_id: str, task_id: str, request_data: CreateChecklistItemRequest) -> TaskChecklistItem:
        self.get_user_project_or_404(db, user_id, project_id)
        task = db.query(ProjectTask).filter(ProjectTask.id == task_id, ProjectTask.project_id == project_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "TASK_NOT_FOUND", "message": "Task not found."})

        item = TaskChecklistItem(
            task_id=task.id,
            title=request_data.title,
            display_order=request_data.displayOrder or 0
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def toggle_checklist_item(self, db: Session, user_id: str, project_id: str, task_id: str, item_id: str) -> bool:
        self.get_user_project_or_404(db, user_id, project_id)
        item = db.query(TaskChecklistItem).join(ProjectTask).filter(
            TaskChecklistItem.id == item_id,
            TaskChecklistItem.task_id == task_id,
            ProjectTask.project_id == project_id
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CHECKLIST_ITEM_NOT_FOUND", "message": "Checklist item not found."})

        item.completed = not item.completed
        db.add(item)
        db.commit()
        return item.completed

    def update_checklist_item(self, db: Session, user_id: str, project_id: str, task_id: str, item_id: str, request_data: UpdateChecklistItemRequest) -> TaskChecklistItem:
        self.get_user_project_or_404(db, user_id, project_id)
        item = db.query(TaskChecklistItem).join(ProjectTask).filter(
            TaskChecklistItem.id == item_id,
            TaskChecklistItem.task_id == task_id,
            ProjectTask.project_id == project_id
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CHECKLIST_ITEM_NOT_FOUND", "message": "Checklist item not found."})

        item.title = request_data.title
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def delete_checklist_item(self, db: Session, user_id: str, project_id: str, task_id: str, item_id: str) -> bool:
        self.get_user_project_or_404(db, user_id, project_id)
        item = db.query(TaskChecklistItem).join(ProjectTask).filter(
            TaskChecklistItem.id == item_id,
            TaskChecklistItem.task_id == task_id,
            ProjectTask.project_id == project_id
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CHECKLIST_ITEM_NOT_FOUND", "message": "Checklist item not found."})

        db.delete(item)
        db.commit()
        return True

    # ==========================================
    # 📌 5. TIME SESSION LOGGING OPERATIONS
    # ==========================================

    def log_time(self, db: Session, user_id: str, project_id: str, request_data: CreateTimeLogRequest) -> ProjectTimeLog:
        project = self.get_user_project_or_404(db, user_id, project_id)
        if request_data.taskId:
            task = db.query(ProjectTask).filter(ProjectTask.id == request_data.taskId, ProjectTask.project_id == project_id).first()
            if not task:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "TASK_NOT_FOUND", "message": "Task not found."})
            task.spent_hours = float(task.spent_hours or 0.0) + request_data.durationHours
            db.add(task)

        time_log = ProjectTimeLog(
            project_id=project.id,
            task_id=request_data.taskId,
            user_id=user_id,
            duration_hours=request_data.durationHours,
            notes=request_data.notes
        )
        db.add(time_log)
        db.commit()
        db.refresh(time_log)
        self.recalculate_project_metrics(db, project)
        return time_log

    def get_time_logs(self, db: Session, user_id: str, project_id: str) -> List[ProjectTimeLog]:
        project = self.get_user_project_or_404(db, user_id, project_id)
        return db.query(ProjectTimeLog).filter(ProjectTimeLog.project_id == project.id).order_by(ProjectTimeLog.logged_at.desc()).all()

    # ==========================================
    # 📌 6. ATTACHMENT OPERATIONS
    # ==========================================

    def add_attachment(self, db: Session, user_id: str, project_id: str, request_data: CreateAttachmentRequest) -> ProjectAttachment:
        project = self.get_user_project_or_404(db, user_id, project_id)
        attachment = ProjectAttachment(
            project_id=project.id,
            name=request_data.name,
            url=request_data.url,
            file_type=request_data.fileType or "link",
            file_size_bytes=request_data.fileSizeBytes or 0
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        return attachment

    def delete_attachment(self, db: Session, user_id: str, project_id: str, attachment_id: str) -> bool:
        self.get_user_project_or_404(db, user_id, project_id)
        attachment = db.query(ProjectAttachment).filter(
            ProjectAttachment.id == attachment_id,
            ProjectAttachment.project_id == project_id
        ).first()
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "ATTACHMENT_NOT_FOUND", "message": "Attachment not found."})

        db.delete(attachment)
        db.commit()
        return True

    # ==========================================
    # 📌 7. ANALYTICS
    # ==========================================

    def get_analytics(self, db: Session, user_id: str, project_id: str) -> Dict[str, Any]:
        project = self.get_user_project_or_404(db, user_id, project_id)
        self.recalculate_project_metrics(db, project)

        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()

        task_breakdown = {
            "backlog": 0,
            "todo": 0,
            "in_progress": 0,
            "in_review": 0,
            "completed": 0
        }
        now_utc = datetime.now(timezone.utc)
        overdue_count = 0

        for t in tasks:
            st = t.status if t.status in task_breakdown else "todo"
            task_breakdown[st] += 1

            if t.status != "completed" and t.due_date:
                # Ensure naive/aware comparison safety
                due_dt = t.due_date if t.due_date.tzinfo else t.due_date.replace(tzinfo=timezone.utc)
                if due_dt < now_utc:
                    overdue_count += 1

        return {
            "projectId": project.id,
            "overallProgress": project.progress,
            "taskBreakdown": task_breakdown,
            "hoursSummary": {
                "totalEstHours": project.totalEstHours,
                "spentHours": project.spentHours,
                "remainingHours": project.remainingHours
            },
            "overdueTaskCount": overdue_count
        }

    # ==========================================
    # 📌 8. DUAL-MODE RAW JSON OVERWRITE & EXPORT
    # ==========================================

    def update_raw_json(self, db: Session, user_id: str, project_id: str, request_data: RawJsonPayloadRequest) -> Project:
        project = self.get_user_project_or_404(db, user_id, project_id)

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
                detail={"code": "INVALID_PAYLOAD", "message": "Payload must be a JSON string or JSON object."}
            )

        # Update Project properties if present
        if "title" in raw_dict and raw_dict["title"]:
            project.title = raw_dict["title"]
        if "description" in raw_dict:
            project.description = raw_dict.get("description")
        if "category" in raw_dict and raw_dict["category"]:
            project.category = raw_dict["category"]
        if "icon" in raw_dict:
            project.icon = raw_dict.get("icon")
        if "color" in raw_dict:
            project.color = raw_dict.get("color")
        if "status" in raw_dict:
            project.status = raw_dict.get("status")
        if "priority" in raw_dict:
            project.priority = raw_dict.get("priority")

        db.add(project)

        # Remove existing milestones and tasks if milestones or tasks present in JSON
        if "milestones" in raw_dict or "tasks" in raw_dict:
            db.query(ProjectTask).filter(ProjectTask.project_id == project.id).delete(synchronize_session=False)
            db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project.id).delete(synchronize_session=False)

        milestone_map = {}
        if "milestones" in raw_dict and isinstance(raw_dict["milestones"], list):
            for idx, ms_item in enumerate(raw_dict["milestones"]):
                ms = ProjectMilestone(
                    project_id=project.id,
                    title=ms_item.get("title", f"Milestone {idx+1}"),
                    description=ms_item.get("description"),
                    status=ms_item.get("status", "pending"),
                    display_order=ms_item.get("displayOrder", idx)
                )
                db.add(ms)
                db.flush()
                milestone_map[ms.title] = ms.id

        if "tasks" in raw_dict and isinstance(raw_dict["tasks"], list):
            for idx, task_item in enumerate(raw_dict["tasks"]):
                ms_id = task_item.get("milestoneId")
                if not ms_id and task_item.get("milestoneTitle") in milestone_map:
                    ms_id = milestone_map[task_item["milestoneTitle"]]

                task = ProjectTask(
                    project_id=project.id,
                    milestone_id=ms_id,
                    title=task_item.get("title", f"Task {idx+1}"),
                    description=task_item.get("description"),
                    status=task_item.get("status", "todo"),
                    priority=task_item.get("priority", "medium"),
                    est_hours=float(task_item.get("estHours", 1.0)),
                    spent_hours=float(task_item.get("spentHours", 0.0)),
                    display_order=task_item.get("displayOrder", idx)
                )
                db.add(task)
                db.flush()

                chk_list = task_item.get("checklist", [])
                if isinstance(chk_list, list):
                    for chk_idx, chk_el in enumerate(chk_list):
                        if isinstance(chk_el, str):
                            c_title = chk_el
                            c_completed = False
                        elif isinstance(chk_el, dict):
                            c_title = chk_el.get("title", f"Item {chk_idx+1}")
                            c_completed = chk_el.get("completed", False)
                        else:
                            continue

                        chk_obj = TaskChecklistItem(
                            task_id=task.id,
                            title=c_title,
                            completed=c_completed,
                            display_order=chk_idx
                        )
                        db.add(chk_obj)

        db.commit()
        db.refresh(project)
        self.recalculate_project_metrics(db, project)
        return project

    def export_raw_json(self, db: Session, user_id: str, project_id: str) -> Dict[str, Any]:
        project = self.get_user_project_or_404(db, user_id, project_id)
        self.recalculate_project_metrics(db, project)

        milestones = db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project.id).order_by(ProjectMilestone.display_order).all()
        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.id).order_by(ProjectTask.display_order).all()

        milestones_export = [
            {
                "title": m.title,
                "status": m.status,
                "targetDate": m.target_date.isoformat() if m.target_date else None
            }
            for m in milestones
        ]

        tasks_export = []
        for t in tasks:
            checklist = [
                {
                    "title": c.title,
                    "completed": c.completed
                }
                for c in t.checklist
            ]
            tasks_export.append({
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "estHours": t.est_hours,
                "checklist": checklist
            })

        return {
            "title": project.title,
            "description": project.description,
            "category": project.category,
            "icon": project.icon,
            "color": project.color,
            "priority": project.priority,
            "totalEstHours": project.total_est_hours,
            "milestones": milestones_export,
            "tasks": tasks_export
        }


project_service = ProjectService()
