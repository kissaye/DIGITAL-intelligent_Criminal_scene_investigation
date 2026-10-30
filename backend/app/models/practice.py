from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

def uid(): return str(uuid4())
class Course(Base):
    __tablename__="courses"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name: Mapped[str]=mapped_column(String(200)); created_by: Mapped[int]=mapped_column(ForeignKey("users.id"))
class Class(Base):
    __tablename__="classes"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); course_id: Mapped[str]=mapped_column(ForeignKey("courses.id")); name: Mapped[str]=mapped_column(String(200))
class ClassMember(Base):
    __tablename__="class_members"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); class_id: Mapped[str]=mapped_column(ForeignKey("classes.id",ondelete="CASCADE")); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); __table_args__=(UniqueConstraint("class_id","user_id"),)
class Task(Base):
    __tablename__="tasks"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); title: Mapped[str]=mapped_column(String(200)); instructions: Mapped[str|None]=mapped_column(Text); case_version_id: Mapped[str]=mapped_column(ForeignKey("case_versions.id")); start_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); allow_late: Mapped[bool]=mapped_column(Boolean,default=False); status: Mapped[str]=mapped_column(String(20),default="PUBLISHED"); report_template: Mapped[dict|None]=mapped_column(JSON); created_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class TaskAssignment(Base):
    __tablename__="task_assignments"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); task_id: Mapped[str]=mapped_column(ForeignKey("tasks.id",ondelete="CASCADE")); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); __table_args__=(UniqueConstraint("task_id","student_id"),)
class Submission(Base):
    __tablename__="submissions"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); task_id: Mapped[str]=mapped_column(ForeignKey("tasks.id",ondelete="CASCADE")); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); status: Mapped[str]=mapped_column(String(20),default="DRAFT"); report_content: Mapped[dict|None]=mapped_column(JSON); submitted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); version_no: Mapped[int]=mapped_column(Integer,default=1); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now()); __table_args__=(UniqueConstraint("task_id","student_id","version_no"),)
class SubmissionMark(Base):
    __tablename__="submission_marks"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); submission_id: Mapped[str]=mapped_column(ForeignKey("submissions.id",ondelete="CASCADE")); geometry: Mapped[dict]=mapped_column(JSON); title: Mapped[str]=mapped_column(String(200)); description: Mapped[str|None]=mapped_column(Text); viewer_state: Mapped[dict|None]=mapped_column(JSON)
class SubmissionMeasurement(Base):
    __tablename__="submission_measurements"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); submission_id: Mapped[str]=mapped_column(ForeignKey("submissions.id",ondelete="CASCADE")); start_point: Mapped[dict]=mapped_column(JSON); end_point: Mapped[dict]=mapped_column(JSON); distance: Mapped[float]=mapped_column(); viewer_state: Mapped[dict|None]=mapped_column(JSON)
