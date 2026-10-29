import hashlib
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_admin
from app.core.config import get_settings
from app.models.case import AuditLog, Case, CaseVersion, File, Job
from app.models.user import User
from app.schemas.case import CaseCreate, CaseData, CaseListData, FileData, JobData, VersionCreate, VersionData
from app.schemas.common import APIResponse
from app.services.conversion import run_conversion
from app.services.queue import get_queue

router = APIRouter(tags=["cases"])
settings = get_settings()
ALLOWED_SUFFIXES = {".las": "application/vnd.las", ".laz": "application/vnd.laz"}


def case_data(item: Case) -> CaseData:
    recent = max(item.files, key=lambda file: file.created_at, default=None)
    latest = max(item.versions, key=lambda version: version.created_at, default=None)
    return CaseData(id=item.id, internal_code=item.internal_code, teaching_title=item.teaching_title, case_type=item.case_type, difficulty=item.difficulty, course_tags=item.course_tags, valid_until=item.valid_until, desensitization_level=item.desensitization_level, file=FileData(id=recent.id, file_name=recent.original_name, file_size=recent.size_bytes) if recent else None, latest_version=version_data(latest) if latest else None, created_at=item.created_at)


def version_data(item: CaseVersion) -> VersionData:
    latest_job = max(item.jobs, key=lambda job: job.created_at, default=None)
    return VersionData(id=item.id, status=item.status, job_id=latest_job.id if latest_job else None, progress=latest_job.progress if latest_job else 0, point_count=item.point_count, bounds=item.bounds, failure_reason=item.error_message, created_at=item.created_at)


def job_data(item: Job) -> JobData:
    return JobData(id=item.id, type=item.type, status=item.status, progress=item.progress, version_id=item.case_version_id, failure_reason=item.error_message, created_at=item.created_at, started_at=item.started_at, finished_at=item.finished_at)


@router.post("/cases", response_model=APIResponse[CaseData], status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[CaseData]:
    item = Case(title=payload.teaching_title, description=payload.description, internal_code=payload.internal_code, teaching_title=payload.teaching_title, case_type=payload.case_type, difficulty=payload.difficulty, course_tags=payload.course_tags, valid_until=payload.valid_until, desensitization_level=payload.desensitization_level, created_by_id=admin.id)
    db.add(item)
    db.flush()
    db.add(AuditLog(action="CASE_CREATED", actor_id=admin.id, case_id=item.id))
    db.commit()
    db.refresh(item)
    return APIResponse(data=case_data(item), request_id=request_id)


@router.get("/cases", response_model=APIResponse[CaseListData])
def list_cases(admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[CaseListData]:
    items = db.scalars(select(Case).order_by(Case.created_at.desc())).all()
    return APIResponse(data=CaseListData(items=[case_data(item) for item in items], total=len(items)), request_id=request_id)


@router.get("/cases/{case_id}", response_model=APIResponse[CaseData])
def get_case(case_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[CaseData]:
    item = db.scalar(select(Case).where(Case.id == case_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return APIResponse(data=case_data(item), request_id=request_id)


@router.post("/cases/{case_id}/files", response_model=APIResponse[FileData], status_code=status.HTTP_201_CREATED)
async def upload_file(case_id: str, upload: Annotated[UploadFile, FastAPIFile(...)], admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[FileData]:
    case = db.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    original_name = Path(upload.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .las and .laz point-cloud files are supported")
    file_id = str(uuid4())
    storage_key = f"cases/{case_id}/raw/{file_id}{suffix}"
    destination = Path(settings.storage_root).resolve() / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    hasher, size = hashlib.sha256(), 0
    try:
        with destination.open("xb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds maximum size of {settings.max_upload_size_bytes} bytes")
                hasher.update(chunk)
                target.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty files are not accepted")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    item = File(id=file_id, case_id=case_id, storage_key=storage_key, original_name=original_name, mime_type=ALLOWED_SUFFIXES[suffix], size_bytes=size, checksum_sha256=hasher.hexdigest())
    db.add(item)
    db.add(AuditLog(action="POINTCLOUD_UPLOADED", actor_id=admin.id, case_id=case_id, detail={"fileId": item.id, "sizeBytes": size}))
    db.commit()
    db.refresh(item)
    return APIResponse(data=FileData(id=item.id, file_name=item.original_name, file_size=item.size_bytes), request_id=request_id)


@router.post("/cases/{case_id}/versions", response_model=APIResponse[VersionData], status_code=status.HTTP_202_ACCEPTED)
def create_version(case_id: str, payload: VersionCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[VersionData]:
    source = db.scalar(select(File).where(File.id == payload.file_id, File.case_id == case_id))
    if source is None:
        raise HTTPException(status_code=404, detail="Source file not found for case")
    version_number = (db.scalar(select(func.max(CaseVersion.version_number)).where(CaseVersion.case_id == case_id)) or 0) + 1
    version = CaseVersion(case_id=case_id, source_file_id=source.id, version_number=version_number, status="PROCESSING")
    db.add(version)
    db.flush()
    job = Job(case_version_id=version.id, status="PENDING", progress=0)
    db.add(job)
    db.add(AuditLog(action="CONVERSION_STARTED", actor_id=admin.id, case_id=case_id, case_version_id=version.id, job_id=job.id))
    db.commit()
    db.refresh(version)
    try:
        get_queue().enqueue(run_conversion, job.id, job_id=job.id)
    except Exception as exc:
        message = f"Conversion queue unavailable: {exc}"[:4000]
        version.status, version.error_message = "FAILED", message
        job.status, job.error_message = "FAILED", message
        db.add(AuditLog(action="CONVERSION_FAILED", actor_id=admin.id, case_id=case_id, case_version_id=version.id, job_id=job.id, detail={"error": message}))
        db.commit()
    return APIResponse(data=version_data(version), request_id=request_id)


@router.get("/case-versions/{version_id}", response_model=APIResponse[VersionData])
def get_version(version_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[VersionData]:
    item = db.scalar(select(CaseVersion).where(CaseVersion.id == version_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Case version not found")
    return APIResponse(data=version_data(item), request_id=request_id)


@router.get("/jobs/{job_id}", response_model=APIResponse[JobData])
def get_job(job_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[JobData]:
    item = db.scalar(select(Job).where(Job.id == job_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=job_data(item), request_id=request_id)
