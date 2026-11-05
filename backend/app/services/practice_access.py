"""Single source of truth for a student's currently open teaching task."""
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models.case import CaseVersion
from app.models.practice import Task, TaskAssignment
from app.models.user import User
from app.services.publication import require_teaching_version, utc


def require_open_task(db, task_id: str, user: User, version_id: str | None = None):
    """Validate identity, assignment, schedule and teaching publication on every access."""
    if not user.is_active or "STUDENT" not in {role.code for role in user.roles}:
        raise HTTPException(403, "Student role is required")
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None or (version_id is not None and task.case_version_id != version_id):
        raise HTTPException(404, "Task not found")
    assignment = db.scalar(select(TaskAssignment).where(TaskAssignment.task_id == task.id, TaskAssignment.student_id == user.id))
    if assignment is None:
        raise HTTPException(404, "Task not found")
    now, start, due = datetime.now(UTC), utc(task.start_at), utc(task.due_at)
    if task.status != "PUBLISHED" or (start is not None and now < start) or (due is not None and now > due and not task.allow_late):
        raise HTTPException(409, "Task is not currently open")
    version = db.scalar(select(CaseVersion).where(CaseVersion.id == task.case_version_id))
    copy = require_teaching_version(db, version)
    return task, version, copy
