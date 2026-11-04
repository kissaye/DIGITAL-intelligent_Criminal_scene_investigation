from datetime import UTC,datetime
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_db,get_request_id,require_teacher
from app.models.case import AuditLog,Case,CaseVersion
from app.models.practice import Class,ClassMember,Course,Submission,SubmissionMark,SubmissionMeasurement,Task,TaskAssignment
from app.models.user import User
from app.schemas.common import APIResponse
router=APIRouter(prefix="/teacher",tags=["teacher"])
def dt(v): return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else v
def classdata(db,x):
 ids=[m.user_id for m in db.scalars(select(ClassMember).where(ClassMember.class_id==x.id))];return {'id':x.id,'courseId':x.course_id,'name':x.name,'memberIds':ids,'studentCount':len(ids)}
def coursedata(db,x): return {'id':x.id,'title':x.name,'description':x.description or '', 'classCount':len(db.scalars(select(Class).where(Class.course_id==x.id)).all())}
def taskdata(db,t):
 c=db.scalar(select(Class).where(Class.id==t.class_id));v=db.scalar(select(CaseVersion).where(CaseVersion.id==t.case_version_id));case=db.scalar(select(Case).where(Case.id==v.case_id)); assigned=len(db.scalars(select(TaskAssignment).where(TaskAssignment.task_id==t.id)).all()); submitted=len(db.scalars(select(Submission).where(Submission.task_id==t.id,Submission.status=='SUBMITTED')).all());return {'id':t.id,'classId':t.class_id,'className':c.name,'title':t.title,'instructions':t.instructions,'caseVersionId':t.case_version_id,'caseName':case.teaching_title,'startAt':t.start_at,'dueAt':t.due_at,'allowLate':t.allow_late,'assignedCount':assigned,'submittedCount':submitted}
def owned_course(db,cid,u):
 c=db.scalar(select(Course).where(Course.id==cid,Course.created_by==u.id));
 if not c: raise HTTPException(404,"Course not found")
 return c
def owned_class(db,cid,u):
 c=db.scalar(select(Class).where(Class.id==cid));
 if not c: raise HTTPException(404,"Class not found")
 owned_course(db,c.course_id,u);return c
def owned_task(db,tid,u):
 t=db.scalar(select(Task).where(Task.id==tid));
 if not t: raise HTTPException(404,"Task not found")
 owned_class(db,t.class_id,u);return t
