# M4 完整代码

以下为全部改动实现文件、测试、配置和数据库 SQL 的完整内容。可维护源文件仍位于各自目录。交付说明和清单见同目录 README.md、files.md。

## .gitignore

````text
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Environment and secrets
.env
.env.*
!.env.example
backend/*.db

# Local build and render outputs
tmp/
dist/
build/

# Local data and case materials must never be committed
data/
storage/
sample-data/private/
*.las
*.laz
*.e57
*.goslam
*.pcd
*.ply
*.mp4

# Third-party and source materials retained locally only
产品资料/
数智刑勘——刑侦现场数字化产教融合平台(1).docx
数智刑勘平台 PRD 重写版.docx

.venv-test/
````

## README.md

````markdown
# 数智刑勘

刑侦三维案例脱敏与教学实训平台。

本项目接收人工导出的 LAS 或 LAZ 点云及可选媒体资料，经脱敏复核后形成教学副本，支持三维浏览、标记、测量、勘验笔录、任务提交和教师评分。

## MVP 边界

- 不接入 GoSLAM API，不读取 `.goslam` 私有采集包。
- 不替代公安业务系统或认定证据效力。
- 原始案件数据、授权材料和真实案例文件不得提交到本公开仓库。
- 自动脱敏仅提供辅助建议；教学版本必须经过人工复核与发布确认。

## 开发模块

`M0 工程底座` → `M1 案例导入与转换` → `M2 三维浏览与标记` → `M3 学生实训` → `M4 教师教学管理` → `M5 案例版本与审计` → `M6 脱敏增强`

详细规划见 [docs/开发模块总任务书.md](docs/开发模块总任务书.md)。

## 协作约定

- `main` 分支始终保持可启动、可演示。
- 每个模块在独立 `feature/` 分支开发，通过 Pull Request 审查后合并。
- 不提交 `.env`、真实案件材料、授权材料、点云文件或大体积媒体文件。

## M0 后端启动

后端位于 `backend/`，提供 JWT 登录和角色身份接口。默认使用 SQLite，便于本地前后端联调；容器配置使用 PostgreSQL。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000/docs> 查看 Swagger 文档。健康检查为 `GET /api/v1/health`。

三个仅用于本地演示的预置账号均使用密码 `M0DemoPass!2026`：`admin`（ADMIN）、`teacher`（TEACHER）、`student`（STUDENT）。种子命令可安全重复运行，不会覆盖已存在账号的密码。

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/auth/login -ContentType 'application/json' -Body '{"username":"admin","password":"M0DemoPass!2026"}'
```

将响应中的 `data.accessToken` 作为 `Authorization: Bearer <token>` 调用 `GET /api/v1/auth/me`。

具备 Docker 的环境可从仓库根目录运行 `docker compose up --build`。该配置会启动 PostgreSQL、后端与前端；迁移和种子数据自动初始化。打开 <http://localhost:5173>，使用上述演示账号登录。

## M1 案例导入与转换

仅 `ADMIN` 可以创建案例、上传 `.las` / `.laz` 原始点云，并创建转换版本。文件上传后保存于 `STORAGE_ROOT/cases/<case_id>/raw/`；该目录没有静态路由，数据库只记录 `storage_key` 与校验和等元数据。默认文件上限为 1 GiB，可用 `MAX_UPLOAD_SIZE_BYTES` 调整。

创建版本会生成后台任务，状态为 `PENDING → RUNNING → SUCCEEDED / FAILED`；版本为 `DRAFT → PROCESSING → READY`，工具或转换失败时版本为 `FAILED` 并写入错误原因。PDAL 和 PotreeConverter 分别由 `PDAL_PATH`、`POTREE_CONVERTER_PATH` 指定；没有安装工具时任务会明确失败，不会生成伪造的 READY 版本。

转换任务通过 Redis + RQ 的 `pointcloud` 队列执行，不会占用 API 进程。Docker Compose 已包含 Redis 与 `worker` 服务；非容器环境需自行启动 Redis 后运行 `rq worker pointcloud`。

M1 API：`POST /api/v1/cases`、`GET /api/v1/cases`、`GET /api/v1/cases/{caseId}`、`POST /api/v1/cases/{caseId}/files`、`POST /api/v1/cases/{caseId}/versions`、`GET /api/v1/case-versions/{versionId}`、`GET /api/v1/jobs/{jobId}`。上传接口使用表单字段 `upload`。所有创建、上传和转换结果均写入基础审计日志。

## M2 受控点云浏览

M2 仅向管理员开放 READY 版本的 `GET /api/v1/case-versions/{versionId}/viewer-config`。该接口签发一个仅绑定该版本、短期有效的 HttpOnly Cookie，并返回受控的 Potree `metadata.json` 地址。Potree 的 metadata 和瓦片经 `/api/v1/viewer-assets/{versionId}/...` 逐项代理读取；代理会校验 Cookie 中的版本声明、拒绝路径穿越，并且绝不映射原始 LAS/LAZ 或整个 storage 目录。打开 Viewer 和每次资源读取都会写入审计日志。

管理员可在 READY 版本下维护自己的 `ADMIN_WORKSPACE` 标注与测距记录。测距距离由后端基于两端三维坐标重新计算，忽略客户端提交的 distance。

## M3 学生实训

学生接口均要求 `STUDENT` 角色及任务分配记录。工作台只返回该学生自己的草稿、提交标记和测距，并对绑定的 READY 版本签发任务限定的短期 Viewer Cookie。草稿可重复保存；首次提交后转为 `SUBMITTED`，后续草稿或提交写入会被拒绝。截止时间之后仅在 `allow_late=true` 时可提交。

## M4 教师教学管理

已实现教师课程/班级、任务发布与关闭、评分点、作业批改和成绩反馈；学生沿用 M3 提交并查看本人已发布成绩。教师入口位于登录后的首页。真实联调需设置 `VITE_USE_MOCK=false`。

详细接口、迁移 SQL、测试步骤、完整代码和 commit 信息见 [M4 交付说明](docs/m4/README.md)。本轮仍沿用 READY 版本，不增加 M5、M6。

## 项目资料

- `刑侦三维案例脱敏与教学实训平台 PRD V1.0.docx`
- `刑侦三维案例平台 安全合规与竞赛材料包.docx`
- `build_prd_baseline.py` 与 `build_compliance_pack.py`：以上文档的生成脚本。
````

## backend/alembic/versions/20261031_0006_create_teacher_management.py

````python
"""M4 teacher management; preserve existing M3 tasks."""
from alembic import op
import sqlalchemy as sa

revision = "202610310006"
down_revision = "202610300005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("course_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_tasks_course_id", "courses", ["course_id"], ["id"])
        batch.create_index("ix_tasks_course_id", ["course_id"])
    op.create_table("task_classes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", sa.String(36), sa.ForeignKey("classes.id"), nullable=False),
        sa.UniqueConstraint("task_id", "class_id"))
    op.create_index("ix_task_classes_task_id", "task_classes", ["task_id"])
    op.create_table("task_rubric_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("max_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("max_score > 0", name="ck_rubric_positive"))
    op.create_index("ix_task_rubric_items_task_id", "task_rubric_items", ["task_id"])
    op.create_table("submission_grades",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id"), nullable=False, unique=True),
        sa.Column("graded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("total_score >= 0", name="ck_grade_nonnegative"))
    op.create_table("submission_grade_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("grade_id", sa.String(36), sa.ForeignKey("submission_grades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rubric_item_id", sa.String(36), sa.ForeignKey("task_rubric_items.id"), nullable=False),
        sa.Column("score", sa.Numeric(7, 2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.UniqueConstraint("grade_id", "rubric_item_id"),
        sa.CheckConstraint("score >= 0", name="ck_grade_item_nonnegative"))
    op.create_index("ix_submission_grade_items_grade_id", "submission_grade_items", ["grade_id"])


def downgrade():
    for table in ("submission_grade_items", "submission_grades", "task_rubric_items", "task_classes"):
        op.drop_table(table)
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_course_id")
        batch.drop_constraint("fk_tasks_course_id", type_="foreignkey")
        batch.drop_column("course_id")
````

## backend/app/api/deps.py

````python
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str:
    return request.state.request_id


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)], db: Annotated[Session, Depends(get_db)]) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token is required", headers={"WWW-Authenticate": "Bearer"})
    username = decode_access_token(credentials.credentials)
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not available", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if "ADMIN" not in {role.code for role in user.roles}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role is required")
    return user


def require_student(user: Annotated[User, Depends(get_current_user)]) -> User:
    if "STUDENT" not in {role.code for role in user.roles}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student role is required")
    return user


def require_teacher(user: Annotated[User, Depends(get_current_user)]) -> User:
    if "TEACHER" not in {role.code for role in user.roles}:
        raise HTTPException(status_code=403, detail="Teacher role is required")
    return user
````

## backend/app/api/router.py

````python
from fastapi import APIRouter

from app.api.routes import auth, cases, health, viewer, student, teacher

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(viewer.router)
api_router.include_router(student.router)

api_router.include_router(teacher.router)
````

## backend/app/api/routes/student.py

````python
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
from app.services.practice_access import require_open_task, utc
router=APIRouter(prefix="/student",tags=["student"]); settings=get_settings()
def assigned(db,task_id,user):
    task=db.scalar(select(Task).where(Task.id==task_id).with_for_update()); ok=db.scalar(select(TaskAssignment).where(TaskAssignment.task_id==task_id,TaskAssignment.student_id==user.id))
    if not task or not ok or task.status == "DRAFT": raise HTTPException(404,"Task not found")
    return task
def draft(db,task,user): return db.scalar(select(Submission).where(Submission.task_id==task.id,Submission.student_id==user.id,Submission.status=="DRAFT"))
def student_submission(db,t,u): return db.scalar(select(Submission).where(Submission.task_id==t.id,Submission.student_id==u.id).order_by(Submission.created_at.desc()))
def taskdata(db,t,u):
    s=student_submission(db,t,u); v=db.scalar(select(CaseVersion).where(CaseVersion.id==t.case_version_id)); c=db.scalar(select(Case).where(Case.id==v.case_id)) if v else None; now=datetime.now(UTC)
    state="SUBMITTED" if s and s.status=="SUBMITTED" else "CLOSED" if t.status=="CLOSED" else "NOT_STARTED" if t.start_at and now<utc(t.start_at) else "EXPIRED" if t.due_at and now>utc(t.due_at) and not t.allow_late else "IN_PROGRESS"
    return {"id":t.id,"name":t.title,"caseName":c.teaching_title if c else "","instructions":t.instructions,"caseVersionId":t.case_version_id,"startAt":utc(t.start_at),"dueAt":utc(t.due_at),"allowLate":t.allow_late,"status":state,"submissionId":s.id if s and s.status=="SUBMITTED" else None,"submittedAt":s.submitted_at if s else None,"submissionVersion":f"v{s.version_no}" if s else None}
@router.get("/tasks")
def tasks(user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    rows=db.scalars(select(Task).join(TaskAssignment).where(TaskAssignment.student_id==user.id,Task.status!="DRAFT")).all(); return APIResponse(data=[taskdata(db,x,user) for x in rows],request_id=request_id)
@router.get("/tasks/{task_id}")
def task(task_id:str,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)): return APIResponse(data=taskdata(db,assigned(db,task_id,user),user),request_id=request_id)
@router.get("/tasks/{task_id}/workspace")
def workspace(task_id:str,response:Response,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    t=assigned(db,task_id,user); require_open_task(t); v=db.scalar(select(CaseVersion).where(CaseVersion.id==t.case_version_id))
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
    if t.status!="PUBLISHED" or (t.start_at and now<utc(t.start_at)) or (t.due_at and now>utc(t.due_at) and not t.allow_late): raise HTTPException(409,"Task is not editable")
    s=save(db,t,user,payload);db.add(AuditLog(action="DRAFT_SAVED",actor_id=user.id,case_version_id=t.case_version_id,detail={"taskId":t.id,"submissionId":s.id}));db.commit();return APIResponse(data=subdata(db,s),request_id=request_id)
@router.post("/tasks/{task_id}/submissions")
def submit(task_id:str,payload:DraftPayload,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    t=assigned(db,task_id,user); now=datetime.now(UTC)
    if t.status!="PUBLISHED" or (t.start_at and now<utc(t.start_at)) or (t.due_at and now>utc(t.due_at) and not t.allow_late): raise HTTPException(409,"Task submission is closed")
    s=save(db,t,user,payload);s.status="SUBMITTED";s.submitted_at=now;db.add(AuditLog(action="SUBMISSION_CREATED",actor_id=user.id,case_version_id=t.case_version_id,detail={"taskId":t.id,"submissionId":s.id}));db.commit();return APIResponse(data=subdata(db,s),request_id=request_id)
@router.get("/submissions/{submission_id}")
def submission(submission_id:str,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    s=db.scalar(select(Submission).where(Submission.id==submission_id));
    if not s or s.student_id!=user.id: raise HTTPException(404,"Submission not found")
    return APIResponse(data=subdata(db,s),request_id=request_id)

@router.get("/submissions/{submission_id}/grade")
def published_grade(submission_id:str,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    from app.models.teaching import SubmissionGrade
    from app.api.routes.teacher import grade_data, rubric_data
    s=db.get(Submission,submission_id)
    if not s or s.student_id!=user.id: raise HTTPException(404,"Submission not found")
    g=db.scalar(select(SubmissionGrade).where(SubmissionGrade.submission_id==s.id,SubmissionGrade.status=="PUBLISHED"))
    if not g: raise HTTPException(404,"Published grade not found")
    return APIResponse(data={**grade_data(db,g),"rubric":rubric_data(db,s.task_id)},request_id=request_id)
````

## backend/app/api/routes/teacher.py

````python
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
````

## backend/app/api/routes/viewer.py

````python
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_admin
from app.core.config import get_settings
from app.models.case import Annotation, AuditLog, CaseVersion, Measurement
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.viewer import AnnotationCreate, AnnotationData, MeasurementCreate, MeasurementData

router = APIRouter(tags=["viewer"])
settings = get_settings()

def _ready(db: Session, version_id: str) -> CaseVersion:
    item = db.scalar(select(CaseVersion).where(CaseVersion.id == version_id))
    if item is None: raise HTTPException(404, "Case version not found")
    if item.status != "READY" or not item.viewer_manifest_key: raise HTTPException(409, "Viewer is unavailable until conversion is READY")
    return item

def _annotation(item: Annotation) -> AnnotationData:
    return AnnotationData(id=item.id, case_version_id=item.case_version_id, scope=item.scope, type=item.type, geometry=item.geometry, title=item.title, description=item.description, viewer_state=item.viewer_state, created_at=item.created_at, updated_at=item.updated_at)

def _measurement(item: Measurement) -> MeasurementData:
    return MeasurementData(id=item.id, case_version_id=item.case_version_id, start_point=item.start_point, end_point=item.end_point, distance=item.distance, viewer_state=item.viewer_state, created_at=item.created_at, updated_at=item.updated_at)

@router.get("/case-versions/{version_id}/viewer-config")
def viewer_config(version_id: str, response: Response, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    version = _ready(db, version_id)
    exp = datetime.now(UTC) + timedelta(minutes=settings.viewer_token_expire_minutes)
    token = jwt.encode({"sub": str(admin.id), "version": version_id, "exp": exp, "type": "viewer"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    response.set_cookie(f"viewer_{version_id}", token, max_age=settings.viewer_token_expire_minutes * 60, httponly=True, samesite="lax", path=f"{settings.api_v1_prefix}/viewer-assets/{version_id}")
    db.add(AuditLog(action="VIEWER_OPENED", actor_id=admin.id, case_id=version.case_id, case_version_id=version.id))
    db.commit()
    return APIResponse(data={"versionId": version.id, "manifestUrl": f"{settings.api_v1_prefix}/viewer-assets/{version.id}/metadata.json", "initialCamera": {}, "pointBudget": 1000000, "capabilities": {"annotations": True, "measurements": True}}, request_id=request_id)

@router.get("/viewer-assets/{version_id}/{asset_path:path}")
def viewer_asset(version_id: str, asset_path: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    token = request.cookies.get(f"viewer_{version_id}")
    try:
        claims = jwt.decode(token or "", settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if claims.get("type") not in {"viewer", "student_viewer"} or claims.get("version") != version_id: raise ValueError()
    except Exception: raise HTTPException(401, "Viewer asset credential is invalid or expired")
    if claims.get("type") == "student_viewer":
        from app.models.practice import Task
        from app.services.practice_access import require_assignment, require_open_task
        student = db.get(User, int(claims["sub"]))
        if not student or not student.is_active or "STUDENT" not in {r.code for r in student.roles}:
            raise HTTPException(401, "Student is unavailable")
        task = db.get(Task, claims.get("task"))
        require_assignment(db, task, student.id)
        if task.case_version_id != version_id: raise HTTPException(403, "Task version mismatch")
        require_open_task(task)
    version = _ready(db, version_id)
    root = (Path(settings.storage_root).resolve() / "cases" / version.case_id / "versions" / version.id / "potree").resolve()
    target = (root / asset_path).resolve()
    if root not in target.parents and target != root: raise HTTPException(404, "Asset not found")
    if not target.is_file(): raise HTTPException(404, "Asset not found")
    db.add(AuditLog(action="VIEWER_ASSET_ACCESSED", actor_id=int(claims["sub"]), case_id=version.case_id, case_version_id=version.id, detail={"asset": asset_path}))
    db.commit()
    return FileResponse(target)

@router.get("/case-versions/{version_id}/annotations")
def annotations(version_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id)
    rows = db.scalars(select(Annotation).where(Annotation.case_version_id == version_id, Annotation.owner_id == admin.id, Annotation.scope == "ADMIN_WORKSPACE")).all()
    return APIResponse(data=[_annotation(row) for row in rows], request_id=request_id)

@router.post("/case-versions/{version_id}/annotations", status_code=201)
def create_annotation(version_id: str, payload: AnnotationCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id); item = Annotation(case_version_id=version_id, owner_id=admin.id, scope="ADMIN_WORKSPACE", type=payload.type, geometry=payload.geometry, title=payload.title, description=payload.description, viewer_state=payload.viewer_state); db.add(item); db.flush(); db.add(AuditLog(action="ANNOTATION_CREATED", actor_id=admin.id, case_version_id=version_id, detail={"annotationId": item.id})); db.commit(); db.refresh(item); return APIResponse(data=_annotation(item), request_id=request_id)

@router.put("/annotations/{annotation_id}")
def update_annotation(annotation_id: str, payload: AnnotationCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(Annotation).where(Annotation.id == annotation_id));
    if item is None: raise HTTPException(404, "Annotation not found")
    if item.owner_id != admin.id or item.scope != "ADMIN_WORKSPACE": raise HTTPException(403, "Only the owner may modify this annotation")
    for key, value in {"type": payload.type, "geometry": payload.geometry, "title": payload.title, "description": payload.description, "viewer_state": payload.viewer_state}.items(): setattr(item, key, value)
    db.add(AuditLog(action="ANNOTATION_UPDATED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"annotationId": item.id})); db.commit(); db.refresh(item); return APIResponse(data=_annotation(item), request_id=request_id)

@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(Annotation).where(Annotation.id == annotation_id));
    if item is None: raise HTTPException(404, "Annotation not found")
    if item.owner_id != admin.id or item.scope != "ADMIN_WORKSPACE": raise HTTPException(403, "Only the owner may delete this annotation")
    db.add(AuditLog(action="ANNOTATION_DELETED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"annotationId": item.id})); db.delete(item); db.commit(); return APIResponse(data={}, request_id=request_id)

@router.get("/case-versions/{version_id}/measurements")
def measurements(version_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id); rows = db.scalars(select(Measurement).where(Measurement.case_version_id == version_id, Measurement.owner_id == admin.id)).all(); return APIResponse(data=[_measurement(row) for row in rows], request_id=request_id)

@router.post("/case-versions/{version_id}/measurements", status_code=201)
def create_measurement(version_id: str, payload: MeasurementCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id)
    try: distance = math.dist([float(payload.start_point[k]) for k in ("x", "y", "z")], [float(payload.end_point[k]) for k in ("x", "y", "z")])
    except (KeyError, TypeError, ValueError): raise HTTPException(422, "Points must contain numeric x, y, z")
    item = Measurement(case_version_id=version_id, owner_id=admin.id, start_point=payload.start_point, end_point=payload.end_point, distance=distance, viewer_state=payload.viewer_state); db.add(item); db.flush(); db.add(AuditLog(action="MEASUREMENT_CREATED", actor_id=admin.id, case_version_id=version_id, detail={"measurementId": item.id})); db.commit(); db.refresh(item); return APIResponse(data=_measurement(item), request_id=request_id)

@router.delete("/measurements/{measurement_id}")
def delete_measurement(measurement_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(Measurement).where(Measurement.id == measurement_id));
    if item is None: raise HTTPException(404, "Measurement not found")
    if item.owner_id != admin.id: raise HTTPException(403, "Only the owner may delete this measurement")
    db.add(AuditLog(action="MEASUREMENT_DELETED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"measurementId": item.id})); db.delete(item); db.commit(); return APIResponse(data={}, request_id=request_id)
````

## backend/app/models/__init__.py

````python
from app.models.role import Role
from app.models.user import User
from app.models.case import Annotation, AuditLog, Case, CaseVersion, File, Job, Measurement
from app.models.practice import Class, ClassMember, Course, Submission, SubmissionMark, SubmissionMeasurement, Task, TaskAssignment
from app.models.teaching import TaskClass, RubricItem, SubmissionGrade, GradeItem

__all__ = ["Role", "User", "Case", "CaseVersion", "File", "Job", "AuditLog", "Annotation", "Measurement"]
````

## backend/app/models/practice.py

````python
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
    course_id: Mapped[str|None]=mapped_column(ForeignKey("courses.id"),nullable=True,index=True)
    __tablename__="tasks"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); title: Mapped[str]=mapped_column(String(200)); instructions: Mapped[str|None]=mapped_column(Text); case_version_id: Mapped[str]=mapped_column(ForeignKey("case_versions.id")); start_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); allow_late: Mapped[bool]=mapped_column(Boolean,default=False); status: Mapped[str]=mapped_column(String(20),default="PUBLISHED"); report_template: Mapped[dict|None]=mapped_column(JSON); created_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class TaskAssignment(Base):
    __tablename__="task_assignments"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); task_id: Mapped[str]=mapped_column(ForeignKey("tasks.id",ondelete="CASCADE")); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); __table_args__=(UniqueConstraint("task_id","student_id"),)
class Submission(Base):
    __tablename__="submissions"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); task_id: Mapped[str]=mapped_column(ForeignKey("tasks.id",ondelete="CASCADE")); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); status: Mapped[str]=mapped_column(String(20),default="DRAFT"); report_content: Mapped[dict|None]=mapped_column(JSON); submitted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); version_no: Mapped[int]=mapped_column(Integer,default=1); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now()); __table_args__=(UniqueConstraint("task_id","student_id","version_no"),)
class SubmissionMark(Base):
    __tablename__="submission_marks"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); submission_id: Mapped[str]=mapped_column(ForeignKey("submissions.id",ondelete="CASCADE")); geometry: Mapped[dict]=mapped_column(JSON); title: Mapped[str]=mapped_column(String(200)); description: Mapped[str|None]=mapped_column(Text); viewer_state: Mapped[dict|None]=mapped_column(JSON)
class SubmissionMeasurement(Base):
    __tablename__="submission_measurements"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); submission_id: Mapped[str]=mapped_column(ForeignKey("submissions.id",ondelete="CASCADE")); start_point: Mapped[dict]=mapped_column(JSON); end_point: Mapped[dict]=mapped_column(JSON); distance: Mapped[float]=mapped_column(); viewer_state: Mapped[dict|None]=mapped_column(JSON)
````

## backend/app/models/teaching.py

````python
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
````

## backend/app/schemas/teacher.py

````python
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid", str_strip_whitespace=True)


class NameInput(Input):
    name: str = Field(min_length=1, max_length=200)


class MemberInput(Input):
    student_id: int = Field(alias="studentId", gt=0)


class RubricInput(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    max_score: Decimal = Field(alias="maxScore", gt=0, le=99999, max_digits=7, decimal_places=2)


class TaskInput(Input):
    course_id: str = Field(alias="courseId")
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(default="", max_length=20000)
    case_version_id: str = Field(alias="caseVersionId")
    class_ids: list[str] = Field(alias="classIds", min_length=1, max_length=100)
    start_at: datetime | None = Field(default=None, alias="startAt")
    due_at: datetime | None = Field(default=None, alias="dueAt")
    allow_late: bool = Field(default=False, alias="allowLate")
    rubric: list[RubricInput] = Field(min_length=1, max_length=100)

    @field_validator("start_at", "due_at")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Time zone is required")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_at and self.due_at and self.start_at >= self.due_at:
            raise ValueError("Deadline must follow start time")
        if sum(x.max_score for x in self.rubric) > Decimal("99999.99"):
            raise ValueError("Maximum total score exceeded")
        return self


class GradeItemInput(Input):
    rubric_item_id: str = Field(alias="rubricItemId")
    score: Decimal = Field(ge=0, le=99999, max_digits=7, decimal_places=2)
    comment: str = Field(default="", max_length=4000)


class GradeInput(Input):
    feedback: str = Field(default="", max_length=20000)
    items: list[GradeItemInput] = Field(max_length=100)
````

## backend/app/services/practice_access.py

````python
from datetime import UTC, datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models.practice import TaskAssignment


def utc(value):
    """SQLite drops timezone metadata; stored dates are UTC."""
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def require_open_task(task):
    now = datetime.now(UTC)
    if task.status != "PUBLISHED" or (task.start_at and now < utc(task.start_at)) or (task.due_at and now > utc(task.due_at) and not task.allow_late):
        raise HTTPException(409, "Task is not open")


def require_assignment(db, task, student_id):
    if not task or not db.scalar(select(TaskAssignment).where(TaskAssignment.task_id == task.id, TaskAssignment.student_id == student_id)):
        raise HTTPException(404, "Task not found")
````

## backend/requirements-test.txt

````text
-r requirements.txt
httpx>=0.28,<1.0
````

## backend/tests/test_m4.py

````python
"""Run from backend: python -m unittest discover -s tests -v."""
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import Base
from app.main import app
from app.models.case import Case, CaseVersion, File
from app.models.practice import Submission, Task
from app.models.role import Role
from app.models.user import User


class TeachingWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.tmp.name) / 'test.db'), connect_args={'check_same_thread': False})
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        def database():
            with self.sessions() as session:
                yield session
        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)
        with self.sessions.begin() as db:
            roles = {code: Role(code=code, name=code) for code in ('TEACHER','STUDENT','ADMIN')}
            db.add_all(roles.values())
            for name, code in [('teacher','TEACHER'),('other','TEACHER'),('student','STUDENT'),('outsider','STUDENT'),('admin','ADMIN')]:
                db.add(User(username=name, display_name=name, password_hash='unused', roles=[roles[code]]))
            db.flush()
            admin = db.scalar(select(User).where(User.username=='admin'))
            case = Case(title='fixture', teaching_title='教学场景', internal_code='TEST', created_by_id=admin.id)
            db.add(case); db.flush()
            file = File(case_id=case.id, storage_key='test/raw', original_name='fixture.las', mime_type='application/octet-stream', size_bytes=1, checksum_sha256='0'*64)
            db.add(file); db.flush()
            version = CaseVersion(case_id=case.id, source_file_id=file.id, version_number=1, status='READY', viewer_manifest_key='test/metadata.json')
            db.add(version); db.flush(); self.version = version.id

    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); self.engine.dispose(); self.tmp.cleanup()

    def call(self, method, path, data=None, user='teacher', code=200):
        token = create_access_token(user)[0]
        response = self.client.request(method, '/api/v1'+path, json=data, headers={'Authorization':'Bearer '+token})
        self.assertEqual(response.status_code, code, response.text)
        return response.json().get('data')

    def setup_task(self):
        c = self.call('POST','/teacher/courses',{'name':'现场勘验'},code=201)
        g = self.call('POST',f'/teacher/courses/{c["id"]}/classes',{'name':'一班'},code=201)
        student = self.call('GET','/teacher/students?username=student')[0]
        for _ in range(2):
            group = self.call('POST',f'/teacher/classes/{g["id"]}/members',{'studentId':student['id']})
            self.assertEqual(len(group['members']),1)
        now = datetime.now(UTC)
        payload = {'courseId':c['id'],'title':'任务','classIds':[g['id']],'caseVersionId':self.version,'startAt':(now-timedelta(hours=1)).isoformat(),'dueAt':(now+timedelta(days=1)).isoformat(),'rubric':[{'title':'观察','maxScore':'60.10'},{'title':'笔录','maxScore':'39.90'}]}
        task = self.call('POST','/teacher/tasks',payload,code=201)
        self.course_id, self.class_id, self.student_id, self.payload = c['id'],g['id'],student['id'],payload
        return task

    def test_full_workflow_and_ownership(self):
        task = self.setup_task(); tid = task['id']
        self.call('GET',f'/teacher/courses/{self.course_id}',user='other',code=404)
        self.call('PATCH',f'/teacher/classes/{self.class_id}',{'name':'越权'},user='other',code=404)
        self.call('GET','/teacher/courses',user='student',code=403)
        self.call('GET','/teacher/courses',user='admin',code=403)
        self.assertEqual(self.call('GET','/student/tasks',user='student'),[])
        self.call('POST',f'/teacher/tasks/{tid}/publish',user='other',code=404)
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        self.call('PATCH',f'/teacher/tasks/{tid}',self.payload,code=409)
        self.assertEqual(self.call('GET','/student/tasks',user='student')[0]['status'],'IN_PROGRESS')
        self.assertEqual(self.call('GET','/student/tasks',user='outsider'),[])
        self.call('GET',f'/student/tasks/{tid}/workspace',user='outsider',code=404)
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student')
        draft={'reportContent':{'overview':'观察记录'},'marks':[{'geometry':{'position':{'x':1,'y':2,'z':3}},'title':'点位'}],'measurements':[{'startPoint':{'x':0,'y':0,'z':0},'endPoint':{'x':3,'y':4,'z':0},'distance':999}]}
        saved=self.call('PUT',f'/student/tasks/{tid}/draft',draft,user='student')
        self.assertEqual(saved['measurements'][0]['distance'],5)
        self.call('GET',f'/teacher/submissions/{saved["id"]}',code=409)
        submitted=self.call('POST',f'/student/tasks/{tid}/submissions',draft,user='student'); sid=submitted['id']
        self.call('PUT',f'/student/tasks/{tid}/draft',draft,user='student',code=409)
        self.call('POST',f'/student/tasks/{tid}/submissions',draft,user='student',code=409)
        self.call('GET',f'/teacher/submissions/{sid}',user='other',code=404)
        rubric=task['rubric']
        path=f'/teacher/submissions/{sid}/grade'
        self.call('PUT',path,{'items':[{'rubricItemId':rubric[0]['id'],'score':61}]},code=422)
        self.call('PUT',path,{'items':[{'rubricItemId':'foreign','score':1}]},code=422)
        self.call('PUT',path,{'items':[{'rubricItemId':rubric[0]['id'],'score':60.10}]})
        self.call('GET',f'/student/submissions/{sid}/grade',user='student',code=404)
        self.call('POST',path+'/publish',code=409)
        grade={'feedback':'完成良好','items':[{'rubricItemId':r['id'],'score':r['maxScore'],'comment':'达标'} for r in rubric]}
        self.call('PUT',path,grade)
        published=self.call('POST',path+'/publish'); self.assertEqual(float(published['totalScore']),100)
        self.call('PUT',path,grade,code=409)
        self.call('GET',f'/student/submissions/{sid}/grade',user='outsider',code=404)
        self.assertEqual(self.call('GET',f'/student/submissions/{sid}/grade',user='student')['feedback'],'完成良好')
        self.call('POST',f'/teacher/tasks/{tid}/close')
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student',code=409)
        self.call('GET',f'/student/submissions/{sid}',user='student')

    def test_time_boundaries_close_and_asset_revocation(self):
        import jwt
        task=self.setup_task(); tid=task['id']
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        with self.sessions.begin() as db:
            t=db.get(Task,tid); t.start_at=datetime.now(UTC)+timedelta(days=1)
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student',code=409)
        self.call('PUT',f'/student/tasks/{tid}/draft',{'marks':[]},user='student',code=409)
        with self.sessions.begin() as db:
            t=db.get(Task,tid);t.start_at=None;t.due_at=datetime.now(UTC)-timedelta(seconds=1)
        self.assertEqual(self.call('GET','/student/tasks',user='student')[0]['status'],'EXPIRED')
        self.call('POST',f'/student/tasks/{tid}/submissions',{},user='student',code=409)
        with self.sessions.begin() as db: db.get(Task,tid).allow_late=True
        self.call('PUT',f'/student/tasks/{tid}/draft',{},user='student')
        token=jwt.encode({'sub':str(self.student_id),'version':self.version,'task':tid,'type':'student_viewer','exp':datetime.now(UTC)+timedelta(minutes=5)},get_settings().jwt_secret_key,algorithm='HS256')
        self.client.cookies.set(f'viewer_{self.version}',token)
        self.call('POST',f'/teacher/tasks/{tid}/close')
        self.assertEqual(self.call('GET','/student/tasks',user='student')[0]['status'],'CLOSED')
        self.call('PUT',f'/student/tasks/{tid}/draft',{},user='student',code=409)
        self.call('POST',f'/student/tasks/{tid}/submissions',{},user='student',code=409)
        self.call('GET',f'/viewer-assets/{self.version}/metadata.json',user='student',code=409)

    def test_publish_validation_and_assignment_snapshot(self):
        task=self.setup_task(); tid=task['id']
        invalid={**self.payload,'dueAt':self.payload['startAt']}
        self.call('POST','/teacher/tasks',invalid,code=422)
        self.call('POST',f'/teacher/classes/{self.class_id}/members',{'studentId':999999},code=422)
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        self.call('POST',f'/teacher/tasks/{tid}/publish',code=409)
        self.call('DELETE',f'/teacher/classes/{self.class_id}/members/{self.student_id}')
        self.assertEqual(len(self.call('GET','/student/tasks',user='student')),1)
        other=self.call('POST','/teacher/courses',{'name':'其他教师'},user='other',code=201)
        group=self.call('POST',f'/teacher/courses/{other["id"]}/classes',{'name':'其他班'},user='other',code=201)
        self.call('POST','/teacher/tasks',{**self.payload,'classIds':[group['id']]},code=404)

    def test_migration_preserves_m3_rows_and_downgrades(self):
        from sqlalchemy import inspect, text
        settings=get_settings(); previous=settings.database_url
        url='sqlite:///'+str(Path(self.tmp.name)/'migration.db')
        settings.database_url=url
        config=Config('alembic.ini')
        migrated=create_engine(url)
        try:
            command.upgrade(config,'202610300005')
            with migrated.begin() as db:
                db.execute(text("INSERT INTO courses(id,name,created_by) VALUES ('legacy-course','M3 course',NULL)"))
                db.execute(text("INSERT INTO tasks(id,title,status) VALUES ('legacy-task','M3 task','PUBLISHED')"))
            command.upgrade(config,'head')
            with migrated.connect() as db:
                self.assertEqual(db.execute(text("SELECT course_id FROM tasks WHERE id='legacy-task'")).scalar(),None)
                self.assertEqual(db.execute(text("SELECT title FROM tasks WHERE id='legacy-task'")).scalar(),'M3 task')
            self.assertIn('submission_grades',inspect(migrated).get_table_names())
            command.downgrade(config,'202610300005')
            self.assertNotIn('course_id',[c['name'] for c in inspect(migrated).get_columns('tasks')])
            with migrated.connect() as db:
                self.assertEqual(db.execute(text('SELECT count(*) FROM tasks')).scalar(),1)
        finally:
            settings.database_url=previous; migrated.dispose()


if __name__ == '__main__':
    unittest.main()
````

## docs/m4/migration.postgresql.sql

````sql
-- M4 only; run on M3 revision 202610300005. Prefer alembic upgrade head.
BEGIN;

-- Running upgrade 202610300005 -> 202610310006

ALTER TABLE tasks ADD COLUMN course_id VARCHAR(36);

ALTER TABLE tasks ADD CONSTRAINT fk_tasks_course_id FOREIGN KEY(course_id) REFERENCES courses (id);

CREATE INDEX ix_tasks_course_id ON tasks (course_id);

CREATE TABLE task_classes (
    id VARCHAR(36) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    class_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (task_id, class_id),
    FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES classes (id)
);

CREATE INDEX ix_task_classes_task_id ON task_classes (task_id);

CREATE TABLE task_rubric_items (
    id VARCHAR(36) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    max_score NUMERIC(7, 2) NOT NULL,
    sort_order INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_rubric_positive CHECK (max_score > 0),
    FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

CREATE INDEX ix_task_rubric_items_task_id ON task_rubric_items (task_id);

CREATE TABLE submission_grades (
    id VARCHAR(36) NOT NULL,
    submission_id VARCHAR(36) NOT NULL,
    graded_by INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_score NUMERIC(7, 2) NOT NULL,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT ck_grade_nonnegative CHECK (total_score >= 0),
    UNIQUE (submission_id),
    FOREIGN KEY(submission_id) REFERENCES submissions (id),
    FOREIGN KEY(graded_by) REFERENCES users (id)
);

CREATE TABLE submission_grade_items (
    id VARCHAR(36) NOT NULL,
    grade_id VARCHAR(36) NOT NULL,
    rubric_item_id VARCHAR(36) NOT NULL,
    score NUMERIC(7, 2) NOT NULL,
    comment TEXT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (grade_id, rubric_item_id),
    CONSTRAINT ck_grade_item_nonnegative CHECK (score >= 0),
    FOREIGN KEY(grade_id) REFERENCES submission_grades (id) ON DELETE CASCADE,
    FOREIGN KEY(rubric_item_id) REFERENCES task_rubric_items (id)
);

CREATE INDEX ix_submission_grade_items_grade_id ON submission_grade_items (grade_id);

UPDATE alembic_version SET version_num='202610310006' WHERE alembic_version.version_num = '202610300005';

COMMIT;
````

## frontend/src/api/student.ts

````typescript
import http, { responseData } from '@/api/http'
import type { DraftResponse, StudentDraftPayload, StudentTask, StudentWorkspace, Submission } from '@/types/student'
import type { Annotation, Measurement } from '@/types/viewer'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const key = (suffix: string) => `dici.mock-student-${suffix}`
const wait = (ms = 180) => new Promise((resolve) => window.setTimeout(resolve, ms))
const emptyWorkspace = (): StudentWorkspace => ({ manifestUrl: '', draft: { overview: '', process: '', evidenceDescription: '', preliminaryConclusion: '' }, annotations: [], measurements: [], submitted: false, submittedAt: null, submissionVersion: null })
interface WorkspaceResponse { task: StudentTask; draft: DraftResponse | null; viewerConfig: { versionId: string; manifestUrl: string } }
function toWorkspace(response: WorkspaceResponse): StudentWorkspace { const draft = response.draft; return { manifestUrl: response.viewerConfig.manifestUrl, draft: draft?.reportContent || emptyWorkspace().draft, annotations: draft?.marks || [], measurements: draft?.measurements || [], submitted: draft?.status === 'SUBMITTED', submittedAt: draft?.submittedAt || null, submissionVersion: draft?.version || null } }
function toPayload(workspace: StudentWorkspace): StudentDraftPayload { return { reportContent: workspace.draft, marks: workspace.annotations, measurements: workspace.measurements } }
export async function getSubmittedWork(submissionId: string): Promise<DraftResponse> {
  if (!useMock) return responseData<DraftResponse>(await http.get(`/api/v1/student/submissions/${submissionId}`))
  const t = mockTasks().find(t => t.submissionId === submissionId)
  if (!t) throw new Error('提交不存在')
  const w = mockWorkspace(t.id)
  return { id: submissionId, status: 'SUBMITTED', reportContent: w.draft, marks: w.annotations, measurements: w.measurements, submittedAt: w.submittedAt, version: w.submissionVersion }
}
function applyDraftResponse(workspace: StudentWorkspace, draft: DraftResponse): StudentWorkspace { return { ...workspace, draft: draft.reportContent, annotations: draft.marks, measurements: draft.measurements, submitted: draft.status === 'SUBMITTED', submittedAt: draft.submittedAt, submissionVersion: draft.version } }
function mockTasks(): StudentTask[] { const raw = localStorage.getItem(key('tasks')); if (raw) return JSON.parse(raw) as StudentTask[]; const tasks: StudentTask[] = [{ id: 'mock-task-001', name: '住宅现场勘查实训', caseName: '教学演示案例', instructions: '完成现场观察、标记与勘验笔录。', caseVersionId: 'mock-version-001', startAt: '2026-10-01T08:00:00+08:00', dueAt: '2026-12-31T23:59:59+08:00', status: 'IN_PROGRESS', allowLate: false, submissionId: null, submittedAt: null, submissionVersion: null }]; localStorage.setItem(key('tasks'), JSON.stringify(tasks)); return tasks }
function mockWorkspace(taskId: string): StudentWorkspace { const raw = localStorage.getItem(key(`workspace-${taskId}`)); if (raw) return JSON.parse(raw); const workspace = emptyWorkspace(); localStorage.setItem(key(`workspace-${taskId}`), JSON.stringify(workspace)); return workspace }
function saveWorkspace(taskId: string, value: StudentWorkspace) { localStorage.setItem(key(`workspace-${taskId}`), JSON.stringify(value)) }
function task(taskId: string) { const item = mockTasks().find((value) => value.id === taskId); if (!item) throw new Error('实训任务不存在'); return item }

export async function getStudentTasks(): Promise<StudentTask[]> { if (!useMock) return responseData<StudentTask[]>(await http.get('/api/v1/student/tasks')); await wait(); return mockTasks() }
export async function getStudentTask(taskId: string): Promise<StudentTask> { if (!useMock) return responseData<StudentTask>(await http.get(`/api/v1/student/tasks/${taskId}`)); await wait(); return task(taskId) }
export async function getStudentWorkspace(taskId: string): Promise<StudentWorkspace> { if (!useMock) return toWorkspace(responseData<WorkspaceResponse>(await http.get(`/api/v1/student/tasks/${taskId}/workspace`))); await wait(); return mockWorkspace(taskId) }
export async function saveStudentDraft(taskId: string, workspace: StudentWorkspace): Promise<StudentWorkspace> { if (!useMock) { const response = responseData<DraftResponse>(await http.put(`/api/v1/student/tasks/${taskId}/draft`, toPayload(workspace))); return applyDraftResponse(workspace, response) } await wait(280); saveWorkspace(taskId, workspace); return workspace }
export async function submitStudentTask(taskId: string, workspace: StudentWorkspace): Promise<Submission> { if (!useMock) { const response = responseData<DraftResponse>(await http.post(`/api/v1/student/tasks/${taskId}/submissions`, toPayload(workspace))); return { id: response.id, submittedAt: response.submittedAt || new Date().toISOString(), version: response.version || '' } } await wait(350); const submittedAt = new Date().toISOString(); workspace.submitted = true; workspace.submittedAt = submittedAt; workspace.submissionVersion = 'v1'; saveWorkspace(taskId, workspace); const tasks = mockTasks(); const item = task(taskId); item.status = 'SUBMITTED'; item.submittedAt = submittedAt; item.submissionVersion = 'v1'; item.submissionId = `mock-submission-${Date.now()}`; localStorage.setItem(key('tasks'), JSON.stringify(tasks)); return { id: item.submissionId, submittedAt, version: 'v1' } }
export async function getStudentSubmission(submissionId: string): Promise<Submission> { if (!useMock) return responseData<Submission>(await http.get(`/api/v1/student/submissions/${submissionId}`)); await wait(); const item = mockTasks().find((value) => value.submissionId === submissionId); if (!item?.submittedAt || !item.submissionVersion) throw new Error('提交记录不存在'); return { id: submissionId, submittedAt: item.submittedAt, version: item.submissionVersion } }
````

## frontend/src/api/teacher.ts

````typescript
import http, { responseData } from '@/api/http'
import type { Course, Grade, Review, Student, SubmissionRow, TaskForm, TeachingClass, TeachingTask } from '@/types/teacher'
import { teacherMock } from './teacherMock'

const base = '/api/v1/teacher'
const mock = import.meta.env.VITE_USE_MOCK !== 'false'
export async function get<T>(path: string): Promise<T> { return mock ? teacherMock<T>('GET',path) : responseData<T>(await http.get(base + path)) }
export async function post<T>(path: string, data: unknown = {}): Promise<T> { return mock ? teacherMock<T>('POST',path,data) : responseData<T>(await http.post(base + path, data)) }
export async function patch<T>(path: string, data: unknown): Promise<T> { return mock ? teacherMock<T>('PATCH',path,data) : responseData<T>(await http.patch(base + path, data)) }
export const courses = () => get<Course[]>('/courses')
export const course = (id: string) => get<Course>(`/courses/${id}`)
export const teachingClass = (id: string) => get<TeachingClass>(`/classes/${id}`)
export const findStudent = (name: string) => get<Student[]>(`/students?username=${encodeURIComponent(name)}`)
export async function removeMember(classId: string, studentId: number) { if(mock) await teacherMock('DELETE',`/classes/${classId}/members/${studentId}`); else await http.delete(`${base}/classes/${classId}/members/${studentId}`) }
export const tasks = (courseId: string, status: string) => get<TeachingTask[]>(`/tasks?courseId=${encodeURIComponent(courseId)}&status=${status}`)
export const task = (id: string) => get<TeachingTask>(`/tasks/${id}`)
export function saveTask(id: string | undefined, form: TaskForm) { const payload = { ...form, rubric: form.rubric.map(({ title, description, maxScore }) => ({ title, description, maxScore })) }; return id ? patch<TeachingTask>(`/tasks/${id}`, payload) : post<TeachingTask>('/tasks', payload) }
export const submissions = (id: string) => get<SubmissionRow[]>(`/tasks/${id}/submissions`)
export const review = (id: string) => get<Review>(`/submissions/${id}`)
export async function saveGrade(id: string, feedback: string, items: Grade['items']) { return responseData<Grade>(await http.put(`${base}/submissions/${id}/grade`, { feedback, items: items.filter(i => i.score !== null && i.score !== undefined) })) }
export function message(error: unknown) { return (error as { response?: { data?: { message?: string } } }).response?.data?.message || (error instanceof Error ? error.message : '操作失败') }
````

## frontend/src/api/teacherMock.ts

````typescript
/** UI-only demo storage, isolated per mock teacher. Real authorization is server-side. */
import type { Course, Student, TaskForm, TeachingClass, TeachingTask } from '@/types/teacher'

