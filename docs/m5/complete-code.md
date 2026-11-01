# M5 完整代码

收录本模块改动实现文件及数据库 SQL 的完整内容。测试步骤、接口与限制见 README.md。

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

## M5 案例发布与审计

新增独立教学副本、人工发布、授权登记与撤销、有效期拦截、版本谱系和审计查询。M3/M4 现在仅使用有效的 PUBLISHED 版本。升级说明、SQL 和验收步骤见 [M5 交付说明](docs/m5/README.md)。
````

## backend/alembic/versions/20261101_0007_publication_audit.py

````python
"""M5 publication and authorization."""
from alembic import op
import sqlalchemy as sa
revision='202611010007'
down_revision='202610310006'
branch_labels=None
depends_on=None


def upgrade():
    with op.batch_alter_table('case_versions') as b:
        b.add_column(sa.Column('parent_version_id',sa.String(36)))
        b.create_foreign_key('fk_version_parent','case_versions',['parent_version_id'],['id'])
    op.create_table('case_authorizations',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('case_id',sa.String(36),sa.ForeignKey('cases.id'),nullable=False),
        sa.Column('reference',sa.String(200),nullable=False),sa.Column('scope',sa.Text(),nullable=False),
        sa.Column('valid_until',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked_at',sa.DateTime(timezone=True)),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_case_authorizations_case_id','case_authorizations',['case_id'])
    op.create_table('teaching_copies',
        sa.Column('id',sa.String(36),primary_key=True),sa.Column('version_id',sa.String(36),sa.ForeignKey('case_versions.id'),unique=True,nullable=False),
        sa.Column('authorization_id',sa.String(36),sa.ForeignKey('case_authorizations.id'),nullable=False),
        sa.Column('manifest_key',sa.String(512),nullable=False),sa.Column('checksum',sa.String(64),nullable=False),
        sa.Column('review_note',sa.Text(),nullable=False),sa.Column('valid_until',sa.DateTime(timezone=True),nullable=False),
        sa.Column('published_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('published_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))


def downgrade():
    op.execute("UPDATE case_versions SET status='READY' WHERE status='PUBLISHED'")
    op.drop_table('teaching_copies');op.drop_table('case_authorizations')
    with op.batch_alter_table('case_versions') as b:
        b.drop_constraint('fk_version_parent',type_='foreignkey');b.drop_column('parent_version_id')
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

from app.api.routes import publication
api_router.include_router(publication.router)
````

## backend/app/api/routes/cases.py

````python
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
    if payload.parent_version_id:
        parent = db.get(CaseVersion, payload.parent_version_id)
        if not parent or parent.case_id != case_id:
            raise HTTPException(422, "Parent version must belong to same case")
    version_number = (db.scalar(select(func.max(CaseVersion.version_number)).where(CaseVersion.case_id == case_id)) or 0) + 1
    version = CaseVersion(parent_version_id=payload.parent_version_id, case_id=case_id, source_file_id=source.id, version_number=version_number, status="PROCESSING")
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
````

## backend/app/api/routes/publication.py

````python
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
from app.services.publication import require_teaching_version
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
    require_teaching_version(db,v)
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
    require_teaching_version(db,db.get(CaseVersion,t.case_version_id))
    s=save(db,t,user,payload);db.add(AuditLog(action="DRAFT_SAVED",actor_id=user.id,case_version_id=t.case_version_id,detail={"taskId":t.id,"submissionId":s.id}));db.commit();return APIResponse(data=subdata(db,s),request_id=request_id)
@router.post("/tasks/{task_id}/submissions")
def submit(task_id:str,payload:DraftPayload,user:User=Depends(require_student),db:Session=Depends(get_db),request_id:str=Depends(get_request_id)):
    t=assigned(db,task_id,user); now=datetime.now(UTC)
    if t.status!="PUBLISHED" or (t.start_at and now<utc(t.start_at)) or (t.due_at and now>utc(t.due_at) and not t.allow_late): raise HTTPException(409,"Task submission is closed")
    require_teaching_version(db,db.get(CaseVersion,t.case_version_id))
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

from app.services.publication import require_teaching_version
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
    task_id=detail.get("taskId")
    submission=db.get(Submission,detail["submissionId"]) if detail.get("submissionId") else None
    task=db.get(Task,task_id or submission.task_id) if task_id or submission else None
    version=db.get(CaseVersion,task.case_version_id) if task else None
    db.add(AuditLog(action=action, actor_id=teacher.id, case_id=version.case_id if version else None, case_version_id=version.id if version else None, detail=detail))


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
    rows = db.execute(select(CaseVersion, Case.teaching_title).join(Case).where(CaseVersion.status == "PUBLISHED", CaseVersion.viewer_manifest_key.is_not(None))).all()
    available=[]
    for v, title in rows:
        try: require_teaching_version(db,v)
        except HTTPException: continue
        available.append({"id":v.id,"teachingTitle":title,"versionNumber":v.version_number})
    return result(available,rid)


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
    require_teaching_version(db, version)
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
    require_teaching_version(db, version)
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
    if item.status not in {"READY", "PUBLISHED"} or not item.viewer_manifest_key: raise HTTPException(409, "Viewer is unavailable until conversion is READY")
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
    if claims.get("type") == "student_viewer":
        from app.services.publication import require_teaching_version
        copy = require_teaching_version(db,version)
        storage = Path(settings.storage_root).resolve()
        root = (storage / copy.manifest_key).resolve().parent
        if storage not in root.parents: raise HTTPException(404,"Asset not found")
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

from app.models.publication import CaseAuthorization, TeachingCopy
````

## backend/app/models/case.py

````python
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
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("case_versions.id"), nullable=True)
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


class Annotation(Base):
    __tablename__ = "annotations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_version_id: Mapped[str] = mapped_column(ForeignKey("case_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(40), nullable=False, default="ADMIN_WORKSPACE")
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON(), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    viewer_state: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Measurement(Base):
    __tablename__ = "measurements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_version_id: Mapped[str] = mapped_column(ForeignKey("case_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_point: Mapped[dict] = mapped_column(JSON(), nullable=False)
    end_point: Mapped[dict] = mapped_column(JSON(), nullable=False)
    distance: Mapped[float] = mapped_column(nullable=False)
    viewer_state: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
