"""M6 administrator-only desensitization rules and derived versions."""
import math
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_request_id, require_admin
from app.core.config import get_settings
from app.models.case import AuditLog, CaseVersion, DesensitizationRule, File, Job, TeachingCopy
from app.models.practice import Task
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.queue import get_queue
from app.services.desensitization import run_delete_desensitization

router=APIRouter(tags=["desensitization"]); settings=get_settings()
class RuleInput(BaseModel):
    mode: str
    geometry: dict
    title: str=Field(min_length=1,max_length=200)
    description: str|None=None

def box(geometry):
    try:
        if geometry.get("type")!="BOX": raise ValueError()
        low,high=geometry["min"],geometry["max"]
        if len(low)!=3 or len(high)!=3: raise ValueError()
        low,high=[float(x) for x in low],[float(x) for x in high]
        if not all(math.isfinite(x) for x in low+high) or any(a>=b for a,b in zip(low,high)): raise ValueError()
        return {"type":"BOX","min":low,"max":high}
    except (KeyError,TypeError,ValueError): raise HTTPException(422,"geometry must be a finite 3D BOX with min < max")
def editable(db,v):
    if not v: raise HTTPException(404,"Case version not found")
    if v.status in {"PUBLISHED","ARCHIVED"} or db.scalar(select(Task.id).where(Task.case_version_id==v.id)) or db.scalar(select(TeachingCopy.id).where(TeachingCopy.case_version_id==v.id)):
        raise HTTPException(409,"Published or teaching-assigned versions cannot be modified")
    if v.status not in {"READY","DRAFT"}: raise HTTPException(409,"Rules require READY or DRAFT version")
    return v
def data(r): return {"id":r.id,"caseVersionId":r.case_version_id,"mode":r.mode,"geometry":r.geometry,"title":r.title,"description":r.description or "","status":r.status,"enforced":r.status=="APPLIED" and r.mode=="HIDE","createdAt":r.created_at,"updatedAt":r.updated_at}
@router.get("/case-versions/{version_id}/desensitization-rules")
def rules(version_id:str,_:User=Depends(require_admin),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    if not db.get(CaseVersion,version_id): raise HTTPException(404,"Case version not found")
    return APIResponse(data=[data(x) for x in db.scalars(select(DesensitizationRule).where(DesensitizationRule.case_version_id==version_id)).all()],request_id=request_id)
@router.post("/case-versions/{version_id}/desensitization-rules",status_code=201)
def create(version_id:str,payload:RuleInput,admin:User=Depends(require_admin),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    v=editable(db,db.get(CaseVersion,version_id)); mode=payload.mode.upper()
    if mode not in {"HIDE","DELETE"}: raise HTTPException(422,"mode must be HIDE or DELETE")
    r=DesensitizationRule(case_version_id=v.id,created_by=admin.id,mode=mode,geometry=box(payload.geometry),title=payload.title,description=payload.description)
    db.add(r);db.flush();db.add(AuditLog(action=f"DESENSITIZATION_{mode}_RULE_CREATED",actor_id=admin.id,case_id=v.case_id,case_version_id=v.id,detail={"ruleId":r.id}));db.commit();db.refresh(r);return APIResponse(data=data(r),request_id=request_id)
@router.put("/desensitization-rules/{rule_id}")
def update(rule_id:str,payload:RuleInput,admin:User=Depends(require_admin),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    r=db.get(DesensitizationRule,rule_id)
    if not r: raise HTTPException(404,"Rule not found")
    editable(db,db.get(CaseVersion,r.case_version_id)); mode=payload.mode.upper()
    if mode not in {"HIDE","DELETE"}: raise HTTPException(422,"mode must be HIDE or DELETE")
    r.mode,r.geometry,r.title,r.description=mode,box(payload.geometry),payload.title,payload.description;db.add(AuditLog(action=f"DESENSITIZATION_{mode}_RULE_UPDATED",actor_id=admin.id,case_version_id=r.case_version_id,detail={"ruleId":r.id}));db.commit();db.refresh(r);return APIResponse(data=data(r),request_id=request_id)
@router.delete("/desensitization-rules/{rule_id}")
def delete(rule_id:str,admin:User=Depends(require_admin),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    r=db.get(DesensitizationRule,rule_id)
    if not r: raise HTTPException(404,"Rule not found")
    editable(db,db.get(CaseVersion,r.case_version_id));db.add(AuditLog(action=f"DESENSITIZATION_{r.mode}_RULE_DELETED",actor_id=admin.id,case_version_id=r.case_version_id,detail={"ruleId":r.id}));db.delete(r);db.commit();return APIResponse(data={},request_id=request_id)
@router.post("/case-versions/{version_id}/desensitization/apply",status_code=202)
def apply(version_id:str,admin:User=Depends(require_admin),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    parent=editable(db,db.get(CaseVersion,version_id)); rules=db.scalars(select(DesensitizationRule).where(DesensitizationRule.case_version_id==version_id,DesensitizationRule.status=="DRAFT")).all()
    if not rules: raise HTTPException(409,"No draft desensitization rules")
    number=(db.scalar(select(func.max(CaseVersion.version_number)).where(CaseVersion.case_id==parent.case_id)) or 0)+1; has_delete=any(r.mode=="DELETE" for r in rules)
    child_id=str(uuid4()); source_id=parent.source_file_id
    if has_delete:
        suffix=Path(parent.source_file.original_name).suffix.lower() or ".las"; file_id=str(uuid4())
        db.add(File(id=file_id,case_id=parent.case_id,storage_key=f"cases/{parent.case_id}/derived/{child_id}/{file_id}{suffix}",original_name=f"desensitized-{file_id}{suffix}",mime_type=parent.source_file.mime_type,size_bytes=0,checksum_sha256="0"*64)); source_id=file_id
    child=CaseVersion(id=child_id,case_id=parent.case_id,source_file_id=source_id,parent_version_id=parent.id,version_number=number,status="PROCESSING" if has_delete else "READY",point_count=parent.point_count,bounds=parent.bounds,viewer_manifest_key=parent.viewer_manifest_key)
    db.add(child);db.flush()
    for r in rules:
        db.add(DesensitizationRule(case_version_id=child.id,created_by=admin.id,mode=r.mode,geometry=r.geometry,title=r.title,description=r.description,status="APPLIED"))
    job=None
    if has_delete:
        job=Job(case_version_id=child.id,type="DESENSITIZATION_DELETE",status="PENDING",progress=0);db.add(job)
    db.add(AuditLog(action="DESENSITIZATION_APPLIED",actor_id=admin.id,case_id=child.case_id,case_version_id=child.id,detail={"parentVersionId":parent.id,"modes":[r.mode for r in rules]}));db.commit()
    if job:
        try: get_queue().enqueue(run_delete_desensitization,job.id,job_id=job.id,job_timeout=settings.conversion_timeout_seconds * 3 + 60)
        except Exception as exc:
            child.status,child.error_message="FAILED",f"Desensitization queue unavailable: {exc}"[:4000];job.status,job.error_message="FAILED",child.error_message;db.commit()
    return APIResponse(data={"versionId":child.id,"parentVersionId":child.parent_version_id,"status":child.status,"jobId":job.id if job else None,"progress":job.progress if job else 100,"failureReason":child.error_message},request_id=request_id)