interface State { courses: Course[]; classes: TeachingClass[]; tasks: TeachingTask[] }
const uid = () => crypto.randomUUID()
export async function teacherMock<T>(method: string, path: string, payload: unknown = {}): Promise<T> {
  const key = `dici.mock-teacher-${localStorage.getItem('dici.access-token')}`
  const state: State = JSON.parse(localStorage.getItem(key) || '{"courses":[],"classes":[],"tasks":[]}')
  const [pathname, query] = path.split('?'), parts = pathname.split('/').filter(Boolean)
  const body = payload as Record<string, unknown>
  const course = () => { const item=state.courses.find(c=>c.id===parts[1]);if(!item)throw new Error('课程不存在');return item }
  const group = () => { const item=state.classes.find(c=>c.id===parts[1]);if(!item)throw new Error('班级不存在');return item }
  const task = () => { const item=state.tasks.find(t=>t.id===parts[1]);if(!item)throw new Error('任务不存在');return item }
  let data: unknown
  if(parts[0]==='courses') {
    if(parts.length===1) {
      if(method==='POST'){const c={id:uid(),name:String(body.name),classes:[]};state.courses.push(c);data=c}else data=state.courses
    } else if(parts[2]==='classes') {
      const c=course(), g={id:uid(),courseId:c.id,name:String(body.name),members:[]};state.classes.push(g);c.classes.push({id:g.id,name:g.name});data=g
    } else {const c=course();if(method==='PATCH')c.name=String(body.name);data=c}
  } else if(parts[0]==='classes') {
    const g=group()
    if(parts[2]==='members') {
      if(method==='DELETE')g.members=g.members.filter(s=>s.id!==Number(parts[3]))
      else if(!g.members.some(s=>s.id===Number(body.studentId)))g.members.push({id:Number(body.studentId),username:'student',displayName:'演示学生'})
    } else if(method==='PATCH'){g.name=String(body.name);const c=state.courses.find(c=>c.id===g.courseId)?.classes.find(c=>c.id===g.id);if(c)c.name=g.name}
    data=g
  } else if(parts[0]==='students') {
    const name=new URLSearchParams(query).get('username');data=name==='student'?[{id:1,username:'student',displayName:'演示学生'} satisfies Student]:[]
  } else if(parts[0]==='case-versions') data=[{id:'mock-version-001',teachingTitle:'教学演示案例',versionNumber:1}]
  else if(parts[0]==='tasks') {
    if(parts.length===1){
      if(method==='POST'){const t={...(payload as TaskForm),id:uid(),status:'DRAFT',assignedCount:0,submittedCount:0};t.rubric=t.rubric.map(r=>({...r,id:uid()}));state.tasks.push(t);data=t}
      else {const q=new URLSearchParams(query);data=state.tasks.filter(t=>(!q.get('courseId')||t.courseId===q.get('courseId'))&&(!q.get('status')||t.status===q.get('status')))}
    } else {const t=task()
      if(parts[2]==='submissions')data=[]
      else if(parts[2]==='publish'){if(t.status!=='DRAFT')throw new Error('只有草稿可发布');const members=new Set(t.classIds.flatMap(id=>state.classes.find(c=>c.id===id)?.members.map(s=>s.id)||[]));if(!members.size)throw new Error('请先添加班级学生');t.status='PUBLISHED';t.assignedCount=members.size;data=t}
      else if(parts[2]==='close'){if(t.status!=='PUBLISHED')throw new Error('任务尚未发布');t.status='CLOSED';data=t}
      else {if(method==='PATCH'){if(t.status!=='DRAFT')throw new Error('任务已冻结');Object.assign(t,payload);t.rubric=t.rubric.map(r=>({...r,id:uid()}))}data=t}
    }
  } else throw new Error('模拟模式不提供真实作业批改，请关闭 Mock 后联调')
  localStorage.setItem(key,JSON.stringify(state))
  return structuredClone(data) as T
}
````

