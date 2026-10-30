import math
from datetime import UTC, datetime, timedelta
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_db,get_request_id,require_student
from app.core.config import get_settings
from app.models.case import AuditLog,Case,CaseVersion
from app.models.practice import Submission,SubmissionMark,SubmissionMeasurement,Task,TaskAssignment
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.student import DraftPayload
router=APIRouter(prefix="/student",tags=["student"]); settings=get_settings()
def assigned(db,task_id,user):
    task=db.scalar(select(Task).where(Task.id==task_id)); ok=db.scalar(select(TaskAssignment).where(TaskAssignment.task_id==task_id,TaskAssignment.student_id==user.id))
    if not task or not ok: raise HTTPException(404,"Task not found")
    return task
def draft(db,task,user): return db.scalar(select(Submission).where(Submission.task_id==task.id,Submission.student_id==user.id,Submission.status=="DRAFT"))
def student_submission(db,t,u): return db.scalar(select(Submission).where(Submission.task_id==t.id,Submission.student_id==u.id).order_by(Submission.created_at.desc()))
def taskdata(db,t,u):
    s=student_submission(db,t,u); v=db.scalar(select(CaseVersion).where(CaseVersion.id==t.case_version_id)); c=db.scalar(select(Case).where(Case.id==v.case_id)) if v else None; now=datetime.now(UTC)
    state="SUBMITTED" if s and s.status=="SUBMITTED" else "NOT_STARTED" if t.start_at and now<t.start_at else "EXPIRED" if t.due_at and now>t.due_at and not t.allow_late else "IN_PROGRESS"
    return {"id":t.id,"name":t.title,"caseName":c.teaching_title if c else "","instructions":t.instructions,"caseVersionId":t.case_version_id,"startAt":t.start_at,"dueAt":t.due_at,"allowLate":t.allow_late,"status":state,"submissionId":s.id if s else None,"submittedAt":s.submitted_at if s else None,"submissionVersion":f"v{s.version_no}" if s else None}
@router.get("/tasks")
def tasks(user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    rows=db.scalars(select(Task).join(TaskAssignment).where(TaskAssignment.student_id==user.id)).all(); return APIResponse(data=[taskdata(db,x,user) for x in rows],request_id=request_id)
@router.get("/tasks/{task_id}")
def task(task_id:str,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)): return APIResponse(data=taskdata(db,assigned(db,task_id,user),user),request_id=request_id)
@router.get("/tasks/{task_id}/workspace")
def workspace(task_id:str,response:Response,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    t=assigned(db,task_id,user); v=db.scalar(select(CaseVersion).where(CaseVersion.id==t.case_version_id))
    if not v or v.status!="READY" or not v.viewer_manifest_key: raise HTTPException(409,"Workspace viewer is unavailable")
    d=student_submission(db,t,user); exp=datetime.now(UTC)+timedelta(minutes=settings.viewer_token_expire_minutes); token=jwt.encode({"sub":str(user.id),"version":v.id,"task":t.id,"exp":exp,"type":"student_viewer"},settings.jwt_secret_key,algorithm=settings.jwt_algorithm)
    response.set_cookie(f"viewer_{v.id}",token,max_age=settings.viewer_token_expire_minutes*60,httponly=True,samesite="lax",path=f"{settings.api_v1_prefix}/viewer-assets/{v.id}")
    db.add(AuditLog(action="TASK_WORKSPACE_OPENED",actor_id=user.id,case_id=v.case_id,case_version_id=v.id,detail={"taskId":t.id}));db.commit()
    return APIResponse(data={"task":taskdata(db,t,user),"draft":subdata(db,d) if d else None,"viewerConfig":{"versionId":v.id,"manifestUrl":f"{settings.api_v1_prefix}/viewer-assets/{v.id}/metadata.json"}},request_id=request_id)
def subdata(db,s):
    return {"id":s.id,"status":s.status,"reportContent":s.report_content,"marks":[{"id":x.id,"geometry":x.geometry,"title":x.title,"description":x.description,"viewerState":x.viewer_state} for x in db.scalars(select(SubmissionMark).where(SubmissionMark.submission_id==s.id))],"measurements":[{"id":x.id,"startPoint":x.start_point,"endPoint":x.end_point,"distance":x.distance,"viewerState":x.viewer_state} for x in db.scalars(select(SubmissionMeasurement).where(SubmissionMeasurement.submission_id==s.id))],"submittedAt":s.submitted_at,"version":f"v{s.version_no}"}
def save(db,t,u,p):
    if db.scalar(select(Submission).where(Submission.task_id==t.id,Submission.student_id==u.id,Submission.status=="SUBMITTED")):
        raise HTTPException(409,"Submitted work is frozen")
    s=draft(db,t,u) or Submission(task_id=t.id,student_id=u.id,status="DRAFT",version_no=1);db.add(s);db.flush();s.report_content=p.report_content;db.query(SubmissionMark).filter_by(submission_id=s.id).delete();db.query(SubmissionMeasurement).filter_by(submission_id=s.id).delete()
    for m in p.marks: db.add(SubmissionMark(submission_id=s.id,geometry=m.get("geometry",{}),title=m.get("title",""),description=m.get("description"),viewer_state=m.get("viewerState")))
    for m in p.measurements:
        a,b=m.get("startPoint",{}),m.get("endPoint",{});dist=math.dist([float(a[k]) for k in('x','y','z')],[float(b[k]) for k in('x','y','z')]);db.add(SubmissionMeasurement(submission_id=s.id,start_point=a,end_point=b,distance=dist,viewer_state=m.get("viewerState")))
    return s
@router.put("/tasks/{task_id}/draft")
def save_draft(task_id:str,payload:DraftPayload,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    t=assigned(db,task_id,user); now=datetime.now(UTC)
    if t.status!="PUBLISHED" or (t.start_at and now<t.start_at) or (t.due_at and now>t.due_at and not t.allow_late): raise HTTPException(409,"Task is not editable")
    s=save(db,t,user,payload);db.add(AuditLog(action="DRAFT_SAVED",actor_id=user.id,case_version_id=t.case_version_id,detail={"taskId":t.id,"submissionId":s.id}));db.commit();return APIResponse(data=subdata(db,s),request_id=request_id)
@router.post("/tasks/{task_id}/submissions")
def submit(task_id:str,payload:DraftPayload,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    t=assigned(db,task_id,user); now=datetime.now(UTC)
    if t.status!="PUBLISHED" or (t.start_at and now<t.start_at) or (t.due_at and now>t.due_at and not t.allow_late): raise HTTPException(409,"Task submission is closed")
    s=save(db,t,user,payload);s.status="SUBMITTED";s.submitted_at=now;db.add(AuditLog(action="SUBMISSION_CREATED",actor_id=user.id,case_version_id=t.case_version_id,detail={"taskId":t.id,"submissionId":s.id}));db.commit();return APIResponse(data=subdata(db,s),request_id=request_id)
@router.get("/submissions/{submission_id}")
def submission(submission_id:str,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    s=db.scalar(select(Submission).where(Submission.id==submission_id));
    if not s or s.student_id!=user.id: raise HTTPException(404,"Submission not found")
    return APIResponse(data=subdata(db,s),request_id=request_id)
