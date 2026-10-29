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

## 当前资料

- `刑侦三维案例脱敏与教学实训平台 PRD V1.0.docx`
- `刑侦三维案例平台 安全合规与竞赛材料包.docx`
- `build_prd_baseline.py` 与 `build_compliance_pack.py`：以上文档的生成脚本。