## frontend/src/router/index.ts

````typescript
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types/auth'
import { homeRouteForRoles } from '@/utils/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guestOnly: true } },
  { path: '/admin', name: 'admin', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases', name: 'admin-cases', component: () => import('@/views/CaseListView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases/new', name: 'admin-case-new', component: () => import('@/views/CaseCreateView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases/:caseId', name: 'admin-case-detail', component: () => import('@/views/CaseDetailView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/admin/cases/:caseId/viewer', name: 'admin-case-viewer', component: () => import('@/views/CaseViewerView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
  { path: '/teacher/courses', name: 'teacher-courses', component: () => import('@/views/TeacherCoursesView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/courses/:courseId', name: 'teacher-course', component: () => import('@/views/TeacherCoursesView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/tasks', name: 'teacher-tasks', component: () => import('@/views/TeacherTasksView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/tasks/new', name: 'teacher-task-new', component: () => import('@/views/TeacherTaskDetailView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/tasks/:taskId', name: 'teacher-task', component: () => import('@/views/TeacherTaskDetailView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/teacher/submissions/:submissionId', name: 'teacher-review', component: () => import('@/views/TeacherSubmissionView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/student/submissions/:submissionId', name: 'student-submission', component: () => import('@/views/StudentSubmissionView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/teacher', name: 'teacher', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, roles: ['TEACHER'] } },
  { path: '/student', name: 'student', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/student/tasks', name: 'student-tasks', component: () => import('@/views/StudentTaskListView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/student/tasks/:taskId', name: 'student-task-workspace', component: () => import('@/views/StudentWorkspaceView.vue'), meta: { requiresAuth: true, roles: ['STUDENT'] } },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.restore()
  if (to.meta.guestOnly && auth.isAuthenticated) return homeRouteForRoles(auth.user?.roles)
  if (!to.meta.requiresAuth) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
  const roles = (to.meta.roles as string[] | undefined) || []
  if (!roles.some((role) => auth.user?.roles.includes(role as UserRole))) return homeRouteForRoles(auth.user?.roles)
  return true
})

export default router
````

## frontend/src/styles/main.css

````css
:root { font-family: Inter, "Microsoft YaHei", Arial, sans-serif; color: #172033; background: #f4f7fb; }
* { box-sizing: border-box; }
body { min-width: 320px; min-height: 100vh; margin: 0; }
button, input { font: inherit; }

.teacher-page{max-width:1200px;margin:auto;padding:32px}.teacher-page header{display:flex;align-items:center;gap:16px;margin-bottom:24px}.teacher-page h1{flex:1}.teacher-page .el-card{margin-top:24px}.teacher-page .el-form{max-width:900px}.teacher-page pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px}.teacher-page .actions{display:flex;gap:12px;margin:20px 0}.teacher-page .rubric-row{display:flex;gap:12px;align-items:center;margin-bottom:12px}
````

## frontend/src/types/student.ts

````typescript
import type { Annotation, Measurement } from '@/types/viewer'

export type StudentTaskStatus = 'CLOSED' | 'NOT_STARTED' | 'IN_PROGRESS' | 'EXPIRED' | 'SUBMITTED'
export interface RecordDraft { overview: string; process: string; evidenceDescription: string; preliminaryConclusion: string }
export interface StudentTask { id: string; name: string; caseName: string; instructions: string; caseVersionId: string; startAt: string | null; dueAt: string | null; status: StudentTaskStatus; allowLate: boolean; submissionId: string | null; submittedAt: string | null; submissionVersion: string | null }
export interface StudentWorkspace { manifestUrl: string; draft: RecordDraft; annotations: Annotation[]; measurements: Measurement[]; submitted: boolean; submittedAt: string | null; submissionVersion: string | null }
export interface Submission { id: string; submittedAt: string; version: string }
export interface StudentDraftPayload { reportContent: RecordDraft; marks: Annotation[]; measurements: Measurement[] }
export interface DraftResponse { id: string; status: string; reportContent: RecordDraft; marks: Annotation[]; measurements: Measurement[]; submittedAt: string | null; version: string | null }
````

## frontend/src/types/teacher.ts

````typescript
export interface Student { id: number; username: string; displayName: string }
export interface Course { id: string; name: string; classes: { id: string; name: string }[] }
export interface TeachingClass { id: string; courseId: string; name: string; members: Student[] }
export interface Rubric { id?: string; title: string; description?: string | null; maxScore: number | string }
export interface TaskForm { courseId: string; title: string; instructions: string; caseVersionId: string; classIds: string[]; startAt: string | null; dueAt: string | null; allowLate: boolean; rubric: Rubric[] }
export interface TeachingTask extends TaskForm { id: string; status: string; assignedCount?: number; submittedCount?: number }
export interface GradeItem { rubricItemId: string; score: number | string | null; comment: string }
export interface Grade { status: string; totalScore: number | string; feedback: string; items: GradeItem[]; publishedAt: string | null; rubric?: Rubric[] }
export interface SubmissionRow { student: Student; submissionId: string | null; status: string; submittedAt: string | null; gradeStatus: string | null; totalScore: number | string | null }
export interface Review { student: Student; task: TeachingTask; submission: { id: string; reportContent: Record<string, unknown>; marks: { id: string; title: string; description: string; geometry: unknown }[]; measurements: { id: string; startPoint: unknown; endPoint: unknown; distance: number }[] }; grade: Grade | null }
````

## frontend/src/utils/student.ts

````typescript
import type { StudentTaskStatus } from '@/types/student'
export const taskStatus = (status: StudentTaskStatus) => ({ CLOSED: ['已关闭', 'info'], NOT_STARTED: ['未开始', 'info'], IN_PROGRESS: ['进行中', 'primary'], EXPIRED: ['已截止', 'danger'], SUBMITTED: ['已提交', 'success'] }[status] as [string, 'info' | 'primary' | 'danger' | 'success'])
export const displayTime = (time: string | null) => time ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(time)) : '-'
````

## frontend/src/views/HomeView.vue

````vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { roleLabel } from '@/utils/auth'

const mock = import.meta.env.VITE_USE_MOCK !== 'false'
const router = useRouter()
const auth = useAuthStore()
const user = computed(() => auth.user)
const roles = computed(() => roleLabel(user.value?.roles))
const isAdmin = computed(() => user.value?.roles.includes('ADMIN'))
const isTeacher = computed(() => user.value?.roles.includes('TEACHER'))
const isStudent = computed(() => user.value?.roles.includes('STUDENT'))

async function logout() {
  auth.clear()
  await router.replace('/login')
}
</script>

<template>
  <main class="home-page">
    <el-card class="home-card">
      <div class="topline">
        <div><p class="eyebrow">数智刑勘平台</p><h1>{{ roles }}首页</h1></div>
        <el-button plain @click="logout">退出登录</el-button>
      </div>
      <el-alert v-if="isTeacher && mock" title="模拟模式：教师数据仅保存在本浏览器，查找学生使用 student；真实任务分配和批改请设置 VITE_USE_MOCK=false。" type="warning" :closable="false"/>
      <el-divider />
      <p>当前用户：<strong>{{ user?.displayName || user?.username }}</strong></p>
      <p>当前角色：<el-tag type="primary">{{ roles }}</el-tag></p>
      <el-button v-if="isAdmin" type="primary" @click="router.push('/admin/cases')">案例管理</el-button>
      <el-button v-if="isStudent" type="primary" @click="router.push('/student/tasks')">我的实训任务</el-button>
      <el-button v-if="isTeacher" type="primary" @click="router.push('/teacher/courses')">课程管理</el-button>
      <el-button v-if="isTeacher" @click="router.push('/teacher/tasks')">教学任务</el-button>
      <el-empty description="模块开发中" :image-size="100" />
    </el-card>
  </main>
</template>

<style scoped>
.home-page { min-height: 100vh; padding: 48px 24px; background: #f4f7fb; }
.home-card { max-width: 760px; margin: 0 auto; }
.topline { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.eyebrow { margin: 0 0 8px; color: #6b7b91; font-size: 13px; }
h1 { margin: 0; color: #142d4d; font-size: 25px; }
</style>
````

## frontend/src/views/StudentSubmissionView.vue

````vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http, { responseData } from '@/api/http'
import { getSubmittedWork } from '@/api/student'
import { message } from '@/api/teacher'
import type { Grade } from '@/types/teacher'
import type { DraftResponse } from '@/types/student'
const route=useRoute(), submission=ref<DraftResponse>(), grade=ref<Grade>(), error=ref(''), notice=ref(''), busy=ref(false)
const labels:Record<string,string>={overview:'现场概况',process:'勘验过程',evidenceDescription:'物证描述',preliminaryConclusion:'初步结论'}
onMounted(async()=>{busy.value=true;const path=`/api/v1/student/submissions/${route.params.submissionId}`;try{submission.value=await getSubmittedWork(String(route.params.submissionId));if(import.meta.env.VITE_USE_MOCK!=='false'){notice.value='模拟模式不包含教师真实评分';return}try{grade.value=responseData<Grade>(await http.get(`${path}/grade`))}catch(e){notice.value=(e as {response?:{status:number}}).response?.status===404?'教师尚未发布成绩':message(e)}}catch(e){error.value=message(e)}finally{busy.value=false}})
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>我的提交与成绩</h1><el-button @click="$router.push('/student/tasks')">返回任务</el-button></header><el-alert v-if="error" :title="error" type="error"/><el-card v-if="submission"><h2>勘验笔录</h2><section v-for="(value,key) in submission.reportContent" :key="key"><b>{{labels[key]||key}}</b><pre>{{value}}</pre></section><h3>标记</h3><div v-for="m in submission.marks" :key="m.id"><b>{{m.title}}</b><p>{{m.description}}</p><pre>{{m.geometry}}</pre></div><h3>测距</h3><pre v-for="m in submission.measurements" :key="m.id">{{m.startPoint}} → {{m.endPoint}}</pre></el-card><el-alert v-if="notice" :title="notice" type="info" :closable="false"/><el-card v-if="grade"><h2>成绩：{{grade.totalScore}}</h2><p>{{grade.feedback||'无总评'}}</p><div v-for="r in grade.rubric" :key="r.id"><h3>{{r.title}} · {{grade.items.find(i=>i.rubricItemId===r.id)?.score}} / {{r.maxScore}}</h3><p>{{grade.items.find(i=>i.rubricItemId===r.id)?.comment||'无单项反馈'}}</p></div></el-card></main></template>
````

## frontend/src/views/StudentTaskListView.vue

````vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudentTasks } from '@/api/student'
import type { StudentTask } from '@/types/student'
import { displayTime, taskStatus } from '@/utils/student'

const tasks = ref<StudentTask[]>([]); const loading = ref(false)
async function load(){ loading.value=true; try { tasks.value=await getStudentTasks() } catch(e) { ElMessage.error(e instanceof Error?e.message:'任务加载失败') } finally { loading.value=false } }
onMounted(load)
</script>
<template><main class="page"><div class="head"><div><p>学生 / 我的实训</p><h1>我的实训任务</h1></div><el-button @click="load">刷新</el-button></div><el-card shadow="never"><el-table :data="tasks" v-loading="loading"><el-table-column prop="name" label="任务名称" min-width="180"/><el-table-column prop="caseName" label="案例名称" min-width="160"/><el-table-column label="开始/截止时间" min-width="300"><template #default="{row}">{{ displayTime(row.startAt) }}<br><span class="muted">截止：{{ displayTime(row.dueAt) }}</span></template></el-table-column><el-table-column label="状态" width="110"><template #default="{row}"><el-tag :type="taskStatus(row.status)[1]">{{ taskStatus(row.status)[0] }}</el-tag></template></el-table-column><el-table-column label="允许迟交" width="100"><template #default="{row}">{{ row.allowLate?'是':'否' }}</template></el-table-column><el-table-column label="操作" width="210" fixed="right"><template #default="{row}"><el-button v-if="row.submissionId" link type="primary" @click="$router.push(`/student/submissions/${row.submissionId}`)">作业与成绩</el-button><el-button v-if="row.status==='IN_PROGRESS'" link type="primary" @click="$router.push(`/student/tasks/${row.id}`)">{{ row.status==='SUBMITTED'?'查看提交':'进入实训' }}</el-button></template></el-table-column></el-table><el-empty v-if="!loading&&!tasks.length" description="暂无实训任务"/></el-card></main></template>
<style scoped>.page{max-width:1440px;min-height:100vh;margin:auto;padding:36px 32px}.head{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.head p{margin:0;color:#64748b;font-size:13px}h1{margin:7px 0;font-size:27px;color:#142d4d}.muted{color:#8491a3;font-size:12px}@media(max-width:720px){.page{padding:24px 16px}}</style>
````

## frontend/src/views/StudentWorkspaceView.vue

````vue
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import PotreeFrame from '@/components/PotreeFrame.vue'
import { getStudentTask, getStudentWorkspace, saveStudentDraft, submitStudentTask } from '@/api/student'
import type { StudentTask, StudentWorkspace } from '@/types/student'
import type { Annotation, Measurement, Point3D } from '@/types/viewer'
import { displayTime } from '@/utils/student'

const route=useRoute(),router=useRouter(),frame=ref<InstanceType<typeof PotreeFrame>>();const task=ref<StudentTask>();const workspace=ref<StudentWorkspace>();const loading=ref(true),viewerError=ref(''),saveState=ref<'saved'|'saving'|'unsaved'|'failed'>('saved'),lastSaved=ref(''),timer=ref<number>();const camera=ref<Record<string,unknown>>({});const mock=import.meta.env.VITE_USE_MOCK!=='false';const point=ref<Point3D>({x:0,y:0,z:0});const pointTitle=ref('');const pointDescription=ref('');const areaTitle=ref('重点区域');const measure=ref({startPoint:{x:0,y:0,z:0},endPoint:{x:3,y:4,z:0}})
const readonly=computed(()=>Boolean(task.value?.status==='CLOSED'||workspace.value?.submitted||task.value?.status==='NOT_STARTED'||(task.value?.status==='EXPIRED'&&!task.value.allowLate)));const taskId=()=>String(route.params.taskId);const distance=computed(()=>Math.hypot(measure.value.startPoint.x-measure.value.endPoint.x,measure.value.startPoint.y-measure.value.endPoint.y,measure.value.startPoint.z-measure.value.endPoint.z).toFixed(2))
async function load(){loading.value=true;try{const [t,w]=await Promise.all([getStudentTask(taskId()),getStudentWorkspace(taskId())]);task.value=t;workspace.value=w;lastSaved.value=new Date().toLocaleString('zh-CN')}catch(e){viewerError.value=e instanceof Error?e.message:'实训工作台加载失败'}finally{loading.value=false}}
function schedule(){if(readonly.value||!workspace.value)return;saveState.value='unsaved';if(timer.value)window.clearTimeout(timer.value);timer.value=window.setTimeout(save,900)}
async function save(){if(readonly.value||!workspace.value)return false;if(timer.value)window.clearTimeout(timer.value);saveState.value='saving';try{workspace.value=await saveStudentDraft(taskId(),workspace.value);saveState.value='saved';lastSaved.value=new Date().toLocaleString('zh-CN');return true}catch(error){saveState.value='failed';const status=(error as { response?: { status?: number } }).response?.status;ElMessage.error(status===409?'当前任务状态不允许保存，请刷新后重试。':'草稿自动保存失败，请检查网络后重试');return false}}
function picked(value:Point3D){point.value=value;ElMessage.success('已获取点位坐标')};function measured(v:{startPoint:Point3D;endPoint:Point3D}){measure.value=v;ElMessage.success('已获取两点坐标')};function selectedArea(v:{center:[number,number,number];size:[number,number,number];rotation:[number,number,number]}){if(!workspace.value)return;workspace.value.annotations.unshift({id:`local-area-${Date.now()}`,type:'AREA_MARK',geometry:v,title:areaTitle.value,description:'',viewerState:{camera:camera.value},createdAt:new Date().toISOString()});schedule()}
function addPoint(){if(!workspace.value||!pointTitle.value.trim()){ElMessage.warning('请输入标记标题');return}workspace.value.annotations.unshift({id:`local-point-${Date.now()}`,type:'POINT_MARK',geometry:{position:point.value},title:pointTitle.value,description:pointDescription.value,viewerState:{camera:camera.value},createdAt:new Date().toISOString()});pointTitle.value='';pointDescription.value='';schedule()}
function addMeasure(){if(!workspace.value)return;workspace.value.measurements.unshift({id:`local-measure-${Date.now()}`,...measure.value,createdAt:new Date().toISOString()});schedule()}function removeAnnotation(item:Annotation){if(!workspace.value)return;workspace.value.annotations=workspace.value.annotations.filter(v=>v.id!==item.id);schedule()}function removeMeasurement(item:Measurement){if(!workspace.value)return;workspace.value.measurements=workspace.value.measurements.filter(v=>v.id!==item.id);schedule()}
async function submit(){if(readonly.value)return;await ElMessageBox.confirm('提交后将无法再编辑笔录、标记和测距记录，是否确认提交？','确认提交',{type:'warning'});if(!await save()||!workspace.value)return;try{const result=await submitStudentTask(taskId(),workspace.value);workspace.value.submitted=true;workspace.value.submittedAt=result.submittedAt;workspace.value.submissionVersion=result.version;if(task.value){task.value.status='SUBMITTED';task.value.submittedAt=result.submittedAt;task.value.submissionVersion=result.version}ElMessage.success('实训已提交')}catch(e){const status=(e as { response?: { status?: number } }).response?.status;ElMessage.error(status===409?'当前任务状态不允许提交，请刷新后重试。':e instanceof Error?e.message:'提交失败')}}
onMounted(load);onBeforeUnmount(()=>{if(timer.value)window.clearTimeout(timer.value)})
</script>
<template><main class="workspace"><header><div><p>学生 / 实训工作台</p><h1>{{ task?.name||'实训工作台' }}</h1></div><div><el-tag v-if="mock" type="warning">模拟 Viewer 模式</el-tag><el-tag v-if="readonly" type="info">只读</el-tag><el-button @click="router.push('/student/tasks')">返回任务</el-button></div></header><el-alert v-if="task?.status==='NOT_STARTED'" title="任务尚未开始" description="请在开始时间后进入实训并提交。" type="info" :closable="false" show-icon/><el-alert v-if="viewerError" title="无法加载实训工作台" :description="viewerError" type="error" :closable="false" show-icon/><el-skeleton v-else-if="loading" :rows="12" animated/><section v-else-if="workspace" class="layout"><div class="viewer"><PotreeFrame ref="frame" :manifest-url="workspace.manifestUrl" :mock="mock" @error="viewerError=$event" @camera="camera=$event" @pick="picked" @measurement="measured" @area="selectedArea"/></div><aside><el-alert v-if="mock" title="模拟 Viewer 模式" description="未加载或伪造真实点云，仅演示学生实训数据流。" type="warning" :closable="false"/><el-tabs><el-tab-pane label="实训工具"><el-button-group><el-button :disabled="readonly" @click="frame?.startPointPick()">取点</el-button><el-button :disabled="readonly" @click="frame?.startArea()">重点区域</el-button><el-button :disabled="readonly" @click="frame?.startMeasurement()">两点测距</el-button><el-button @click="frame?.resetView()">复位</el-button></el-button-group><el-divider>点位标记</el-divider><el-input v-model="pointTitle" :disabled="readonly" placeholder="标记标题"/><el-input v-model="pointDescription" :disabled="readonly" type="textarea" placeholder="描述"/><p class="muted">坐标：{{point.x.toFixed(2)}}, {{point.y.toFixed(2)}}, {{point.z.toFixed(2)}}</p><el-button type="primary" :disabled="readonly" @click="addPoint">加入草稿</el-button><el-divider>两点测距</el-divider><p class="muted">距离：{{distance}} m</p><el-button type="primary" :disabled="readonly" @click="addMeasure">加入草稿</el-button></el-tab-pane><el-tab-pane label="笔录"><el-form label-position="top"><el-form-item label="现场概况"><el-input v-model="workspace.draft.overview" :disabled="readonly" type="textarea" :rows="3" @input="schedule"/></el-form-item><el-form-item label="勘验过程"><el-input v-model="workspace.draft.process" :disabled="readonly" type="textarea" :rows="3" @input="schedule"/></el-form-item><el-form-item label="物证描述"><el-input v-model="workspace.draft.evidenceDescription" :disabled="readonly" type="textarea" :rows="3" @input="schedule"/></el-form-item><el-form-item label="初步结论"><el-input v-model="workspace.draft.preliminaryConclusion" :disabled="readonly" type="textarea" :rows="3" @input="schedule"/></el-form-item></el-form></el-tab-pane><el-tab-pane :label="`标记 ${workspace.annotations.length}`"><el-empty v-if="!workspace.annotations.length" description="暂无学生标记"/><div v-for="item in workspace.annotations" :key="item.id" class="item"><b>{{item.title}}</b><p>{{item.description||'无描述'}}</p><el-button link type="danger" :disabled="readonly" @click="removeAnnotation(item)">删除</el-button></div></el-tab-pane><el-tab-pane :label="`测距 ${workspace.measurements.length}`"><el-empty v-if="!workspace.measurements.length" description="暂无测距"/><div v-for="item in workspace.measurements" :key="item.id" class="item"><b>{{Math.hypot(item.startPoint.x-item.endPoint.x,item.startPoint.y-item.endPoint.y,item.startPoint.z-item.endPoint.z).toFixed(2)}} m</b><el-button link type="danger" :disabled="readonly" @click="removeMeasurement(item)">删除</el-button></div></el-tab-pane></el-tabs><div class="footer"><span>自动保存：{{saveState==='saved'?'已保存':saveState==='saving'?'保存中…':saveState==='unsaved'?'待保存':'保存失败'}}<br>最后保存：{{lastSaved||'-'}}</span><el-button v-if="!readonly" type="primary" @click="submit">提交实训</el-button><span v-else-if="workspace.submitted">提交于 {{displayTime(workspace.submittedAt!)}}，版本 {{workspace.submissionVersion}}</span><span v-else-if="task?.status==='NOT_STARTED'">任务尚未开始</span><span v-else>已截止，且不允许迟交</span></div></aside></section></main></template>
<style scoped>.workspace{height:100vh;min-width:1100px;background:#f4f7fb}header{height:76px;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;background:#fff;border-bottom:1px solid #dde4ee}header p{margin:0;color:#64748b;font-size:12px}h1{margin:5px 0;font-size:20px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 400px;height:calc(100vh - 76px)}.viewer{min-width:0}.layout aside{overflow:auto;padding:16px;background:#fff;border-left:1px solid #dde4ee}.layout aside :deep(.el-input){margin-bottom:8px}.layout aside :deep(.el-alert){margin-bottom:12px}.muted,.footer{font-size:12px;color:#64748b;line-height:1.6}.item{padding:10px 0;border-bottom:1px solid #edf1f6}.item p{margin:4px 0;color:#64748b;font-size:12px}.footer{display:flex;justify-content:space-between;align-items:center;gap:12px;padding-top:14px;border-top:1px solid #edf1f6}@media(max-width:1100px){.workspace{min-width:0}.layout{grid-template-columns:1fr}.viewer{height:55vh}.layout aside{border-left:0;border-top:1px solid #dde4ee}}</style>
````

## frontend/src/views/TeacherCoursesView.vue

````vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import * as api from '@/api/teacher'
import type { Course, Student, TeachingClass } from '@/types/teacher'

const route=useRoute()
const list = ref<Course[]>([]), selected = ref<Course>(), group = ref<TeachingClass>(), search = ref(''), found = ref<Student[]>([]), busy = ref(false)
async function run(action: () => Promise<void>) { busy.value = true; try { await action() } catch (e) { ElMessage.error(api.message(e)) } finally { busy.value = false } }
async function load() { list.value = await api.courses(); if (selected.value) selected.value = list.value.find(c => c.id === selected.value?.id) }
async function name(title: string, value = '') { const p = await ElMessageBox.prompt('名称', title, { inputValue: value, inputValidator: v => Boolean(v?.trim()) && v.trim().length <= 200 || '请输入 1–200 字名称' }); return p.value.trim() }
async function createCourse() { try { const value = await name('创建课程'); await run(async () => { await api.post('/courses', { name: value }); await load() }) } catch {} }
async function renameCourse(c: Course) { try { const value = await name('编辑课程', c.name); await run(async () => { await api.patch(`/courses/${c.id}`, { name: value }); await load() }) } catch {} }
async function createClass() { if (!selected.value) return; try { const value = await name('创建班级'); await run(async () => { await api.post(`/courses/${selected.value!.id}/classes`, { name: value }); await load() }) } catch {} }
async function renameClass() { if (!group.value) return; try { const value = await name('编辑班级', group.value.name); await run(async () => { await api.patch(`/classes/${group.value!.id}`, { name: value }); group.value = await api.teachingClass(group.value!.id); await load() }) } catch {} }
function select(c: Course) { selected.value = c; group.value = undefined; found.value = [] }
function openClass(id: string) { run(async () => { group.value = await api.teachingClass(id); found.value = [] }) }
function add(s: Student) { run(async () => { group.value = await api.post<TeachingClass>(`/classes/${group.value!.id}/members`, { studentId: s.id }) }) }
function remove(s: Student) { run(async () => { await api.removeMember(group.value!.id, s.id); group.value = await api.teachingClass(group.value!.id) }) }
onMounted(() => run(async()=>{await load();const c=list.value.find(c=>c.id===route.params.courseId);if(c)select(c)}))
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>课程与班级</h1><el-button @click="$router.push('/teacher/tasks')">教学任务</el-button><el-button @click="$router.push('/teacher')">首页</el-button></header><el-button type="primary" @click="createCourse">创建课程</el-button><el-table :data="list"><el-table-column prop="name" label="课程"/><el-table-column label="操作"><template #default="{row}"><el-button link @click="select(row)">管理班级</el-button><el-button link @click="renameCourse(row)">编辑</el-button></template></el-table-column></el-table><el-card v-if="selected"><h2>{{ selected.name }}</h2><el-button @click="createClass">创建班级</el-button><el-button v-for="c in selected.classes" :key="c.id" @click="openClass(c.id)">{{c.name}}</el-button><section v-if="group"><h3>{{group.name}} <el-button link @click="renameClass">编辑名称</el-button></h3><p>班级成员变动不会改变已发布任务的学生名单。</p><el-input v-model="search" placeholder="输入完整学生用户名" style="max-width:300px"/><el-button @click="run(async()=>{found=await api.findStudent(search)})">查找学生</el-button><div v-for="s in found" :key="s.id">{{s.displayName}}（{{s.username}}）<el-button link @click="add(s)">加入班级</el-button></div><el-table :data="group.members"><el-table-column prop="username" label="用户名"/><el-table-column prop="displayName" label="姓名"/><el-table-column label="操作"><template #default="{row}"><el-button link type="danger" @click="remove(row)">移除</el-button></template></el-table-column></el-table></section></el-card></main></template>
````

## frontend/src/views/TeacherSubmissionView.vue

````vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '@/api/teacher'
import type { GradeItem, Review } from '@/types/teacher'
const route=useRoute(), data=ref<Review>(), items=ref<GradeItem[]>([]), feedback=ref(''), busy=ref(false)
const frozen=computed(()=>data.value?.grade?.status==='PUBLISHED'), total=computed(()=>items.value.reduce((n,i)=>n+Number(i.score||0),0).toFixed(2))
const labels:Record<string,string>={overview:'现场概况',process:'勘验过程',evidenceDescription:'物证描述',preliminaryConclusion:'初步结论'}
async function load(){data.value=await api.review(String(route.params.submissionId));feedback.value=data.value.grade?.feedback||'';items.value=data.value.task.rubric.map(r=>data.value!.grade?.items.find(i=>i.rubricItemId===r.id)||{rubricItemId:r.id!,score:null,comment:''}).map(i=>({...i,score:i.score===null?null:Number(i.score)}))}
async function run(action:()=>Promise<void>){busy.value=true;try{await action()}catch(e){ElMessage.error(api.message(e))}finally{busy.value=false}}
async function save(){await api.saveGrade(String(route.params.submissionId),feedback.value,items.value);ElMessage.success('批改草稿已保存')}
async function publish(){try{await ElMessageBox.confirm('成绩发布后学生可见，且不能继续修改。确认发布？','发布成绩');await run(async()=>{await save();await api.post(`/submissions/${route.params.submissionId}/grade/publish`);await load()})}catch{}}
onMounted(()=>run(load))
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>作业批改</h1><el-button @click="$router.push(`/teacher/tasks/${data?.task.id}`)">返回任务</el-button></header><template v-if="data"><h2>{{data.task.title}} · {{data.student.displayName}}（{{data.student.username}}）</h2><el-card><h3>勘验笔录</h3><section v-for="(value,key) in data.submission.reportContent" :key="key"><b>{{labels[key]||key}}</b><pre>{{value}}</pre></section><h3>标记</h3><section v-for="m in data.submission.marks" :key="m.id"><b>{{m.title}}</b><p>{{m.description}}</p><pre>{{JSON.stringify(m.geometry,null,2)}}</pre></section><el-empty v-if="!data.submission.marks.length" description="无标记"/><h3>测距</h3><div v-for="m in data.submission.measurements" :key="m.id"><p>{{m.distance}} m</p><pre>{{m.startPoint}} → {{m.endPoint}}</pre></div></el-card><el-card><h3>评分与反馈 · {{frozen?'已发布':'草稿'}}</h3><el-form :disabled="frozen||busy" label-position="top"><div v-for="(r,index) in data.task.rubric" :key="r.id"><el-form-item :label="`${r.title}（满分 ${r.maxScore}）`"><p>{{r.description}}</p><el-input-number v-model="(items[index].score as number)" :min="0" :max="Number(r.maxScore)" :precision="2" placeholder="未评分"/><el-input v-model="items[index].comment" type="textarea" placeholder="单项反馈"/></el-form-item></div><el-form-item label="总评"><el-input v-model="feedback" type="textarea" :rows="4"/></el-form-item></el-form><p>总分：{{total}}</p><div v-if="!frozen" class="actions"><el-button :disabled="busy" @click="run(save)">保存批改草稿</el-button><el-button type="primary" :disabled="busy" @click="publish">发布成绩</el-button></div></el-card></template></main></template>
````

## frontend/src/views/TeacherTaskDetailView.vue

````vue
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as api from '@/api/teacher'
import type { Course, SubmissionRow, TaskForm, TeachingTask } from '@/types/teacher'
import { displayTime } from '@/utils/student'

const route=useRoute(), router=useRouter(), busy=ref(false), courses=ref<Course[]>([]), versions=ref<{id:string;teachingTitle:string;versionNumber:number}[]>([]), rows=ref<SubmissionRow[]>([]), state=ref('DRAFT')
const id=computed(()=>route.params.taskId ? String(route.params.taskId) : undefined), editable=computed(()=>state.value==='DRAFT')
const form=ref<TaskForm>({courseId:'',title:'',instructions:'',caseVersionId:'',classIds:[],startAt:null,dueAt:null,allowLate:false,rubric:[{title:'勘验质量',description:'',maxScore:100}]})
const classes=computed(()=>courses.value.find(c=>c.id===form.value.courseId)?.classes||[])
function courseChanged(){form.value.classIds=[]}
async function run(action:()=>Promise<void>){busy.value=true;try{await action()}catch(e){ElMessage.error(api.message(e))}finally{busy.value=false}}
async function load(){courses.value=await api.courses();versions.value=await api.get('/case-versions');rows.value=[];if(id.value){const t=await api.task(id.value);state.value=t.status;form.value={courseId:t.courseId,title:t.title,instructions:t.instructions,caseVersionId:t.caseVersionId,classIds:t.classIds,startAt:t.startAt,dueAt:t.dueAt,allowLate:t.allowLate,rubric:t.rubric.map(r=>({...r,maxScore:Number(r.maxScore)}))};if(t.status!=='DRAFT')rows.value=await api.submissions(id.value)}else{state.value='DRAFT'}}
async function save(){await run(async()=>{const t=await api.saveTask(id.value,form.value);ElMessage.success('任务草稿已保存');if(!id.value)await router.replace(`/teacher/tasks/${t.id}`);else await load()})}
async function transition(action:'publish'|'close'){try{await ElMessageBox.confirm(action==='publish'?'发布后将冻结案例版本、名单和评分标准，确认发布？':'关闭后学生不能继续实训和提交，确认关闭？','确认操作');await run(async()=>{await api.post<TeachingTask>(`/tasks/${id.value}/${action}`);await load()})}catch{}}
onMounted(()=>run(load));watch(id,()=>run(load))
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>{{id?'任务详情':'创建教学任务'}} · {{state==='DRAFT'?'草稿':state==='PUBLISHED'?'已发布':'已关闭'}}</h1><el-button @click="router.push('/teacher/tasks')">返回任务</el-button></header><el-alert title="当前使用已转换的 READY 案例版本；本模块不包含案例发布或脱敏复核。" type="info" :closable="false"/><el-form label-position="top" :disabled="!editable||busy"><el-form-item label="课程"><el-select v-model="form.courseId" @change="courseChanged"><el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id"/></el-select></el-form-item><el-form-item label="任务名称"><el-input v-model="form.title" maxlength="200"/></el-form-item><el-form-item label="目标班级"><el-select v-model="form.classIds" multiple><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id"/></el-select></el-form-item><el-form-item label="案例版本"><el-select v-model="form.caseVersionId"><el-option v-for="v in versions" :key="v.id" :label="`${v.teachingTitle} · v${v.versionNumber}`" :value="v.id"/></el-select></el-form-item><el-form-item label="任务说明"><el-input v-model="form.instructions" type="textarea" :rows="4"/></el-form-item><el-form-item label="开始时间（可空，立即开始）"><el-date-picker v-model="form.startAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ"/></el-form-item><el-form-item label="截止时间（可空）"><el-date-picker v-model="form.dueAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ"/></el-form-item><el-form-item label="允许迟交"><el-switch v-model="form.allowLate"/></el-form-item><h2>评分点</h2><div v-for="(r,index) in form.rubric" :key="index"><div class="rubric-row"><el-input v-model="r.title" placeholder="评分点名称" maxlength="200"/><el-input-number v-model="(r.maxScore as number)" :min="0.01" :max="99999" :precision="2"/><el-button :disabled="form.rubric.length<=1" @click="form.rubric.splice(index,1)">删除</el-button></div><el-input v-model="r.description" placeholder="评分要求" type="textarea"/></div><el-button @click="form.rubric.push({title:'',description:'',maxScore:10})">添加评分点</el-button></el-form><div class="actions"><el-button v-if="editable" type="primary" :disabled="busy" @click="save">保存草稿</el-button><el-button v-if="editable&&id" type="success" :disabled="busy" @click="transition('publish')">发布已保存的任务</el-button><el-button v-if="state==='PUBLISHED'" type="danger" :disabled="busy" @click="transition('close')">关闭任务</el-button></div><el-card v-if="state!=='DRAFT'"><h2>学生提交</h2><el-table :data="rows"><el-table-column prop="student.displayName" label="学生"/><el-table-column prop="student.username" label="用户名"/><el-table-column label="提交状态"><template #default="{row}">{{row.status==='SUBMITTED'?'已提交':row.status==='DRAFT'?'草稿':'未开始'}}</template></el-table-column><el-table-column label="提交时间"><template #default="{row}">{{displayTime(row.submittedAt)}}</template></el-table-column><el-table-column label="成绩"><template #default="{row}">{{row.gradeStatus==='PUBLISHED'?'已发布':row.gradeStatus==='DRAFT'?'批改草稿':'未批改'}} {{row.totalScore??''}}</template></el-table-column><el-table-column label="操作"><template #default="{row}"><el-button v-if="row.submissionId" link type="primary" @click="router.push(`/teacher/submissions/${row.submissionId}`)">批改 / 查看</el-button></template></el-table-column></el-table></el-card></main></template>
````

## frontend/src/views/TeacherTasksView.vue

````vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '@/api/teacher'
import type { Course, TeachingTask } from '@/types/teacher'
const list=ref<TeachingTask[]>([]), courses=ref<Course[]>([]), courseId=ref(''), status=ref(''), busy=ref(false)
const labels:Record<string,string>={DRAFT:'草稿',PUBLISHED:'已发布',CLOSED:'已关闭'}
async function load(){busy.value=true;try{list.value=await api.tasks(courseId.value,status.value)}catch(e){ElMessage.error(api.message(e))}finally{busy.value=false}}
onMounted(async()=>{try{courses.value=await api.courses();await load()}catch(e){ElMessage.error(api.message(e))}})
</script>
<template><main class="teacher-page"><header><h1>教学任务</h1><el-button @click="$router.push('/teacher/courses')">课程管理</el-button><el-button type="primary" @click="$router.push('/teacher/tasks/new')">创建任务</el-button></header><div class="actions"><el-select v-model="courseId" clearable placeholder="全部课程" style="width:240px" @change="load"><el-option v-for="c in courses" :key="c.id" :value="c.id" :label="c.name"/></el-select><el-select v-model="status" clearable placeholder="全部状态" style="width:160px" @change="load"><el-option v-for="(label,value) in labels" :key="value" :value="value" :label="label"/></el-select><el-button @click="load">刷新</el-button></div><el-table :data="list" v-loading="busy"><el-table-column prop="title" label="任务"/><el-table-column label="状态"><template #default="{row}">{{labels[row.status]}}</template></el-table-column><el-table-column label="提交进度"><template #default="{row}">{{row.submittedCount}} / {{row.assignedCount}}</template></el-table-column><el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="$router.push(`/teacher/tasks/${row.id}`)">详情 / 批改</el-button></template></el-table-column></el-table><el-empty v-if="!busy&&!list.length" description="暂无教学任务"/></main></template>
````
