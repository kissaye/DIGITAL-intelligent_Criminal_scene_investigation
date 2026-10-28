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

## 当前资料

- `刑侦三维案例脱敏与教学实训平台 PRD V1.0.docx`
- `刑侦三维案例平台 安全合规与竞赛材料包.docx`
- `build_prd_baseline.py` 与 `build_compliance_pack.py`：以上文档的生成脚本。
