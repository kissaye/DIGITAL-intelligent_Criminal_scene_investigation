# M4 教师教学管理交付

功能分支：`feature/m4-teacher-management`，基于 `97a49d1`。未合并 main，未推送远程。

## 实现范围

沿用 Vue 3、Element Plus、FastAPI、SQLAlchemy、Alembic、JWT 和现有三角色权限。
课程和班级管理、按完整用户名添加有效学生、任务草稿和评分点、按班级发布任务、关闭任务、批改草稿、成绩发布、学生查看本人提交和反馈。

教师只能管理自己创建的课程与任务。班级权限经课程归属校验，提交权限经任务归属校验；其他教师资源返回 404，错误角色返回 403。
管理员身份不自动授予教师权限。学生仍使用现有 task_assignments 与 submissions。

任务仅在 DRAFT 状态可编辑，发布时从班级成员生成去重后的学生分配快照。发布后所有任务内容冻结；班级成员后续变化不改变已发布名单。
评分按评分点限制得分，后端用 Decimal 累加总分；允许部分填写并保存批改草稿，发布时必须评完所有项。成绩发布后冻结，学生只能读取本人已发布成绩。

本轮继续选择 READY 且具有 viewer_manifest_key 的案例版本。不增加 M5 案例发布、有效期、教学副本或 M6 脱敏。批改页以只读文字、坐标和测距展示作业，不增加教师 Viewer 授权。

## 数据库变更

- `tasks.course_id`：可空，关联 courses；历史 M3 任务无需回填。
- `task_classes`：任务目标班级，任务/班级组合唯一。
- `task_rubric_items`：评分点、说明、Numeric(7,2) 满分、排序。
- `submission_grades`：每份提交唯一批改、教师、状态、总分、总评及时间。
- `submission_grade_items`：评分明细、单项反馈，批改/评分点组合唯一。

迁移：`backend/alembic/versions/20261031_0006_create_teacher_management.py`。
SQL：`migration.postgresql.sql`，由同一 Alembic 迁移生成，只适用于已在 M3 revision `202610300005` 的 PostgreSQL。SQL 与 Alembic 二选一执行，不能重复执行。
正常升级使用 `alembic upgrade head`；回退 `alembic downgrade 202610300005` 会删除 M4 评分和目标班级数据，保留旧任务与作业。回退前备份数据库。

## API 清单

均以 `/api/v1` 为前缀，沿用 `{code,message,data,requestId}`。请求和响应业务字段采用 camelCase。

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET / POST | /teacher/courses | 本人课程列表、创建 |
| GET / PATCH | /teacher/courses/{id} | 详情、改名 |
| POST | /teacher/courses/{id}/classes | 新建班级 |
| GET / PATCH | /teacher/classes/{id} | 班级和成员、改名 |
| GET | /teacher/students?username=student | 精确查找有效学生 |
| POST | /teacher/classes/{id}/members | 添加学生，body: {studentId} |
| DELETE | /teacher/classes/{id}/members/{studentId} | 移除成员 |
| GET | /teacher/case-versions | 选择 READY 版本的教学标题和版本号 |
| GET / POST | /teacher/tasks | 列表、新建草稿；列表支持 courseId、status |
| GET / PATCH | /teacher/tasks/{id} | 详情、替换完整草稿表单 |
| POST | /teacher/tasks/{id}/publish | 发布任务和学生分配 |
| POST | /teacher/tasks/{id}/close | 关闭任务 |
| GET | /teacher/tasks/{id}/submissions | 学生提交及批改状态 |
| GET | /teacher/submissions/{id} | 只读提交、任务评分点、批改 |
| PUT | /teacher/submissions/{id}/grade | 保存评分草稿 |
| POST | /teacher/submissions/{id}/grade/publish | 发布成绩 |
| GET | /student/submissions/{id}/grade | 本人已发布成绩 |

任务新建和修改表单示例（PATCH 使用相同完整字段，rubric 不提交 id）：

```json
{
  "courseId": "<course-id>",
  "title": "住宅现场勘验",
  "instructions": "观察现场，完成标记、测距及笔录。",
  "caseVersionId": "<ready-version-id>",
  "classIds": ["<class-id>"],
  "startAt": null,
  "dueAt": null,
  "allowLate": false,
  "rubric": [{"title": "勘验质量", "description": "观察与笔录完整", "maxScore": 100}]
}
```

时间字段必须携带时区，例如 `2026-11-10T08:00:00+08:00`，入库归一为 UTC。截止时间必须晚于开始时间，发布时截止时间不能已过。默认 SQLite 读取出的无时区时间按 UTC 解释。

批改草稿请求：

```json
{"feedback":"观察完整", "items":[{"rubricItemId":"<rubric-id>","score":90.5,"comment":"注意物证位置描述"}]}
```

