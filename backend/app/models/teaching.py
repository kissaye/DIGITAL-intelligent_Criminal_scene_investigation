from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.practice import uid


class TaskClass(Base):
    __tablename__ = "task_classes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"))
    __table_args__ = (UniqueConstraint("task_id", "class_id"),)


class RubricItem(Base):
    __tablename__ = "task_rubric_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    max_score: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("max_score > 0", name="ck_rubric_positive"),)


class SubmissionGrade(Base):
    __tablename__ = "submission_grades"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), unique=True)
    graded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    total_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("total_score >= 0", name="ck_grade_nonnegative"),)


class GradeItem(Base):
    __tablename__ = "submission_grade_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    grade_id: Mapped[str] = mapped_column(ForeignKey("submission_grades.id", ondelete="CASCADE"), index=True)
    rubric_item_id: Mapped[str] = mapped_column(ForeignKey("task_rubric_items.id"))
    score: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    comment: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("grade_id", "rubric_item_id"), CheckConstraint("score >= 0", name="ck_grade_item_nonnegative"))
