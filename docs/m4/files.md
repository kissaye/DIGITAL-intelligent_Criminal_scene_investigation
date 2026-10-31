# M4 修改文件清单

工作分支：`feature/m4-teacher-management`。本清单随功能分支提交；不合并 main。

| 文件 | 变更 | 用途 |
| --- | --- | --- |
| `.gitignore` | 修改 | 忽略本地测试虚拟环境 |
| `README.md` | 修改 | 新增 M4 入口说明 |
| `backend/alembic/versions/20261031_0006_create_teacher_management.py` | 新增 | M3 到 M4 数据库迁移与回退 |
| `backend/app/api/deps.py` | 修改 | 教师角色鉴权 |
| `backend/app/api/router.py` | 修改 | 注册教师路由 |
| `backend/app/api/routes/student.py` | 修改 | 关闭状态、时间和学生成绩接口 |
| `backend/app/api/routes/teacher.py` | 新增 | 教师课程、班级、发布和评分 API |
| `backend/app/api/routes/viewer.py` | 修改 | 学生 Viewer 任务状态与分配复核 |
| `backend/app/models/__init__.py` | 修改 | 注册教学模型 |
| `backend/app/models/practice.py` | 修改 | 任务关联课程 |
| `backend/app/models/teaching.py` | 新增 | 目标班级、评分点与批改模型 |
| `backend/app/schemas/teacher.py` | 新增 | 教师请求模型与参数校验 |
| `backend/app/services/practice_access.py` | 新增 | 任务时间与分配校验复用 |
| `backend/requirements-test.txt` | 新增 | HTTP 测试客户端依赖 |
| `backend/tests/test_m4.py` | 新增 | JWT 接口与迁移回归测试 |
| `docs/m4/README.md` | 新增 | 交付说明或数据库 SQL |
| `docs/m4/migration.postgresql.sql` | 新增 | 交付说明或数据库 SQL |
| `frontend/src/api/student.ts` | 修改 | 学生真实/模拟提交详情 |
| `frontend/src/api/teacher.ts` | 新增 | 教师 API 客户端 |
| `frontend/src/api/teacherMock.ts` | 新增 | 隔离的浏览器界面演示存储 |
| `frontend/src/router/index.ts` | 修改 | 新增教师与成绩页面路由 |
| `frontend/src/styles/main.css` | 修改 | 教学页面共享样式 |
| `frontend/src/types/student.ts` | 修改 | 关闭状态类型 |
| `frontend/src/types/teacher.ts` | 新增 | 教学业务 TypeScript 类型 |
| `frontend/src/utils/student.ts` | 修改 | 关闭状态展示 |
| `frontend/src/views/HomeView.vue` | 修改 | 教师导航与模拟提示 |
| `frontend/src/views/StudentSubmissionView.vue` | 新增 | 教师管理/批改或学生成绩页面 |
| `frontend/src/views/StudentTaskListView.vue` | 修改 | 作业成绩入口与有效任务入口 |
| `frontend/src/views/StudentWorkspaceView.vue` | 修改 | 关闭任务禁止编辑 |
| `frontend/src/views/TeacherCoursesView.vue` | 新增 | 教师管理/批改或学生成绩页面 |
| `frontend/src/views/TeacherSubmissionView.vue` | 新增 | 教师管理/批改或学生成绩页面 |
| `frontend/src/views/TeacherTaskDetailView.vue` | 新增 | 教师管理/批改或学生成绩页面 |
| `frontend/src/views/TeacherTasksView.vue` | 新增 | 教师管理/批改或学生成绩页面 |
| `docs/m4/files.md` | 新增 | 本清单 |
| `docs/m4/complete-code.md` | 新增 | 全部改动实现文件的完整内容快照 |