````

## backend/app/models/publication.py

````python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.practice import uid


class CaseAuthorization(Base):
    __tablename__ = 'case_authorizations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'), index=True)
    reference: Mapped[str] = mapped_column(String(200))
    scope: Mapped[str] = mapped_column(Text)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeachingCopy(Base):
    __tablename__ = 'teaching_copies'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey('case_versions.id'), unique=True)
    authorization_id: Mapped[str] = mapped_column(ForeignKey('case_authorizations.id'))
    manifest_key: Mapped[str] = mapped_column(String(512))
    checksum: Mapped[str] = mapped_column(String(64))
    review_note: Mapped[str] = mapped_column(Text)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
````

## backend/app/schemas/case.py

````python
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def _utc_timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ApiModel(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda value: _utc_timestamp(value).isoformat().replace("+00:00", "Z")})


class CaseCreate(ApiModel):
    internal_code: str = Field(alias="internalCode", min_length=1, max_length=64)
    teaching_title: str = Field(alias="teachingTitle", min_length=1, max_length=200)
    case_type: str = Field(alias="caseType", min_length=1, max_length=64)
    difficulty: str
    course_tags: list[str] = Field(alias="courseTags", default_factory=list)
    valid_until: datetime | None = Field(alias="validUntil", default=None)
    desensitization_level: str = Field(alias="desensitizationLevel")
    description: str | None = None


class FileData(ApiModel):
    id: str
    file_name: str = Field(serialization_alias="fileName")
    file_size: int = Field(serialization_alias="fileSize")


class VersionCreate(ApiModel):
    parent_version_id: str | None = Field(alias="parentVersionId", default=None)
    file_id: str = Field(alias="fileId", serialization_alias="fileId")


class VersionData(ApiModel):
    id: str
    status: str
    job_id: str | None = Field(serialization_alias="jobId")
    progress: int
    point_count: int | None = Field(serialization_alias="pointCount")
    bounds: dict | None
    failure_reason: str | None = Field(serialization_alias="failureReason")
    created_at: datetime = Field(serialization_alias="createdAt")


class CaseData(ApiModel):
    id: str
    internal_code: str = Field(serialization_alias="internalCode")
    teaching_title: str = Field(serialization_alias="teachingTitle")
    case_type: str = Field(serialization_alias="caseType")
    difficulty: str
    course_tags: list[str] = Field(serialization_alias="courseTags")
    valid_until: datetime | None = Field(serialization_alias="validUntil")
    desensitization_level: str = Field(serialization_alias="desensitizationLevel")
    file: FileData | None
    latest_version: VersionData | None = Field(serialization_alias="latestVersion")
    created_at: datetime = Field(serialization_alias="createdAt")


class JobData(ApiModel):
    id: str
    type: str
    status: str
    progress: int
    version_id: str = Field(serialization_alias="versionId")
    failure_reason: str | None = Field(serialization_alias="failureReason")
    created_at: datetime = Field(serialization_alias="createdAt")
    started_at: datetime | None = Field(serialization_alias="startedAt")
    finished_at: datetime | None = Field(serialization_alias="finishedAt")


class CaseListData(ApiModel):
    items: list[CaseData]
    total: int
````

## backend/app/services/conversion.py

````python
"""M1 point-cloud conversion worker executed by RQ."""
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.case import AuditLog, CaseVersion, Job


def _tool_error(tool_name: str, configured_path: str) -> str | None:
    if Path(configured_path).is_file() or shutil.which(configured_path):
        return None
    return f"{tool_name} is unavailable: configured path '{configured_path}' was not found"


def _read_pdal_metadata(raw_path: Path) -> tuple[int, dict]:
    settings = get_settings()
    unavailable = _tool_error("PDAL", settings.pdal_path)
    if unavailable:
        raise RuntimeError(unavailable)
    result = subprocess.run([settings.pdal_path, "info", "--metadata", str(raw_path)], capture_output=True, text=True, timeout=settings.conversion_timeout_seconds, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"PDAL metadata failed: {result.stderr.strip() or result.stdout.strip()}")
    payload = json.loads(result.stdout)
    metadata = payload.get("metadata", {})
    reader = next((value for key, value in metadata.items() if key.startswith("readers.")), metadata)
    count = reader.get("count") or reader.get("num_points")
    bounds = reader.get("bbox", {}).get("native") or reader.get("bounds")
    if not isinstance(count, int) or not isinstance(bounds, dict):
        raise RuntimeError("PDAL metadata did not contain point count and bounds")
    try:
        normalized_bounds = {"min": [bounds[axis]["min"] for axis in ("x", "y", "z")], "max": [bounds[axis]["max"] for axis in ("x", "y", "z")]}
    except (KeyError, TypeError) as exc:
        raise RuntimeError("PDAL metadata bounds format is unsupported") from exc
    return count, normalized_bounds