403 表示角色不符，404 表示资源不存在或无归属权限，409 表示状态冲突，422 表示参数错误。

## 页面

- `/teacher/courses` 和 `/teacher/courses/:courseId`：课程、班级和成员管理。
- `/teacher/tasks`：任务筛选、提交人数。
- `/teacher/tasks/new` 和 `/teacher/tasks/:taskId`：任务、评分点、发布关闭及学生名单。
- `/teacher/submissions/:submissionId`：查看提交、单项评分、总评及发布。
- `/student/submissions/:submissionId`：本人作业和已发布成绩。
- 教师首页增加业务入口；学生任务列表增加作业与成绩入口。

## M3 配套调整

学生列表隐藏 DRAFT，关闭任务显示 CLOSED（已提交学生仍显示 SUBMITTED）。仅 IN_PROGRESS 提供进入工作台入口；已提交学生通过独立只读页面查看作业与成绩。
工作台和 Viewer 瓦片均校验任务开放时间和状态，关闭后已有 Cookie 也不能继续读取资源。学生角色、账号有效性、分配和版本绑定在资源读取时重新校验。
学生提交结构及提交后冻结规则保留；关闭任务后不再允许保存草稿或提交。
写入学生草稿/提交与教师关闭任务复用任务行锁，PostgreSQL 下避免关闭与写入交错。SQLite 不提供同等行锁能力。

## 安装和自动测试

使用 README 原有 Python 虚拟环境流程，在 backend 执行：

```powershell
pip install -r requirements-test.txt
alembic upgrade head
python -m app.seed
python -m unittest discover -s tests -v
```

测试使用独立临时 SQLite 数据库，通过真实 JWT 及 FastAPI TestClient 请求接口，不连接开发数据库。

覆盖四组场景：

1. 教师课程→班级→发布→学生草稿/提交→批改→成绩；教师隔离、三角色拒绝、学生作业隔离、提交冻结、超分拒绝、漏评拒绝、Decimal 汇总及成绩可见性。
2. M3 迁移到 M4 并回退，保留原课程和任务。
3. 非法时间/学生/其他教师班级拒绝、重复发布拒绝、成员变化不影响分配快照。
4. 未开始、已截止、允许迟交、任务关闭后禁写，以及旧 Viewer Cookie 失效。

前端验证：

```powershell
cd frontend
npm install
npm run build
```

## 手动联调步骤

1. 启动 backend 和 frontend，前端 `.env` 设置 `VITE_USE_MOCK=false`，重启 Vite。用 README 演示教师账号登录。
2. 新建课程和班级；用完整用户名 `student` 查找并加入班级。重复添加应不产生重复成员。
3. 管理员按 M1 流程准备一个 READY 版本。真实点云转换仍需要既有 PDAL/PotreeConverter 环境；本模块不改变其部署。
4. 教师新建任务，选择课程、班级和 READY 版本，填写两个评分点和时间；保存、发布。发布后不能编辑，提交名单包含学生。
5. 学生登录，查看任务，写笔录、标记和测距、等待自动保存后刷新；内容应保留。提交后不能再编辑。
6. 教师从名单进入作业，核对内容，填写部分评分并保存。学生应看不到成绩；漏评发布应失败。
7. 填完全部评分点并发布。学生在任务列表点击“作业与成绩”，查看总分、单项分和反馈；教师不能再修改已发布成绩。
8. 教师提前关闭另一未提交任务。学生刷新后应看到关闭状态；已有工作台保存/提交应返回 409，已有 Viewer Cookie 的资源请求也应拒绝。
9. 使用另一教师账号访问第一位教师课程/任务/提交应返回 404；学生访问教师 API 返回 403。

Mock 模式仅在本浏览器按教师隔离保存课程、班级与任务界面演示数据，查找学生使用 `student`。Mock 教师任务不投递到 M3 的独立模拟任务库，批改需真实接口；首页明确提示。这避免把浏览器演示当成服务端权限和教学闭环验证。

## 实际验证与限制

- 已通过：4 组后端自动测试、Python 编译检查、Vue/TypeScript 检查及 Vite 生产构建。
- 已验证 SQLite 的 M3→M4 升级、回退、旧数据保留。
- PostgreSQL SQL 已由迁移离线生成；未在 PostgreSQL 实例运行，未验证并发压力。
- 未进行浏览器逐页人工操作、真实点云加载或 Docker 全栈联调。
- Vite 仍提示既有主包较大；本次没有调整打包架构。

## Commit 信息

```text
feat(m4): add teacher course, task and grading workflows

- add teacher-owned courses, classes and student membership
- publish class task assignments with frozen rubrics
- add submission grading drafts and published student feedback
- enforce M3 task closure and viewer access checks
- add backward-compatible migration, SQL and regression tests
```

`complete-code.md` 收录所有改动实现文件的完整内容；`files.md` 列出修改文件及用途。
