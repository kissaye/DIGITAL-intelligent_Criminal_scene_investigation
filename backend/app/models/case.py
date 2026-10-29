from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def new_uuid() -> str:
    return str(uuid4())


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    internal_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, default="")
    teaching_title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    case_type: Mapped[str] = mapped_column(String(64), nullable=False, default="OTHER")
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, default="BEGINNER")
    course_tags: Mapped[list] = mapped_column(JSON(), nullable=False, default=list)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    desensitization_level: Mapped[str] = mapped_column(String(32), nullable=False, default="NONE")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by: Mapped["User"] = relationship(back_populates="created_cases")
    files: Mapped[list["File"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    versions: Mapped[list["CaseVersion"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    case: Mapped[Case] = relationship(back_populates="files")
    versions: Mapped[list["CaseVersion"]] = relationship(back_populates="source_file")


class CaseVersion(Base):
    __tablename__ = "case_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_file_id: Mapped[str] = mapped_column(ForeignKey("files.id", ondelete="RESTRICT"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    point_count: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    bounds: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
    viewer_manifest_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    case: Mapped[Case] = relationship(back_populates="versions")
    source_file: Mapped[File] = relationship(back_populates="versions")
    jobs: Mapped[list["Job"]] = relationship(back_populates="case_version", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="POINTCLOUD_CONVERSION")
    case_version_id: Mapped[str] = mapped_column(ForeignKey("case_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    progress: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    case_version: Mapped[CaseVersion] = relationship(back_populates="jobs")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    case_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    detail: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
