"""Administrator authorization, publication and audit endpoints."""
import hashlib
import shutil
import stat
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_request_id, require_admin
from app.core.config import get_settings
from app.models.case import AuditLog, Case, CaseAuthorization, CaseVersion, DesensitizationRule, TeachingCopy
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.publication import utc

router = APIRouter(tags=["m5"])

class AuthorizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reference: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=4000)
    valid_until: AwareDatetime = Field(alias="validUntil")

class PublicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    authorization_id: str = Field(alias="authorizationId")
    valid_until: AwareDatetime = Field(alias="validUntil")
    review_confirmed: bool = Field(alias="reviewConfirmed")
    review_note: str = Field(alias="reviewNote", min_length=1, max_length=4000)

def case_or_404(db, case_id):
    case = db.get(Case, case_id)
    if case is None: raise HTTPException(404, "Case not found")
    return case

def authorization_data(item):
    return {"id": item.id, "reference": item.authorization_no, "scope": item.scope, "validUntil": utc(item.valid_until), "revokedAt": utc(item.revoked_at)}

REQUIRED_POTREE_FILES = {"metadata.json", "hierarchy.bin", "octree.bin"}
PUBLISHED_SUFFIXES = {".json", ".bin"}

def copy_checksum(directory):
    digest = hashlib.sha256()
    files = sorted((p for p in directory.rglob("*") if p.is_file()), key=lambda p: p.relative_to(directory).as_posix())
    for item in files:
        digest.update(item.relative_to(directory).as_posix().encode("utf-8"))
        with item.open("rb") as stream:
            while chunk := stream.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()

def safe_potree_source(version, storage_root: Path | None = None):
    root = (storage_root or Path(get_settings().storage_root)).resolve()
    source = (root / "cases" / version.case_id / "versions" / version.id / "potree").resolve()
    if root not in source.parents or not source.is_dir() or source.is_symlink():
        raise HTTPException(409, "Converted point cloud is unavailable")
    present = {path.name for path in source.iterdir() if path.is_file() and not path.is_symlink()}
    if not REQUIRED_POTREE_FILES <= present: raise HTTPException(409, "Potree metadata, hierarchy.bin and octree.bin are required")
    publishable=[]
    for item in source.rglob("*"):
        resolved = item.resolve()
        if item.is_symlink() or (resolved != source and source not in resolved.parents): raise HTTPException(409, "Unsafe converter output")
        mode = item.stat(follow_symlinks=False).st_mode
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)): raise HTTPException(409, "Unsafe converter output")
        if item.is_file():
            relative=item.relative_to(source)
            # PotreeConverter 2.1.1 diagnostic only; never publish it.
            if relative.as_posix()=="log.txt": continue
            if item.suffix.lower() not in PUBLISHED_SUFFIXES: raise HTTPException(409, "Unexpected converter output")
            publishable.append(relative)
    return root, source, publishable

def copy_teaching_assets(source, destination, files):
    if destination.exists(): raise HTTPException(409,"Unsafe teaching destination")
    destination.mkdir(parents=True)
    try:
        for relative in files:
            src=(source/relative).resolve(); target=(destination/relative).resolve()
            if source not in src.parents or destination not in target.parents or src.is_symlink() or not src.is_file() or not stat.S_ISREG(src.stat().st_mode):
                raise HTTPException(409,"Unsafe converter output")
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,target)
    except Exception:
        # This helper owns a newly-created destination.  Never leave a partial
        # teaching copy behind for a caller that handles a copy failure.
        shutil.rmtree(destination, ignore_errors=True)
        raise

