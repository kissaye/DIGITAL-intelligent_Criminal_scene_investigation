# M5 修改文件

功能分支 `feature/m5-version-audit`，基于 M4；本清单随功能分支提交；不合并 main。

| 文件 | 变更 |
| --- | --- |
| `README.md` | 修改 |
| `backend/alembic/versions/20261101_0007_publication_audit.py` | 新增 |
| `backend/app/api/router.py` | 修改 |
| `backend/app/api/routes/cases.py` | 修改 |
| `backend/app/api/routes/publication.py` | 新增 |
| `backend/app/api/routes/student.py` | 修改 |
| `backend/app/api/routes/teacher.py` | 修改 |
| `backend/app/api/routes/viewer.py` | 修改 |
| `backend/app/models/__init__.py` | 修改 |
| `backend/app/models/case.py` | 修改 |
| `backend/app/models/publication.py` | 新增 |
| `backend/app/schemas/case.py` | 修改 |
| `backend/app/services/conversion.py` | 修改 |
| `backend/app/services/publication.py` | 新增 |
| `backend/tests/test_m4.py` | 修改 |
| `backend/tests/test_m5.py` | 新增 |
| `docs/m5/README.md` | 新增 |
| `docs/m5/migration.postgresql.sql` | 新增 |
| `frontend/src/router/index.ts` | 修改 |
| `frontend/src/types/case.ts` | 修改 |
| `frontend/src/utils/case.ts` | 修改 |
| `frontend/src/views/CaseDetailView.vue` | 修改 |
| `frontend/src/views/CasePublicationView.vue` | 新增 |
| `frontend/src/views/CaseViewerView.vue` | 修改 |
| `frontend/src/views/TeacherTaskDetailView.vue` | 修改 |
| `docs/m5/files.md` | 新增，文件清单 |
| `docs/m5/complete-code.md` | 新增，完整代码 |
