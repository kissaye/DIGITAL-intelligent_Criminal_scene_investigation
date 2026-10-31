"""M4 teaching APIs. Every resource lookup is scoped to its teacher."""
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_teacher
from app.api.routes.student import subdata
from app.models.case import AuditLog, Case, CaseVersion
from app.models.practice import Class, ClassMember, Course, Submission, Task, TaskAssignment
from app.models.role import Role
from app.models.teaching import GradeItem, RubricItem, SubmissionGrade, TaskClass
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.teacher import GradeInput, MemberInput, NameInput, TaskInput
from app.services.practice_access import utc

router = APIRouter(prefix="/teacher", tags=["teacher"])


def result(data, request_id):
    return APIResponse(data=data, request_id=request_id)


def owned(db, model, resource_id, teacher):
    item = db.scalar(select(model).where(model.id == resource_id, model.created_by == teacher.id).with_for_update())
    if item is None:
        raise HTTPException(404, "Resource not found")
    return item


def owned_class(db, class_id, teacher):
    item = db.get(Class, class_id)
    if item is None:
        raise HTTPException(404, "Class not found")
    owned(db, Course, item.course_id, teacher)
    return item


def audit(db, action, teacher, **detail):
    db.add(AuditLog(action=action, actor_id=teacher.id, detail=detail))


def course_data(db, item):
    return {"id": item.id, "name": item.name, "classes": [{"id": c.id, "name": c.name} for c in db.scalars(select(Class).where(Class.course_id == item.id)).all()]}


def student_data(user):
    return {"id": user.id, "username": user.username, "displayName": user.display_name}