@router.get('/students')
def students(u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 return APIResponse(data=[{"id":x.id,"username":x.username,"displayName":x.display_name} for x in db.scalars(select(User)).all() if 'STUDENT' in {r.code for r in x.roles}],request_id=request_id)
@router.get('/courses')
def courses(u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)): return APIResponse(data=[coursedata(db,x) for x in db.scalars(select(Course).where(Course.created_by==u.id))],request_id=request_id)
@router.post('/courses',status_code=201)
def course(p:dict,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 title=p.get('title','').strip()
 if not title: raise HTTPException(422,'title is required')
 x=Course(name=title,description=p.get('description',''),created_by=u.id);db.add(x);db.commit();db.refresh(x);return APIResponse(data=coursedata(db,x),request_id=request_id)
@router.get('/classes')
def classes(courseId:str,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 owned_course(db,courseId,u);return APIResponse(data=[classdata(db,x) for x in db.scalars(select(Class).where(Class.course_id==courseId))],request_id=request_id)
@router.post('/classes',status_code=201)
def create_class(p:dict,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 owned_course(db,p['courseId'],u); ids=p.get('memberIds',p.get('studentIds',[]));
 for i in ids:
  q=db.scalar(select(User).where(User.id==i));
  if not q or 'STUDENT' not in {r.code for r in q.roles}: raise HTTPException(422,'members must be students')
 x=Class(course_id=p['courseId'],name=p['name']);db.add(x);db.flush();[db.add(ClassMember(class_id=x.id,user_id=i)) for i in ids];db.commit();return APIResponse(data=classdata(db,x),request_id=request_id)
@router.put('/classes/{cid}/members')
def members(cid:str,p:dict,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 x=owned_class(db,cid,u);ids=p.get('memberIds',p.get('studentIds',[]));
 for i in ids:
  q=db.scalar(select(User).where(User.id==i));
  if not q or 'STUDENT' not in {r.code for r in q.roles}: raise HTTPException(422,'members must be students')
 db.query(ClassMember).filter_by(class_id=cid).delete();[db.add(ClassMember(class_id=cid,user_id=i)) for i in ids];db.commit();return APIResponse(data=classdata(db,x),request_id=request_id)
@router.get('/case-versions/ready')
def ready(u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 rows=db.scalars(select(CaseVersion).where(CaseVersion.status=='READY')).all();return APIResponse(data=[{"id":v.id,"caseId":v.case_id,"caseName":db.scalar(select(Case.teaching_title).where(Case.id==v.case_id)),"internalCode":db.scalar(select(Case.internal_code).where(Case.id==v.case_id)),"createdAt":v.created_at} for v in rows],request_id=request_id)
@router.post('/tasks',status_code=201)
def create_task(p:dict,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 c=owned_class(db,p['classId'],u);v=db.scalar(select(CaseVersion).where(CaseVersion.id==p['caseVersionId'],CaseVersion.status=='READY'))
 if not v: raise HTTPException(409,'Case version is not READY')
 start,due=dt(p.get('startAt')),dt(p.get('dueAt'))
 if start and due and due<start: raise HTTPException(422,'dueAt must not precede startAt')
 members=db.scalars(select(ClassMember).where(ClassMember.class_id==c.id)).all()
 if not members: raise HTTPException(409,'Class has no students')
 t=Task(class_id=c.id,title=p['title'],instructions=p.get('instructions'),case_version_id=v.id,start_at=start,due_at=due,allow_late=p.get('allowLate',False),status='PUBLISHED',report_template=p.get('reportTemplate'),created_by=u.id);db.add(t);db.flush();[db.add(TaskAssignment(task_id=t.id,student_id=m.user_id)) for m in members];db.add(AuditLog(action='TASK_CREATED',actor_id=u.id,case_version_id=v.id,detail={'taskId':t.id}));db.add(AuditLog(action='TASK_ASSIGNED',actor_id=u.id,case_version_id=v.id,detail={'taskId':t.id,'count':len(members)}));db.commit();return APIResponse(data=taskdata(db,t),request_id=request_id)
@router.get('/tasks')
def tasks(u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)): return APIResponse(data=[taskdata(db,t) for t in db.scalars(select(Task).where(Task.created_by==u.id))],request_id=request_id)
@router.get('/tasks/{tid}')
def task(tid:str,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 t=owned_task(db,tid,u);return APIResponse(data=taskdata(db,t),request_id=request_id)
def summary(s,db):
 student=db.scalar(select(User).where(User.id==s.student_id));return {'id':s.id,'studentId':student.id,'studentName':student.display_name,'status':s.status,'submittedAt':s.submitted_at,'score':s.score,'gradedAt':s.graded_at,'feedback':s.feedback}
@router.get('/tasks/{tid}/submissions')
def submissions(tid:str,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 owned_task(db,tid,u);return APIResponse(data=[summary(s,db) for s in db.scalars(select(Submission).where(Submission.task_id==tid))],request_id=request_id)
@router.get('/submissions/{sid}')
def submission(sid:str,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 s=db.scalar(select(Submission).where(Submission.id==sid));
 if not s: raise HTTPException(404,'Submission not found')
 owned_task(db,s.task_id,u);return APIResponse(data={**summary(s,db),'reportContent':s.report_content,'marks':[{'id':x.id,'geometry':x.geometry,'title':x.title,'description':x.description} for x in db.scalars(select(SubmissionMark).where(SubmissionMark.submission_id==s.id))],'measurements':[{'id':x.id,'startPoint':x.start_point,'endPoint':x.end_point,'distance':x.distance} for x in db.scalars(select(SubmissionMeasurement).where(SubmissionMeasurement.submission_id==s.id))],'feedback':s.feedback},request_id=request_id)
@router.put('/submissions/{sid}/grade')
def grade(sid:str,p:dict,u:User=Depends(require_teacher),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
 s=db.scalar(select(Submission).where(Submission.id==sid));
 if not s: raise HTTPException(404,'Submission not found')
 owned_task(db,s.task_id,u); score=p.get('score')
 if s.status!='SUBMITTED': raise HTTPException(409,'Only submitted work may be graded')
 if not isinstance(score,(int,float)) or not 0<=score<=100: raise HTTPException(422,'score must be between 0 and 100')
 s.score=score;s.feedback=p.get('feedback');s.graded_by=u.id;s.graded_at=datetime.now(UTC);db.add(AuditLog(action='SUBMISSION_GRADED',actor_id=u.id,detail={'submissionId':s.id}));db.commit();return APIResponse(data=summary(s,db),request_id=request_id)