def run_conversion(job_id: str) -> None:
    """Update durable job/version state. Any tool error becomes FAILED, never READY."""
    settings = get_settings()
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if job is None:
            return
        version = job.case_version
        from app.models.practice import Task
        if version.status == "PUBLISHED" or db.scalar(select(Task.id).where(Task.case_version_id==version.id)):
            return
        if job.status != "PENDING" or version.status != "PROCESSING":
            return
        job.status, job.progress, job.started_at = "RUNNING", 5, datetime.now(UTC)
        version.status, version.error_message = "PROCESSING", None

    try:
        with SessionLocal.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id))
            version = job.case_version
            raw_path = Path(settings.storage_root).resolve() / version.source_file.storage_key
            if not raw_path.is_file():
                raise RuntimeError("Raw point-cloud file is missing from controlled storage")
            point_count, bounds = _read_pdal_metadata(raw_path)
            job.progress = 45
            version.point_count, version.bounds = point_count, bounds
            unavailable = _tool_error("PotreeConverter", settings.potree_converter_path)
            if unavailable:
                raise RuntimeError(unavailable)
            output_dir = Path(settings.storage_root).resolve() / "cases" / version.case_id / "versions" / version.id / "potree"
            output_dir.mkdir(parents=True, exist_ok=True)
            result = subprocess.run([settings.potree_converter_path, str(raw_path), "-o", str(output_dir)], capture_output=True, text=True, timeout=settings.conversion_timeout_seconds, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"PotreeConverter failed: {result.stderr.strip() or result.stdout.strip()}")
            manifest = output_dir / "metadata.json"
            if not manifest.is_file():
                raise RuntimeError("PotreeConverter completed but metadata.json was not produced")
            version.viewer_manifest_key = str(manifest.relative_to(Path(settings.storage_root).resolve())).replace("\\", "/")
            version.status, job.status, job.progress, job.finished_at = "READY", "SUCCEEDED", 100, datetime.now(UTC)
            db.add(AuditLog(action="CONVERSION_SUCCEEDED", case_id=version.case_id, case_version_id=version.id, job_id=job.id))
    except Exception as exc:  # Persist tool/process failures for administrator diagnosis.
        message = str(exc)[:4000]
        with SessionLocal.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id))
            if job is not None:
                version = job.case_version
                version.status, version.error_message = "FAILED", message
                job.status, job.error_message, job.finished_at = "FAILED", message, datetime.now(UTC)
                db.add(AuditLog(action="CONVERSION_FAILED", case_id=version.case_id, case_version_id=version.id, job_id=job.id, detail={"error": message}))
````

## backend/app/services/publication.py

````python
from datetime import UTC, datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models.case import Case
from app.models.publication import CaseAuthorization, TeachingCopy
from app.services.practice_access import utc


def require_teaching_version(db, version):
    if not version or version.status != 'PUBLISHED':
        raise HTTPException(409, 'Published teaching version required')
    copy = db.scalar(select(TeachingCopy).where(TeachingCopy.version_id == version.id))
    authorization = db.get(CaseAuthorization, copy.authorization_id) if copy else None
    case = db.get(Case, version.case_id)
    now = datetime.now(UTC)
    if not copy or not authorization or authorization.revoked_at or utc(copy.valid_until) <= now or utc(authorization.valid_until) <= now or (case.valid_until and utc(case.valid_until) <= now):
        raise HTTPException(409, 'Teaching publication or authorization is expired/revoked')
    return copy
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
            version = CaseVersion(case_id=case.id, source_file_id=file.id, version_number=1, status='PUBLISHED', viewer_manifest_key='test/metadata.json')
            db.add(version); db.flush(); self.version = version.id
            from app.models.publication import CaseAuthorization, TeachingCopy
            auth=CaseAuthorization(case_id=case.id,reference='test',scope='teaching',valid_until=datetime.now(UTC)+timedelta(days=30),created_by=admin.id)
            db.add(auth);db.flush()
            db.add(TeachingCopy(version_id=version.id,authorization_id=auth.id,manifest_key='teaching/test/metadata.json',checksum='0'*64,review_note='fixture',valid_until=datetime.now(UTC)+timedelta(days=30),published_by=admin.id))


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

## backend/tests/test_m5.py

````python
import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlalchemy import delete, select
import test_m4
from app.core.config import get_settings
from app.models.case import CaseVersion
from app.models.publication import TeachingCopy


class PublicationWorkflow(unittest.TestCase):
    call = test_m4.TeachingWorkflow.call
    setup_task = test_m4.TeachingWorkflow.setup_task

    def setUp(self):
        test_m4.TeachingWorkflow.setUp(self)
        self.old_storage=get_settings().storage_root
        get_settings().storage_root=str(Path(self.tmp.name)/'storage')
        with self.sessions.begin() as db:
            v=db.get(CaseVersion,self.version);self.case_id=v.case_id
            db.execute(delete(TeachingCopy));v.status='READY'
        self.source=Path(get_settings().storage_root)/'cases'/self.case_id/'versions'/self.version/'potree'
        self.source.mkdir(parents=True)
        (self.source/'metadata.json').write_text(json.dumps({'name':'synthetic-test'}))
        (self.source/'octree.bin').write_bytes(b'synthetic-points')
        expiry=(datetime.now(UTC)+timedelta(days=5)).isoformat()
        a=self.call('POST',f'/cases/{self.case_id}/authorizations',{'reference':'TEST-ONLY','scope':'synthetic teaching','validUntil':expiry},user='admin',code=201)
        self.authorization_id=a['id']
        self.publication={'authorizationId':a['id'],'validUntil':expiry,'reviewConfirmed':True,'reviewNote':'synthetic reviewed data'}

    def tearDown(self):
        get_settings().storage_root=self.old_storage
        test_m4.TeachingWorkflow.tearDown(self)

    def test_copy_is_independent_and_revocation_blocks_access(self):
        path=f'/case-versions/{self.version}/publish'
        self.call('POST',path,self.publication,user='teacher',code=403)
        self.call('POST',path,{**self.publication,'reviewConfirmed':False},user='admin',code=422)
        self.call('POST',path,self.publication,user='admin')
        self.call('POST',path,self.publication,user='admin',code=409)
        with self.sessions() as db:
            copy=db.scalar(select(TeachingCopy));manifest=Path(get_settings().storage_root)/copy.manifest_key
        self.assertNotEqual(manifest.parent,self.source)
        (self.source/'metadata.json').write_text('changed source')
        self.assertEqual(json.loads(manifest.read_text())['name'],'synthetic-test')
        task=self.setup_task();tid=task['id']
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student')
        asset=f'/viewer-assets/{self.version}/metadata.json'
        response=self.client.get('/api/v1'+asset)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['name'],'synthetic-test')
        self.call('POST',f'/authorizations/{self.authorization_id}/revoke',user='admin')
        self.assertEqual(self.call('GET','/teacher/case-versions'),[])
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student',code=409)
        self.call('GET',asset,user='student',code=409)
        self.call('PUT',f'/student/tasks/{tid}/draft',{},user='student',code=409)
        self.call('POST','/teacher/tasks',self.payload,code=409)
        logs=self.call('GET',f'/audit-logs?caseId={self.case_id}&action=VERSION_PUBLISHED',user='admin')
        self.assertEqual(logs['total'],1)
        self.call('GET','/audit-logs',user='student',code=403)

    def test_expiry_blocks_new_tasks_and_submission(self):
        self.call('POST',f'/case-versions/{self.version}/publish',self.publication,user='admin')
        task=self.setup_task();self.call('POST',f'/teacher/tasks/{task["id"]}/publish')
        with self.sessions.begin() as db:db.scalar(select(TeachingCopy)).valid_until=datetime.now(UTC)-timedelta(seconds=1)
        self.call('POST','/teacher/tasks',self.payload,code=409)
        self.call('POST',f'/student/tasks/{task["id"]}/submissions',{},user='student',code=409)
        self.assertEqual(self.call('GET','/teacher/case-versions'),[])

    def test_invalid_publication_and_lineage(self):
        self.call('POST',f'/case-versions/{self.version}/publish',{**self.publication,'validUntil':(datetime.now(UTC)+timedelta(days=10)).isoformat()},user='admin',code=422)
        (self.source/'raw.las').write_bytes(b'not allowed')
        self.call('POST',f'/case-versions/{self.version}/publish',self.publication,user='admin',code=409)
        self.assertEqual(list((Path(get_settings().storage_root)/'teaching').glob('*')),[])
        versions=self.call('GET',f'/cases/{self.case_id}/versions',user='admin')
        self.assertEqual(versions[0]['parentVersionId'],None)
        self.call('GET',f'/cases/{self.case_id}/authorizations',user='teacher',code=403)

    def test_published_version_cannot_be_reconverted(self):
        from unittest.mock import patch
        from app.models.case import Job
        from app.services.conversion import run_conversion
        self.call('POST',f'/case-versions/{self.version}/publish',self.publication,user='admin')
        with self.sessions.begin() as db:
            job=Job(case_version_id=self.version,status='PENDING',progress=0)
            db.add(job);db.flush();jid=job.id
        with patch('app.services.conversion.SessionLocal',self.sessions):run_conversion(jid)
        with self.sessions() as db:
            self.assertEqual(db.get(CaseVersion,self.version).status,'PUBLISHED')
            self.assertEqual(db.get(Job,jid).status,'PENDING')