@router.get("/courses")
def courses(user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    return result([course_data(db, c) for c in db.scalars(select(Course).where(Course.created_by == user.id)).all()], rid)


@router.post("/courses", status_code=201)
def create_course(p: NameInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = Course(name=p.name, created_by=user.id)
    db.add(item); db.commit()
    return result(course_data(db, item), rid)


@router.get("/courses/{course_id}")
def course(course_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    return result(course_data(db, owned(db, Course, course_id, user)), rid)


@router.patch("/courses/{course_id}")
def update_course(course_id: str, p: NameInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned(db, Course, course_id, user); item.name = p.name; db.commit()
    return result(course_data(db, item), rid)


@router.post("/courses/{course_id}/classes", status_code=201)
def create_class(course_id: str, p: NameInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    owned(db, Course, course_id, user)
    item = Class(course_id=course_id, name=p.name); db.add(item); db.commit()
    return result({"id": item.id, "name": item.name}, rid)


def class_data(db, item):
    members = db.scalars(select(User).join(ClassMember, ClassMember.user_id == User.id).where(ClassMember.class_id == item.id)).all()
    return {"id": item.id, "courseId": item.course_id, "name": item.name, "members": [student_data(u) for u in members]}


@router.get("/classes/{class_id}")
def get_class(class_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    return result(class_data(db, owned_class(db, class_id, user)), rid)


@router.patch("/classes/{class_id}")
def update_class(class_id: str, p: NameInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned_class(db, class_id, user); item.name = p.name; db.commit()
    return result(class_data(db, item), rid)


@router.get("/students")
def students(username: str=Query(min_length=1, max_length=64), user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    rows = db.scalars(select(User).where(User.username == username, User.is_active.is_(True), User.roles.any(Role.code == "STUDENT"))).all()
    return result([student_data(u) for u in rows], rid)


@router.post("/classes/{class_id}/members")
def add_member(class_id: str, p: MemberInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned_class(db, class_id, user)
    student = db.scalar(select(User).where(User.id == p.student_id, User.is_active.is_(True), User.roles.any(Role.code == "STUDENT")))
    if student is None:
        raise HTTPException(422, "Active student required")
    if not db.scalar(select(ClassMember).where(ClassMember.class_id == class_id, ClassMember.user_id == student.id)):
        db.add(ClassMember(class_id=class_id, user_id=student.id))
    db.commit()
    return result(class_data(db, item), rid)


@router.delete("/classes/{class_id}/members/{student_id}")
def remove_member(class_id: str, student_id: int, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned_class(db, class_id, user)
    db.execute(delete(ClassMember).where(ClassMember.class_id == class_id, ClassMember.user_id == student_id)); db.commit()
    return result(class_data(db, item), rid)


@router.get("/case-versions")
def versions(user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    rows = db.execute(select(CaseVersion, Case.teaching_title).join(Case).where(CaseVersion.status == "READY", CaseVersion.viewer_manifest_key.is_not(None))).all()
    return result([{"id": v.id, "teachingTitle": title, "versionNumber": v.version_number} for v, title in rows], rid)


def rubric_data(db, task_id):
    return [{"id": r.id, "title": r.title, "description": r.description, "maxScore": r.max_score} for r in db.scalars(select(RubricItem).where(RubricItem.task_id == task_id).order_by(RubricItem.sort_order)).all()]


def task_data(db, item):
    return {"id": item.id, "courseId": item.course_id, "title": item.title, "instructions": item.instructions,
            "caseVersionId": item.case_version_id, "classIds": list(db.scalars(select(TaskClass.class_id).where(TaskClass.task_id == item.id)).all()),
            "startAt": utc(item.start_at), "dueAt": utc(item.due_at), "allowLate": item.allow_late, "status": item.status, "rubric": rubric_data(db, item.id)}


def apply_task(db, item, p, user):
    owned(db, Course, p.course_id, user)
    for class_id in set(p.class_ids):
        if owned_class(db, class_id, user).course_id != p.course_id:
            raise HTTPException(422, "Class must belong to selected course")
    version = db.get(CaseVersion, p.case_version_id)
    if not version or version.status != "READY" or not version.viewer_manifest_key:
        raise HTTPException(409, "READY case version required")
    for name in ("course_id", "title", "instructions", "case_version_id", "allow_late"):
        setattr(item, name, getattr(p, name))
    item.start_at = p.start_at.astimezone(UTC) if p.start_at else None
    item.due_at = p.due_at.astimezone(UTC) if p.due_at else None
    db.add(item); db.flush()
    db.execute(delete(TaskClass).where(TaskClass.task_id == item.id))
    db.execute(delete(RubricItem).where(RubricItem.task_id == item.id))
    db.add_all([TaskClass(task_id=item.id, class_id=c) for c in set(p.class_ids)])
    db.add_all([RubricItem(task_id=item.id, title=r.title, description=r.description, max_score=r.max_score, sort_order=i) for i, r in enumerate(p.rubric)])


@router.get("/tasks")
def tasks(course_id: str | None=Query(default=None, alias="courseId"), status: str | None=None, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    query = select(Task).where(Task.created_by == user.id)
    if course_id: query = query.where(Task.course_id == course_id)
    if status: query = query.where(Task.status == status)
    rows = db.scalars(query.order_by(Task.created_at.desc())).all()
    data = []
    for t in rows:
        row = task_data(db, t)
        row["assignedCount"] = len(db.scalars(select(TaskAssignment.id).where(TaskAssignment.task_id == t.id)).all())
        row["submittedCount"] = len(db.scalars(select(Submission.id).where(Submission.task_id == t.id, Submission.status == "SUBMITTED")).all())
        data.append(row)
    return result(data, rid)


@router.post("/tasks", status_code=201)
def create_task(p: TaskInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = Task(created_by=user.id, status="DRAFT")
    apply_task(db, item, p, user); db.commit()
    return result(task_data(db, item), rid)


@router.get("/tasks/{task_id}")
def task(task_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    return result(task_data(db, owned(db, Task, task_id, user)), rid)


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, p: TaskInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned(db, Task, task_id, user)
    if item.status != "DRAFT": raise HTTPException(409, "Only drafts can be edited")
    apply_task(db, item, p, user); db.commit()
    return result(task_data(db, item), rid)


@router.post("/tasks/{task_id}/publish")
def publish(task_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned(db, Task, task_id, user)
    if item.status != "DRAFT": raise HTTPException(409, "Only drafts can be published")
    # Revalidate persisted draft, including class ownership and current version readiness.
    if not item.course_id or not rubric_data(db, item.id): raise HTTPException(409, "Course and rubric required")
    owned(db, Course, item.course_id, user)
    version = db.get(CaseVersion, item.case_version_id)
    if not version or version.status != "READY" or not version.viewer_manifest_key: raise HTTPException(409, "READY case version required")
    if item.due_at and utc(item.due_at) <= datetime.now(UTC): raise HTTPException(409, "Deadline has passed")
    class_ids = list(db.scalars(select(TaskClass.class_id).where(TaskClass.task_id == task_id)).all())
    for cid in class_ids:
        if owned_class(db, cid, user).course_id != item.course_id: raise HTTPException(409, "Invalid class")
    students = db.scalars(select(User.id).join(ClassMember, ClassMember.user_id == User.id).where(ClassMember.class_id.in_(class_ids), User.is_active.is_(True), User.roles.any(Role.code == "STUDENT")).distinct()).all()
    if not students: raise HTTPException(409, "At least one active student required")
    db.add_all([TaskAssignment(task_id=task_id, student_id=s) for s in students])
    item.status = "PUBLISHED"; audit(db, "TASK_PUBLISHED", user, taskId=task_id); db.commit()
    return result(task_data(db, item), rid)


@router.post("/tasks/{task_id}/close")
def close(task_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    item = owned(db, Task, task_id, user)
    if item.status != "PUBLISHED": raise HTTPException(409, "Only published tasks can be closed")
    item.status = "CLOSED"; audit(db, "TASK_CLOSED", user, taskId=task_id); db.commit()
    return result(task_data(db, item), rid)


def owned_submission(db, submission_id, user):
    s = db.get(Submission, submission_id)
    if not s: raise HTTPException(404, "Submission not found")
    t = owned(db, Task, s.task_id, user)
    if s.status != "SUBMITTED": raise HTTPException(409, "Only submitted work can be reviewed")
    return s, t


def grade_data(db, grade):
    if grade is None: return None
    return {"id": grade.id, "status": grade.status, "totalScore": grade.total_score, "feedback": grade.feedback, "publishedAt": utc(grade.published_at),
            "items": [{"rubricItemId": i.rubric_item_id, "score": i.score, "comment": i.comment} for i in db.scalars(select(GradeItem).where(GradeItem.grade_id == grade.id)).all()]}


@router.get("/tasks/{task_id}/submissions")
def submissions(task_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    owned(db, Task, task_id, user)
    students = db.scalars(select(User).join(TaskAssignment, TaskAssignment.student_id == User.id).where(TaskAssignment.task_id == task_id)).all()
    rows = []
    for student in students:
        s = db.scalar(select(Submission).where(Submission.task_id == task_id, Submission.student_id == student.id).order_by(Submission.version_no.desc()))
        g = db.scalar(select(SubmissionGrade).where(SubmissionGrade.submission_id == s.id)) if s and s.status == "SUBMITTED" else None
        rows.append({"student": student_data(student), "submissionId": s.id if s and s.status == "SUBMITTED" else None, "status": s.status if s else "NOT_STARTED", "submittedAt": utc(s.submitted_at) if s else None, "gradeStatus": g.status if g else None, "totalScore": g.total_score if g else None})
    return result(rows, rid)


@router.get("/submissions/{submission_id}")
def submission(submission_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    s, t = owned_submission(db, submission_id, user)
    g = db.scalar(select(SubmissionGrade).where(SubmissionGrade.submission_id == s.id))
    return result({"submission": subdata(db, s), "student": student_data(db.get(User, s.student_id)), "task": task_data(db, t), "grade": grade_data(db, g)}, rid)


@router.put("/submissions/{submission_id}/grade")
def save_grade(submission_id: str, p: GradeInput, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    s, t = owned_submission(db, submission_id, user)
    grade = db.scalar(select(SubmissionGrade).where(SubmissionGrade.submission_id == s.id))
    if grade and grade.status == "PUBLISHED": raise HTTPException(409, "Published grade is frozen")
    rubric = {r.id: r for r in db.scalars(select(RubricItem).where(RubricItem.task_id == t.id)).all()}
    ids = [i.rubric_item_id for i in p.items]
    if len(ids) != len(set(ids)): raise HTTPException(422, "Duplicate rubric items")
    for i in p.items:
        if i.rubric_item_id not in rubric or i.score > rubric[i.rubric_item_id].max_score: raise HTTPException(422, "Invalid rubric item or score")
    if grade is None:
        grade = SubmissionGrade(submission_id=s.id, graded_by=user.id); db.add(grade); db.flush()
    grade.feedback = p.feedback; grade.total_score = sum((i.score for i in p.items), Decimal(0))
    db.execute(delete(GradeItem).where(GradeItem.grade_id == grade.id))
    db.add_all([GradeItem(grade_id=grade.id, rubric_item_id=i.rubric_item_id, score=i.score, comment=i.comment) for i in p.items])
    audit(db, "GRADE_SAVED", user, submissionId=s.id); db.commit()
    return result(grade_data(db, grade), rid)


@router.post("/submissions/{submission_id}/grade/publish")
def publish_grade(submission_id: str, user=Depends(require_teacher), db: Session=Depends(get_db), rid=Depends(get_request_id)):
    s, t = owned_submission(db, submission_id, user)
    grade = db.scalar(select(SubmissionGrade).where(SubmissionGrade.submission_id == s.id))
    if not grade or grade.status != "DRAFT": raise HTTPException(409, "Grade draft required")
    rubric = {r.id: r for r in db.scalars(select(RubricItem).where(RubricItem.task_id == t.id)).all()}
    items = db.scalars(select(GradeItem).where(GradeItem.grade_id == grade.id)).all()
    if not rubric or {i.rubric_item_id for i in items} != set(rubric): raise HTTPException(409, "Complete every rubric item before publishing")
    grade.total_score = sum((i.score for i in items), Decimal(0)); grade.status = "PUBLISHED"; grade.published_at = datetime.now(UTC)
    audit(db, "GRADE_PUBLISHED", user, submissionId=s.id); db.commit()
    return result(grade_data(db, grade), rid)
