from datetime import UTC, datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models.practice import TaskAssignment


def utc(value):
    """SQLite drops timezone metadata; stored dates are UTC."""
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def require_open_task(task):
    now = datetime.now(UTC)
    if task.status != "PUBLISHED" or (task.start_at and now < utc(task.start_at)) or (task.due_at and now > utc(task.due_at) and not task.allow_late):
        raise HTTPException(409, "Task is not open")


def require_assignment(db, task, student_id):
    if not task or not db.scalar(select(TaskAssignment).where(TaskAssignment.task_id == task.id, TaskAssignment.student_id == student_id)):
        raise HTTPException(404, "Task not found")