@router.get("/cases/{case_id}/authorizations")
def authorizations(case_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    case_or_404(db, case_id)
    rows = db.scalars(select(CaseAuthorization).where(CaseAuthorization.case_id == case_id).order_by(CaseAuthorization.created_at.desc())).all()
    return APIResponse(data=[authorization_data(row) for row in rows], request_id=request_id)

@router.post("/cases/{case_id}/authorizations", status_code=201)
def add_authorization(case_id: str, payload: AuthorizationInput, admin: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    case_or_404(db, case_id); valid_until = payload.valid_until.astimezone(UTC)
    if valid_until <= datetime.now(UTC): raise HTTPException(422, "validUntil must be in the future")
    item = CaseAuthorization(case_id=case_id, authorization_no=payload.reference, scope=payload.scope, valid_until=valid_until, created_by=admin.id)
    db.add(item); db.flush(); db.add(AuditLog(action="AUTHORIZATION_CREATED", actor_id=admin.id, case_id=case_id, detail={"authorizationId": item.id})); db.commit(); db.refresh(item)
    return APIResponse(data=authorization_data(item), request_id=request_id)

@router.post("/authorizations/{authorization_id}/revoke")
def revoke_authorization(authorization_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    item = db.scalar(select(CaseAuthorization).where(CaseAuthorization.id == authorization_id).with_for_update())
    if item is None: raise HTTPException(404, "Authorization not found")
    if item.revoked_at is not None: raise HTTPException(409, "Authorization is already revoked")
    item.revoked_at = datetime.now(UTC); db.add(AuditLog(action="AUTHORIZATION_REVOKED", actor_id=admin.id, case_id=item.case_id, detail={"authorizationId": item.id})); db.commit(); db.refresh(item)
    return APIResponse(data=authorization_data(item), request_id=request_id)

@router.get("/cases/{case_id}/versions")
def versions(case_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    case_or_404(db, case_id); result = []
    for version in db.scalars(select(CaseVersion).where(CaseVersion.case_id == case_id).order_by(CaseVersion.version_number)).all():
        copy = db.scalar(select(TeachingCopy).where(TeachingCopy.case_version_id == version.id))
        publication = None if copy is None else {"authorizationId": copy.authorization_id, "validUntil": utc(copy.valid_until), "publishedAt": utc(copy.published_at), "checksum": copy.checksum_sha256, "reviewNote": copy.review_note}
        result.append({"id": version.id, "versionNumber": version.version_number, "parentVersionId": version.parent_version_id, "status": version.status, "createdAt": utc(version.created_at), "publication": publication})
    return APIResponse(data=result, request_id=request_id)

@router.post("/case-versions/{version_id}/publish")
def publish(version_id: str, payload: PublicationInput, admin: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    version = db.scalar(select(CaseVersion).where(CaseVersion.id == version_id).with_for_update())
    if version is None: raise HTTPException(404, "Version not found")
    if version.status != "READY" or db.scalar(select(TeachingCopy).where(TeachingCopy.case_version_id == version.id)): raise HTTPException(409, "Only unpublished READY versions can be published")
    pending_rules=db.scalar(select(DesensitizationRule.id).where(DesensitizationRule.case_version_id==version.id,DesensitizationRule.status!="APPLIED"))
    if pending_rules: raise HTTPException(409,"All desensitization rules must be applied before publication")
    case = case_or_404(db, version.case_id)
    authorization = db.scalar(select(CaseAuthorization).where(CaseAuthorization.id == payload.authorization_id, CaseAuthorization.case_id == version.case_id).with_for_update())
    now, valid_until = datetime.now(UTC), payload.valid_until.astimezone(UTC)
    if not payload.review_confirmed: raise HTTPException(422, "Human review confirmation is required")
    if authorization is None or authorization.revoked_at is not None or utc(authorization.valid_until) <= now: raise HTTPException(409, "A valid authorization for this case is required")
    if valid_until <= now or valid_until > utc(authorization.valid_until) or (case.valid_until is not None and valid_until > utc(case.valid_until)): raise HTTPException(422, "Publication validity exceeds authorization or case validity")
    root, source, assets = safe_potree_source(version); destination = (root / "teaching" / str(uuid4())).resolve()
    if root not in destination.parents or destination.exists(): raise HTTPException(409, "Unsafe teaching destination")
    try:
        copy_teaching_assets(source, destination, assets)
        manifest = destination / "metadata.json"
        hide_rules=[{"id":r.id,"mode":r.mode,"geometry":r.geometry,"title":r.title,"description":r.description} for r in db.scalars(select(DesensitizationRule).where(DesensitizationRule.case_version_id==version.id,DesensitizationRule.mode=="HIDE",DesensitizationRule.status=="APPLIED")).all()]
        copy = TeachingCopy(case_version_id=version.id, authorization_id=authorization.id, manifest_key=manifest.relative_to(root).as_posix(), checksum_sha256=copy_checksum(destination), reviewed_at=now, reviewed_by=admin.id, review_note=payload.review_note, valid_until=valid_until, published_by=admin.id,desensitization_rules=hide_rules)
        db.add(copy); version.status = "PUBLISHED"; db.add(AuditLog(action="VERSION_PUBLISHED", actor_id=admin.id, case_id=version.case_id, case_version_id=version.id, detail={"authorizationId": authorization.id, "checksum": copy.checksum_sha256})); db.commit(); db.refresh(copy)
    except Exception:
        db.rollback()
        if destination.exists(): shutil.rmtree(destination)
        raise
    return APIResponse(data={"id": version.id, "status": version.status, "publication": {"authorizationId": copy.authorization_id, "validUntil": utc(copy.valid_until), "publishedAt": utc(copy.published_at), "checksum": copy.checksum_sha256, "reviewNote": copy.review_note}}, request_id=request_id)

@router.post("/case-versions/{version_id}/archive")
def archive(version_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    version = db.scalar(select(CaseVersion).where(CaseVersion.id == version_id).with_for_update())
    if version is None: raise HTTPException(404, "Version not found")
    if version.status != "PUBLISHED": raise HTTPException(409, "Only PUBLISHED versions can be archived")
    version.status = "ARCHIVED"; db.add(AuditLog(action="VERSION_ARCHIVED", actor_id=admin.id, case_id=version.case_id, case_version_id=version.id)); db.commit()
    return APIResponse(data={"id": version.id, "status": version.status}, request_id=request_id)

@router.get("/audit-logs")
def audit_logs(caseId: str | None = None, versionId: str | None = None, action: str | None = None, actorId: int | None = None, startAt: AwareDatetime | None = None, endAt: AwareDatetime | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), _: User = Depends(require_admin), db: Session = Depends(get_db), request_id: str = Depends(get_request_id)):
    if startAt is not None and endAt is not None and startAt > endAt: raise HTTPException(422, "startAt must not exceed endAt")
    query = select(AuditLog)
    if caseId: query = query.where(or_(AuditLog.case_id == caseId, AuditLog.case_version_id.in_(select(CaseVersion.id).where(CaseVersion.case_id == caseId))))
    if versionId: query = query.where(AuditLog.case_version_id == versionId)
    if action: query = query.where(AuditLog.action == action)
    if actorId is not None: query = query.where(AuditLog.actor_id == actorId)
    if startAt is not None: query = query.where(AuditLog.created_at >= startAt.astimezone(UTC))
    if endAt is not None: query = query.where(AuditLog.created_at <= endAt.astimezone(UTC))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)).all()
    return APIResponse(data={"items": [{"id": row.id, "action": row.action, "actorId": row.actor_id, "caseId": row.case_id, "versionId": row.case_version_id, "createdAt": utc(row.created_at), "detail": row.detail} for row in rows], "total": total}, request_id=request_id)