````

## docs/m5/migration.postgresql.sql

````sql
BEGIN;

-- Running upgrade 202610310006 -> 202611010007

ALTER TABLE case_versions ADD COLUMN parent_version_id VARCHAR(36);

ALTER TABLE case_versions ADD CONSTRAINT fk_version_parent FOREIGN KEY(parent_version_id) REFERENCES case_versions (id);

CREATE TABLE case_authorizations (
    id VARCHAR(36) NOT NULL,
    case_id VARCHAR(36) NOT NULL,
    reference VARCHAR(200) NOT NULL,
    scope TEXT NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(case_id) REFERENCES cases (id),
    FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX ix_case_authorizations_case_id ON case_authorizations (case_id);

CREATE TABLE teaching_copies (
    id VARCHAR(36) NOT NULL,
    version_id VARCHAR(36) NOT NULL,
    authorization_id VARCHAR(36) NOT NULL,
    manifest_key VARCHAR(512) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    review_note TEXT NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    published_by INTEGER NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (version_id),
    FOREIGN KEY(version_id) REFERENCES case_versions (id),
    FOREIGN KEY(authorization_id) REFERENCES case_authorizations (id),
    FOREIGN KEY(published_by) REFERENCES users (id)
);

UPDATE alembic_version SET version_num='202611010007' WHERE alembic_version.version_num = '202610310006';

COMMIT;
````

## frontend/src/router/index.ts

````typescript
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types/auth'
import { homeRouteForRoles } from '@/utils/auth'

const routes: RouteRecordRaw[] = [
  { path: '/admin/cases/:caseId/publication', component: () => import('@/views/CasePublicationView.vue'), meta: { requiresAuth: true, roles: ['ADMIN'] } },
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

## frontend/src/types/case.ts

````typescript
export type CaseVersionStatus = 'DRAFT' | 'PROCESSING' | 'READY' | 'PUBLISHED' | 'FAILED'

export interface CaseFile {
  id: string
  fileName: string
  fileSize: number
}

export interface Bounds {
  min: [number, number, number]
  max: [number, number, number]
}

export interface CaseVersion {
  id: string
  status: CaseVersionStatus
  jobId: string | null
  progress: number | null
  pointCount: number | null
  bounds: Bounds | null
  failureReason: string | null
  createdAt: string
}

export interface CaseRecord {
  id: string
  internalCode: string
  teachingTitle: string
  caseType: string
  difficulty: string
  courseTags: string[]
  validUntil: string | null
  desensitizationLevel: string
  file: CaseFile | null
  latestVersion: CaseVersion | null
  createdAt: string
}

export interface CreateCasePayload {
  internalCode: string
  teachingTitle: string
  caseType: string
  difficulty: string
  courseTags: string[]
  validUntil?: string | null
  desensitizationLevel: string
}

export interface CaseListResult {
  items: CaseRecord[]
  total: number
}
````

## frontend/src/utils/case.ts

````typescript
import type { Bounds, CaseVersionStatus } from '@/types/case'

const statusMap: Record<CaseVersionStatus, { text: string; type: 'info' | 'warning' | 'success' | 'danger' }> = {
  DRAFT: { text: '草稿', type: 'info' },
  PROCESSING: { text: '处理中', type: 'warning' },
  PUBLISHED: { text: '已发布', type: 'success' },
  READY: { text: '已就绪', type: 'success' },
  FAILED: { text: '失败', type: 'danger' },
}

export function statusMeta(status?: CaseVersionStatus) {
  return statusMap[status || 'DRAFT']
}

export function formatBytes(size?: number) {
  if (!size) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let index = 0
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1 }
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`
}

export function formatDate(value?: string) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-'
}

export function formatBounds(bounds: Bounds | null | undefined) {
  if (!bounds) return '-'
  const [minX, minY, minZ] = bounds.min
  const [maxX, maxY, maxZ] = bounds.max
  return `X: ${minX.toFixed(2)}–${maxX.toFixed(2)}；Y: ${minY.toFixed(2)}–${maxY.toFixed(2)}；Z: ${minZ.toFixed(2)}–${maxZ.toFixed(2)}`
}
````

## frontend/src/views/CaseDetailView.vue

````vue
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { getCase, getCaseVersion, getJob } from '@/api/cases'
import type { CaseRecord } from '@/types/case'
import { formatBounds, formatBytes, formatDate, statusMeta } from '@/utils/case'

const route = useRoute(); const router = useRouter()
const record = ref<CaseRecord>(); const loading = ref(false); const timer = ref<number>()
const version = computed(() => record.value?.latestVersion)

async function loadDetail(silent = false) {
  if (!silent) loading.value = true
  try {
    const current = await getCase(String(route.params.caseId))
    if (current.latestVersion?.jobId && current.latestVersion.status === 'PROCESSING') await getJob(current.latestVersion.jobId)
    if (current.latestVersion) current.latestVersion = await getCaseVersion(current.latestVersion.id)
    record.value = current
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '案例详情加载失败') }
  finally { loading.value = false }
}

function refresh() { loadDetail().then(() => ElMessage.success('状态已更新')) }
onMounted(async () => { await loadDetail(); timer.value = window.setInterval(() => { if (version.value?.status === 'PROCESSING') loadDetail(true) }, 5000) })
onBeforeUnmount(() => { if (timer.value) window.clearInterval(timer.value) })
</script>

<template>
  <main class="page-shell">
    <div class="page-header"><div><p class="eyebrow">管理员 / 案例管理</p><h1>{{ record?.teachingTitle || '案例详情' }}</h1><p class="page-description">案例与转换版本信息</p></div><div class="header-actions"><el-button @click="router.push(`/admin/cases/${route.params.caseId}/publication`)">发布与审计</el-button><el-button @click="router.push('/admin/cases')">返回列表</el-button><el-button type="primary" :loading="loading" @click="refresh">重新查询状态</el-button></div></div>
    <el-skeleton v-if="loading && !record" :rows="8" animated />
    <template v-else-if="record">
      <el-card shadow="never" class="card"><template #header><div class="card-title">基本信息 <el-tag :type="statusMeta(version?.status).type">{{ statusMeta(version?.status).text }}</el-tag></div></template><el-descriptions :column="2" border><el-descriptions-item label="内部案例编号">{{ record.internalCode }}</el-descriptions-item><el-descriptions-item label="案例类型">{{ record.caseType }}</el-descriptions-item><el-descriptions-item label="教学难度">{{ record.difficulty }}</el-descriptions-item><el-descriptions-item label="课程标签"><el-tag v-for="tag in record.courseTags" :key="tag" class="tag">{{ tag }}</el-tag></el-descriptions-item><el-descriptions-item label="有效期">{{ record.validUntil || '长期有效' }}</el-descriptions-item><el-descriptions-item label="脱敏等级">{{ record.desensitizationLevel }}</el-descriptions-item><el-descriptions-item label="文件信息" :span="2">{{ record.file?.fileName || '尚未上传' }} <span class="muted">{{ formatBytes(record.file?.fileSize) }}</span></el-descriptions-item><el-descriptions-item label="创建时间" :span="2">{{ formatDate(record.createdAt) }}</el-descriptions-item></el-descriptions></el-card>
      <el-card shadow="never" class="card"><template #header><div class="card-title">转换版本</div></template><el-empty v-if="!version" description="尚未创建转换版本" /><template v-else><el-progress v-if="version.status === 'PROCESSING'" :percentage="version.progress || 0" status="warning" /><el-descriptions :column="2" border class="version-data"><el-descriptions-item label="版本状态"><el-tag :type="statusMeta(version.status).type">{{ statusMeta(version.status).text }}</el-tag></el-descriptions-item><el-descriptions-item label="版本创建时间">{{ formatDate(version.createdAt) }}</el-descriptions-item><el-descriptions-item label="点数">{{ version.pointCount?.toLocaleString() || '-' }}</el-descriptions-item><el-descriptions-item label="边界范围">{{ formatBounds(version.bounds) }}</el-descriptions-item><el-descriptions-item v-if="version.failureReason" label="失败错误信息" :span="2"><span class="failure">{{ version.failureReason }}</span></el-descriptions-item></el-descriptions></template></el-card>
      <el-alert v-if="version?.status === 'PROCESSING'" title="点云转换处理中" description="转换完成后可进入三维工作台。" type="warning" :closable="false" show-icon />
      <el-alert v-else-if="version?.status === 'FAILED'" title="点云转换失败" :description="version.failureReason || '请检查转换任务后重试。'" type="error" :closable="false" show-icon />
      <el-button v-else-if="['READY','PUBLISHED'].includes(version?.status||'')" type="primary" @click="router.push(`/admin/cases/${record.id}/viewer`)">进入三维工作台</el-button>
    </template>
  </main>
</template>

<style scoped>
.page-shell { max-width: 1180px; min-height: 100vh; margin: 0 auto; padding: 36px 32px; }.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 24px; }.header-actions { display: flex; gap: 12px; }.eyebrow { margin: 0 0 8px; color: #6b7b91; font-size: 13px; }h1 { margin: 0; color: #142d4d; font-size: 27px; }.page-description { margin: 10px 0 0; color: #718096; }.card { margin-bottom: 20px; }.card-title { display: flex; align-items: center; justify-content: space-between; }.tag { margin-right: 6px; }.muted { margin-left: 8px; color: #8491a3; }.version-data { margin-top: 18px; }.failure { color: #c45656; }@media (max-width: 720px) { .page-shell { padding: 24px 16px; }.page-header { flex-direction: column; }.header-actions { width: 100%; }.header-actions .el-button { flex: 1; } }
</style>
````

## frontend/src/views/CasePublicationView.vue

````vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { responseData } from '@/api/http'
import { message } from '@/api/teacher'
const route=useRoute(), cid=String(route.params.caseId), mock=import.meta.env.VITE_USE_MOCK!=='false'
interface Authorization {id:string;reference:string;scope:string;validUntil:string;revokedAt:string|null}
interface Version {id:string;versionNumber:number;parentVersionId:string|null;status:string;publication:{validUntil:string;checksum:string;reviewNote:string}|null}
interface Log {id:string;action:string;actorId:number;createdAt:string;detail:unknown}
const auths=ref<Authorization[]>([]), versions=ref<Version[]>([]), logs=ref<Log[]>([]), total=ref(0), page=ref(1), action=ref(''),busy=ref(false)
const authorization=ref({reference:'',scope:'仅限授权教学使用',validUntil:''}), publication=ref({authorizationId:'',validUntil:'',reviewNote:'',reviewConfirmed:false}), selected=ref('')
async function get<T>(path:string){return responseData<T>(await http.get('/api/v1'+path))}
async function timeline(){const data=await get<{items:Log[];total:number}>(`/audit-logs?caseId=${cid}&action=${encodeURIComponent(action.value)}&offset=${(page.value-1)*20}&limit=20`);logs.value=data.items;total.value=data.total}
async function load(){if(mock)return;auths.value=await get(`/cases/${cid}/authorizations`);versions.value=await get(`/cases/${cid}/versions`);await timeline()}
async function run(fn:()=>Promise<void>){busy.value=true;try{await fn()}catch(e){ElMessage.error(message(e))}finally{busy.value=false}}
async function add(){await run(async()=>{await http.post(`/api/v1/cases/${cid}/authorizations`,authorization.value);await load();ElMessage.success('授权记录已添加')})}
async function revoke(id:string){try{await ElMessageBox.confirm('撤销后，关联案例将无法用于新任务和学生访问。确认撤销？','撤销授权');await run(async()=>{await http.post(`/api/v1/authorizations/${id}/revoke`);await load()})}catch{}}
async function publish(){try{await ElMessageBox.confirm('确认已人工复核，并生成独立教学副本？发布后不能覆盖此版本。','发布教学版本');await run(async()=>{await http.post(`/api/v1/case-versions/${selected.value}/publish`,publication.value,{timeout:600000});await load();ElMessage.success('教学版本已发布')})}catch{}}
onMounted(()=>run(load))
</script>
<template><main class="teacher-page" v-loading="busy"><header><h1>案例发布、授权与审计</h1><el-button @click="$router.push(`/admin/cases/${cid}`)">案例详情</el-button></header><el-alert v-if="mock" title="此管理页需要真实后端，请设置 VITE_USE_MOCK=false 并以管理员登录。" type="warning" :closable="false"/><el-alert title="人工复核确认是发布前提；此模块不执行自动脱敏。有效期及授权撤销会即时阻止学生访问。" type="info" :closable="false"/><el-card><h2>授权记录</h2><el-form :disabled="mock||busy" label-position="top"><el-form-item label="授权材料编号（材料原件不上传公开仓库）"><el-input v-model="authorization.reference"/></el-form-item><el-form-item label="授权范围"><el-input v-model="authorization.scope" type="textarea"/></el-form-item><el-form-item label="授权有效期"><el-date-picker v-model="authorization.validUntil" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ"/></el-form-item><el-button @click="add">添加授权</el-button></el-form><el-table :data="auths"><el-table-column prop="reference" label="材料编号"/><el-table-column prop="scope" label="范围"/><el-table-column prop="validUntil" label="有效期"/><el-table-column label="操作"><template #default="{row}"><span v-if="row.revokedAt">已撤销</span><el-button v-else link type="danger" @click="revoke(row.id)">撤销</el-button></template></el-table-column></el-table></el-card><el-card><h2>版本谱系与教学发布</h2><el-table :data="versions"><el-table-column prop="versionNumber" label="版本号"/><el-table-column prop="id" label="版本 ID"/><el-table-column prop="parentVersionId" label="父版本 ID"/><el-table-column prop="status" label="状态"/><el-table-column prop="publication.validUntil" label="教学有效期"/></el-table><el-form :disabled="mock||busy" label-position="top"><el-form-item label="待发布版本"><el-select v-model="selected"><el-option v-for="v in versions.filter(v=>v.status==='READY')" :key="v.id" :value="v.id" :label="`v${v.versionNumber}`"/></el-select></el-form-item><el-form-item label="关联授权"><el-select v-model="publication.authorizationId"><el-option v-for="a in auths.filter(a=>!a.revokedAt)" :key="a.id" :value="a.id" :label="a.reference"/></el-select></el-form-item><el-form-item label="教学版本有效期（不得超过授权或案例有效期）"><el-date-picker v-model="publication.validUntil" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ"/></el-form-item><el-form-item label="人工复核记录"><el-input v-model="publication.reviewNote" type="textarea"/></el-form-item><el-checkbox v-model="publication.reviewConfirmed">已人工复核，确认本版本可用于教学</el-checkbox><p><el-button type="primary" @click="publish">发布独立教学副本</el-button></p></el-form></el-card><el-card><h2>审计时间线</h2><div class="actions"><el-input v-model="action" placeholder="按事件筛选，例如 VERSION_PUBLISHED"/><el-button :disabled="mock" @click="page=1;run(timeline)">查询</el-button></div><el-timeline><el-timeline-item v-for="log in logs" :key="log.id" :timestamp="log.createdAt"><b>{{log.action}}</b> · 操作者 {{log.actorId}}<pre>{{log.detail}}</pre></el-timeline-item></el-timeline><el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" @current-change="run(timeline)"/></el-card></main></template>
````

## frontend/src/views/CaseViewerView.vue

````vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import PotreeFrame from '@/components/PotreeFrame.vue'
import { createAnnotation, createMeasurement, deleteAnnotation, deleteMeasurement, getAnnotations, getMeasurements, getViewerConfig, updateAnnotation } from '@/api/viewer'
import { getCase } from '@/api/cases'
import type { Annotation, Measurement, Point3D } from '@/types/viewer'

const route = useRoute(); const router = useRouter(); const frame = ref<InstanceType<typeof PotreeFrame>>()
const loading = ref(true); const error = ref(''); const manifestUrl = ref(''); const annotations = ref<Annotation[]>([]); const measurements = ref<Measurement[]>([]); const camera = ref<Record<string, unknown>>({}); const selectedPoint = ref<Point3D>({ x: 0, y: 0, z: 0 }); const mock = import.meta.env.VITE_USE_MOCK !== 'false'
const versionId = ref(''); const pointForm = ref({ title: '', description: '' }); const areaForm = ref({ title: '重点区域', description: '', center: [0,0,0] as [number,number,number], size: [1,1,1] as [number,number,number], rotation: [0,0,0] as [number,number,number] }); const measureForm = ref({ startPoint: { x: 0, y: 0, z: 0 }, endPoint: { x: 3, y: 4, z: 0 } })
const distance = computed(() => { const a = measureForm.value.startPoint, b = measureForm.value.endPoint; return Math.hypot(a.x-b.x, a.y-b.y, a.z-b.z).toFixed(2) })
async function reload(){ if(!versionId.value)return; [annotations.value,measurements.value]=await Promise.all([getAnnotations(versionId.value),getMeasurements(versionId.value)]) }
async function init(){ loading.value=true; try { const record=await getCase(String(route.params.caseId)); if(!record.latestVersion || !['READY','PUBLISHED'].includes(record.latestVersion.status)) { error.value='该案例尚未就绪，不能进入三维工作台。'; return } versionId.value=record.latestVersion.id; const config=await getViewerConfig(versionId.value); manifestUrl.value=config.manifestUrl; await reload() } catch(e){error.value=e instanceof Error?e.message:'工作台初始化失败'} finally{loading.value=false} }
function picked(point: Point3D){ selectedPoint.value=point; ElMessage.success('已获取当前点位坐标，可填写标记说明后保存') }
function measured(points: { startPoint: Point3D; endPoint: Point3D }) { measureForm.value = points; ElMessage.success('已获取两点测距，可保存记录') }
function selectedArea(area: { center: [number, number, number]; size: [number, number, number]; rotation: [number, number, number] }) { areaForm.value = { ...areaForm.value, ...area }; ElMessage.success('已获取重点区域包围盒，可填写说明后保存') }
async function savePoint(){ if(!pointForm.value.title.trim()) { ElMessage.warning('请输入标记标题'); return } await createAnnotation(versionId.value,{type:'POINT_MARK',geometry:{position:selectedPoint.value},title:pointForm.value.title,description:pointForm.value.description,viewerState:{camera:camera.value}}); pointForm.value={title:'',description:''}; await reload(); ElMessage.success('点位标记已保存') }
async function saveArea(){ if(!areaForm.value.title.trim()){ElMessage.warning('请输入区域标题');return} await createAnnotation(versionId.value,{type:'AREA_MARK',geometry:{...areaForm.value},title:areaForm.value.title,description:areaForm.value.description,viewerState:{camera:camera.value}});await reload();ElMessage.success('重点区域已保存') }
async function saveMeasurement(){await createMeasurement(versionId.value,measureForm.value);await reload();ElMessage.success('测距记录已保存')}
async function removeAnnotation(item: Annotation){await ElMessageBox.confirm(`删除标记“${item.title}”？`,'确认删除',{type:'warning'});await deleteAnnotation(item.id);await reload()}
async function editAnnotation(item: Annotation){const { value }=await ElMessageBox.prompt('标记标题','编辑标记',{inputValue:item.title});await updateAnnotation(item.id,{...item,title:value});await reload()}
async function removeMeasurement(item: Measurement){await ElMessageBox.confirm('删除这条测距记录？','确认删除',{type:'warning'});await deleteMeasurement(item.id);await reload()}
onMounted(init)
</script>
<template><main class="workspace"><header><div><p>管理员 / 三维工作台</p><h1>点云浏览与标记</h1></div><div><el-tag v-if="mock" type="warning">模拟 Viewer 模式</el-tag><el-button @click="router.back()">返回详情</el-button></div></header><el-alert v-if="error" title="无法加载三维工作台" :description="error" type="error" :closable="false" show-icon /><el-skeleton v-else-if="loading" :rows="12" animated /><section v-else class="layout"><div class="viewer"><PotreeFrame ref="frame" :manifest-url="manifestUrl" :mock="mock" @error="error=$event" @camera="camera=$event" @pick="picked" @measurement="measured" @area="selectedArea" /></div><aside><el-alert v-if="mock" title="模拟 Viewer 模式" description="未加载或伪造真实点云；可用于演示标记和测距数据流程。" type="warning" :closable="false"/><el-tabs><el-tab-pane label="新增工具"><el-button-group><el-button @click="frame?.startPointPick()">新增点标记</el-button><el-button @click="frame?.startArea()">重点区域</el-button><el-button @click="frame?.startMeasurement()">测距</el-button><el-button @click="frame?.resetView()">复位视角</el-button></el-button-group><el-divider>点位标记</el-divider><el-input v-model="pointForm.title" placeholder="标记标题"/><el-input v-model="pointForm.description" type="textarea" placeholder="描述"/><p class="coord">当前点：{{ selectedPoint.x.toFixed(2) }}, {{ selectedPoint.y.toFixed(2) }}, {{ selectedPoint.z.toFixed(2) }}</p><p class="coord">相机状态：{{ Object.keys(camera).length ? '已同步' : '等待 Viewer 同步' }}</p><el-button type="primary" @click="savePoint">保存点标记</el-button><el-divider>重点区域</el-divider><el-input v-model="areaForm.title" placeholder="区域标题"/><el-input v-model="areaForm.description" type="textarea" placeholder="描述"/><el-button type="primary" @click="saveArea">保存重点区域</el-button><el-divider>两点测距</el-divider><p class="coord">当前输入距离：{{ distance }} m</p><el-button type="primary" @click="saveMeasurement">保存测距</el-button></el-tab-pane><el-tab-pane label="标记列表"><el-empty v-if="!annotations.length" description="暂无标记"/><div v-for="item in annotations" :key="item.id" class="item"><b>{{ item.title }}</b><el-tag size="small">{{ item.type==='POINT_MARK'?'点位':'区域' }}</el-tag><p>{{ item.description || '无描述' }}</p><el-button link @click="editAnnotation(item)">编辑</el-button><el-button link type="danger" @click="removeAnnotation(item)">删除</el-button></div></el-tab-pane><el-tab-pane label="测距列表"><el-empty v-if="!measurements.length" description="暂无测距"/><div v-for="item in measurements" :key="item.id" class="item"><b>{{ Math.hypot(item.startPoint.x-item.endPoint.x,item.startPoint.y-item.endPoint.y,item.startPoint.z-item.endPoint.z).toFixed(2) }} m</b><p>{{ item.startPoint.x }},{{ item.startPoint.y }},{{ item.startPoint.z }} → {{ item.endPoint.x }},{{ item.endPoint.y }},{{ item.endPoint.z }}</p><el-button link type="danger" @click="removeMeasurement(item)">删除</el-button></div></el-tab-pane></el-tabs><p class="save">保存状态：数据保存至后端</p></aside></section></main></template>
<style scoped>.workspace{height:100vh;min-width:1100px;background:#f4f7fb}header{height:76px;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #dde4ee}header p{margin:0;color:#64748b;font-size:12px}h1{font-size:20px;margin:5px 0}.layout{display:grid;grid-template-columns:minmax(0,1fr) 360px;height:calc(100vh - 76px)}.viewer{min-width:0}.layout aside{overflow:auto;padding:16px;background:#fff;border-left:1px solid #dde4ee}.layout aside :deep(.el-alert){margin-bottom:14px}.layout aside :deep(.el-input){margin-bottom:8px}.coord,.save{font-size:12px;color:#64748b}.item{padding:12px 0;border-bottom:1px solid #edf1f6}.item .el-tag{margin-left:8px}.item p{font-size:12px;color:#64748b;line-height:1.5;word-break:break-all}@media(max-width:1100px){.workspace{min-width:0}.layout{grid-template-columns:1fr}.viewer{height:55vh}.layout aside{border-left:0;border-top:1px solid #dde4ee}}</style>
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
<template><main class="teacher-page" v-loading="busy"><header><h1>{{id?'任务详情':'创建教学任务'}} · {{state==='DRAFT'?'草稿':state==='PUBLISHED'?'已发布':'已关闭'}}</h1><el-button @click="router.push('/teacher/tasks')">返回任务</el-button></header><el-alert title="仅可选择已发布且授权有效的教学版本；案例过期或授权撤销后不可新建任务或供学生访问。" type="info" :closable="false"/><el-form label-position="top" :disabled="!editable||busy"><el-form-item label="课程"><el-select v-model="form.courseId" @change="courseChanged"><el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id"/></el-select></el-form-item><el-form-item label="任务名称"><el-input v-model="form.title" maxlength="200"/></el-form-item><el-form-item label="目标班级"><el-select v-model="form.classIds" multiple><el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id"/></el-select></el-form-item><el-form-item label="案例版本"><el-select v-model="form.caseVersionId"><el-option v-for="v in versions" :key="v.id" :label="`${v.teachingTitle} · v${v.versionNumber}`" :value="v.id"/></el-select></el-form-item><el-form-item label="任务说明"><el-input v-model="form.instructions" type="textarea" :rows="4"/></el-form-item><el-form-item label="开始时间（可空，立即开始）"><el-date-picker v-model="form.startAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ"/></el-form-item><el-form-item label="截止时间（可空）"><el-date-picker v-model="form.dueAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ"/></el-form-item><el-form-item label="允许迟交"><el-switch v-model="form.allowLate"/></el-form-item><h2>评分点</h2><div v-for="(r,index) in form.rubric" :key="index"><div class="rubric-row"><el-input v-model="r.title" placeholder="评分点名称" maxlength="200"/><el-input-number v-model="(r.maxScore as number)" :min="0.01" :max="99999" :precision="2"/><el-button :disabled="form.rubric.length<=1" @click="form.rubric.splice(index,1)">删除</el-button></div><el-input v-model="r.description" placeholder="评分要求" type="textarea"/></div><el-button @click="form.rubric.push({title:'',description:'',maxScore:10})">添加评分点</el-button></el-form><div class="actions"><el-button v-if="editable" type="primary" :disabled="busy" @click="save">保存草稿</el-button><el-button v-if="editable&&id" type="success" :disabled="busy" @click="transition('publish')">发布已保存的任务</el-button><el-button v-if="state==='PUBLISHED'" type="danger" :disabled="busy" @click="transition('close')">关闭任务</el-button></div><el-card v-if="state!=='DRAFT'"><h2>学生提交</h2><el-table :data="rows"><el-table-column prop="student.displayName" label="学生"/><el-table-column prop="student.username" label="用户名"/><el-table-column label="提交状态"><template #default="{row}">{{row.status==='SUBMITTED'?'已提交':row.status==='DRAFT'?'草稿':'未开始'}}</template></el-table-column><el-table-column label="提交时间"><template #default="{row}">{{displayTime(row.submittedAt)}}</template></el-table-column><el-table-column label="成绩"><template #default="{row}">{{row.gradeStatus==='PUBLISHED'?'已发布':row.gradeStatus==='DRAFT'?'批改草稿':'未批改'}} {{row.totalScore??''}}</template></el-table-column><el-table-column label="操作"><template #default="{row}"><el-button v-if="row.submissionId" link type="primary" @click="router.push(`/teacher/submissions/${row.submissionId}`)">批改 / 查看</el-button></template></el-table-column></el-table></el-card></main></template>
````
