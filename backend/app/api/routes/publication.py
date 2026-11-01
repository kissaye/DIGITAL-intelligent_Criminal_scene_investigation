"""Administrator publication, authorization and audit APIs."""
import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_request_id, require_admin
from app.core.config import get_settings
from app.models.case import AuditLog, Case, CaseVersion
from app.models.publication import CaseAuthorization, TeachingCopy
from app.schemas.common import APIResponse
from app.services.practice_access import utc

router = APIRouter(tags=['publication'])


class AuthorizationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reference: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=4000)
    validUntil: AwareDatetime


class PublicationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    authorizationId: str
    validUntil: AwareDatetime
    reviewConfirmed: bool
    reviewNote: str = Field(min_length=1, max_length=4000)


def case_or_404(db, cid):
    item = db.get(Case, cid)
    if not item: raise HTTPException(404, 'Case not found')
    return item


def auth_data(a):
    return dict(id=a.id, reference=a.reference, scope=a.scope, validUntil=utc(a.valid_until), revokedAt=utc(a.revoked_at))


@router.get('/cases/{case_id}/authorizations')
def authorizations(case_id: str, admin=Depends(require_admin), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    case_or_404(db, case_id)
    return APIResponse(data=[auth_data(a) for a in db.scalars(select(CaseAuthorization).where(CaseAuthorization.case_id == case_id)).all()], request_id=rid)


@router.post('/cases/{case_id}/authorizations', status_code=201)
def add_authorization(case_id: str, p: AuthorizationInput, admin=Depends(require_admin), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    case_or_404(db, case_id)
    if p.validUntil <= datetime.now(UTC): raise HTTPException(422, 'Authorization must expire in future')
    a = CaseAuthorization(case_id=case_id, reference=p.reference, scope=p.scope, valid_until=p.validUntil.astimezone(UTC), created_by=admin.id)
    db.add(a); db.flush()
    db.add(AuditLog(action='AUTHORIZATION_CREATED', actor_id=admin.id, case_id=case_id, detail={'authorizationId':a.id})); db.commit()
    return APIResponse(data=auth_data(a), request_id=rid)


@router.post('/authorizations/{authorization_id}/revoke')
def revoke(authorization_id: str, admin=Depends(require_admin), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    a = db.scalar(select(CaseAuthorization).where(CaseAuthorization.id == authorization_id).with_for_update())
    if not a: raise HTTPException(404, 'Authorization not found')
    if a.revoked_at: raise HTTPException(409, 'Already revoked')
    a.revoked_at = datetime.now(UTC)
    db.add(AuditLog(action='AUTHORIZATION_REVOKED', actor_id=admin.id, case_id=a.case_id, detail={'authorizationId':a.id})); db.commit()
    return APIResponse(data=auth_data(a), request_id=rid)


@router.get('/cases/{case_id}/versions')
def versions(case_id: str, admin=Depends(require_admin), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    case_or_404(db, case_id)
    rows=[]
    for v in db.scalars(select(CaseVersion).where(CaseVersion.case_id == case_id).order_by(CaseVersion.version_number)).all():
        c=db.scalar(select(TeachingCopy).where(TeachingCopy.version_id == v.id))
        rows.append(dict(id=v.id, versionNumber=v.version_number, parentVersionId=v.parent_version_id, status=v.status, publication=dict(validUntil=utc(c.valid_until), publishedAt=utc(c.published_at), checksum=c.checksum, reviewNote=c.review_note, authorizationId=c.authorization_id) if c else None))
    return APIResponse(data=rows, request_id=rid)


@router.post('/case-versions/{version_id}/publish')
def publish(version_id: str, p: PublicationInput, admin=Depends(require_admin), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    v=db.scalar(select(CaseVersion).where(CaseVersion.id == version_id).with_for_update())
    if not v: raise HTTPException(404, 'Version not found')
    if v.status != 'READY' or db.scalar(select(TeachingCopy).where(TeachingCopy.version_id == v.id)): raise HTTPException(409, 'Only unpublished READY versions can be published')
    a=db.scalar(select(CaseAuthorization).where(CaseAuthorization.id == p.authorizationId, CaseAuthorization.case_id == v.case_id).with_for_update())
    case=case_or_404(db,v.case_id); now=datetime.now(UTC)
    if not p.reviewConfirmed: raise HTTPException(422,'Human review confirmation required')
    if not a or a.revoked_at or utc(a.valid_until) <= now: raise HTTPException(409,'Valid case authorization required')
    if p.validUntil <= now or p.validUntil > utc(a.valid_until) or (case.valid_until and p.validUntil > utc(case.valid_until)): raise HTTPException(422,'Publication expiry exceeds authorization/case validity')
    root=Path(get_settings().storage_root).resolve()
    source=(root / 'cases' / v.case_id / 'versions' / v.id / 'potree').resolve()
    if root not in source.parents or not (source/'metadata.json').is_file(): raise HTTPException(409,'Converted point cloud unavailable')
    # Only converter output files enter the independent teaching copy, never raw LAS/LAZ.
    files=list(source.rglob('*'))
    if any(f.is_symlink() or source not in f.resolve().parents or (f.is_file() and f.suffix.lower() not in {'.json','.bin'}) for f in files): raise HTTPException(409,'Unexpected converter output or symbolic link')
    destination=root/'teaching'/str(uuid4())
    try:
        shutil.copytree(source,destination)
        digest=hashlib.sha256()
        for f in sorted(destination.rglob('*')):
            if f.is_file():
                digest.update(f.relative_to(destination).as_posix().encode())
                with f.open('rb') as stream:
                    while chunk:=stream.read(1024*1024): digest.update(chunk)
        c=TeachingCopy(version_id=v.id,authorization_id=a.id,manifest_key=(destination/'metadata.json').relative_to(root).as_posix(),checksum=digest.hexdigest(),review_note=p.reviewNote,valid_until=p.validUntil.astimezone(UTC),published_by=admin.id)
        db.add(c); v.status='PUBLISHED'
        db.add(AuditLog(action='VERSION_PUBLISHED',actor_id=admin.id,case_id=v.case_id,case_version_id=v.id,detail={'checksum':c.checksum,'authorizationId':a.id}));db.commit()
    except Exception:
        db.rollback()
        if destination.exists(): shutil.rmtree(destination)
        raise
    return APIResponse(data={'versionId':v.id,'status':v.status,'validUntil':utc(c.valid_until),'checksum':c.checksum},request_id=rid)


@router.get('/audit-logs')
def audit_logs(caseId: str | None=None, versionId: str | None=None, action: str | None=None, actorId: int | None=None, startAt: AwareDatetime | None=None, endAt: AwareDatetime | None=None, offset: int=Query(0,ge=0), limit: int=Query(50,ge=1,le=200), admin=Depends(require_admin), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    action=action or None
    if startAt and endAt and startAt>endAt: raise HTTPException(422,'Invalid time range')
    q=select(AuditLog)
    if caseId:
        q=q.where(or_(AuditLog.case_id==caseId,AuditLog.case_version_id.in_(select(CaseVersion.id).where(CaseVersion.case_id==caseId))))
    for field,value in [(AuditLog.case_version_id,versionId),(AuditLog.action,action),(AuditLog.actor_id,actorId)]:
        if value is not None:q=q.where(field==value)
    if startAt:q=q.where(AuditLog.created_at>=startAt.astimezone(UTC))
    if endAt:q=q.where(AuditLog.created_at<=endAt.astimezone(UTC))
    total=db.scalar(select(func.count()).select_from(q.subquery()))
    items=db.scalars(q.order_by(AuditLog.created_at.desc(),AuditLog.id.desc()).offset(offset).limit(limit)).all()
    return APIResponse(data={'total':total,'items':[dict(id=a.id,action=a.action,actorId=a.actor_id,caseId=a.case_id,versionId=a.case_version_id,createdAt=utc(a.created_at),detail=a.detail) for a in items]},request_id=rid)
