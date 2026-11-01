# M5 案例版本与审计

分支 `feature/m5-version-audit` 基于 M4 提交 `7091d82`；未合并 main。本模块依赖 M4，合并顺序为 M4 → M5。沿用现有 FastAPI、SQLAlchemy、Alembic、Vue 3、Element Plus、JWT 三角色体系，不涉及 M6。

## 功能与规则

- 管理员登记案例授权编号、范围和截止时间，支持撤销；仅登记授权元数据，不上传原件，也不自动判断法律授权真实性。
- READY 版本必须关联同案例的有效授权，填写人工复核记录并确认后，才能发布为 PUBLISHED。
- 发布将转换目录中的 JSON/BIN 文件复制到独立 `STORAGE_ROOT/teaching/<uuid>/`，计算整个副本的 SHA-256；拒绝原始点云文件、符号链接和越界目录。
- 教学副本不通过静态目录公开。学生 Viewer 沿用短期 HttpOnly Cookie，经受控代理读取教学副本。
- 发布有效期不得超过案例和授权有效期。选择版本、新建任务、发布任务、学生工作台、每次瓦片访问、保存和提交都检查有效期及授权撤销。
- 原有 READY 案例不会被自动发布。升级后，旧任务需由管理员完成对应版本授权登记和人工发布，才能继续实训；历史作业、已发布成绩仍可只读访问。
- 无覆盖已有版本的接口；转换 worker 拒绝重跑已发布或已绑定任务的版本。原有文件上传仅新增 UUID 文件，不覆盖旧文件。
- 新建转换版本支持可选 `parentVersionId`，校验父版本属于同一案例；版本列表显示父版本，实现谱系查询。
- 管理员可按案例、版本、操作者、事件和时间筛选审计日志，分页查询。案例页显示日志时间线，既有上传、浏览、提交、评分记录均纳入查询。

## 数据库与接口

迁移 `202611010007`，接续 M4 `202610310006`：

- `case_versions.parent_version_id`：可空自引用外键，保留旧版本。
- `case_authorizations`：案例、授权编号、范围、有效期、撤销时间及登记人。
- `teaching_copies`：版本唯一、副本路径、校验和、复核记录、授权、有效期、发布人及时间。

在 backend 执行 `alembic upgrade head`。同目录 `migration.postgresql.sql` 是仅从 M4 升级至 M5 的 PostgreSQL SQL，由同一迁移离线生成；SQL 和 Alembic 二选一，不可重复执行。

回退 `alembic downgrade 202610310006` 删除 M5 数据表并将 PUBLISHED 还原 READY。发布副本文件保留在 storage，避免破坏数据；不自动清理。迁移未复制或自动发布真实案例。

全部接口前缀 `/api/v1`，新增接口仅允许 ADMIN，沿用 APIResponse：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET / POST | /cases/{caseId}/authorizations | 查询/登记授权 |
| POST | /authorizations/{id}/revoke | 撤销授权，重复撤销 409 |
| GET | /cases/{caseId}/versions | 版本谱系、发布信息 |
| POST | /case-versions/{id}/publish | 发布独立教学副本 |
| GET | /audit-logs | caseId、versionId、actorId、action、startAt、endAt、offset、limit |

登记授权请求：`{"reference":"授权材料编号","scope":"许可范围","validUntil":"2027-01-01T00:00:00+08:00"}`。

发布请求：`{"authorizationId":"<id>","validUntil":"2026-12-01T00:00:00+08:00","reviewConfirmed":true,"reviewNote":"人工复核记录"}`。

有效期必须携带时区。缺失复核确认、超出授权有效期返回 422；未就绪、已发布、无有效授权返回 409。

版本创建沿用原 `POST /cases/{id}/versions`，增加可选 `parentVersionId`。父版本归属错误返回 422。

## 页面与手动验收

管理员案例详情点击“发布与审计”，进入 `/admin/cases/:caseId/publication`。该页需要 `VITE_USE_MOCK=false` 和真实管理员登录，Mock 模式明确提示并禁止提交。

1. 升级数据库、启动前后端，准备一个真实转换成功的 READY 版本。
2. 管理员进入发布页，添加授权编号、范围、有效期；确认记录进入列表。
3. 选择 READY 版本及授权，填写更早的教学有效期，填写复核记录并勾选确认，发布。页面显示 PUBLISHED 和有效期。
4. 教师创建/发布任务，应仅能选择有效的已发布教学版本。学生进入工作台，保存和提交应正常。
5. 撤销授权后，教师选择列表隐藏该版本；已有学生工作台保存、提交和瓦片请求应被拒绝。
6. 同样验证教学有效期、案例有效期、授权有效期任一届满后禁止使用。历史作业和已发布成绩仍可查看。
7. 在时间线按 VERSION_PUBLISHED、AUTHORIZATION_REVOKED、SUBMISSION_CREATED、GRADE_PUBLISHED 筛选，确认案例相关记录可查。
8. Swagger 创建新版本时传 parentVersionId，检查版本谱系；新转换不会改写旧教学副本。

## 自动测试及实际验证

backend 执行 `python -m unittest discover -s tests -v`，frontend 执行 `npm run build`。
测试使用临时 SQLite 和合成 JSON/BIN 文件，不使用真实案件。M4 测试夹具补上有效发布数据，不绕过服务端发布检查。

覆盖原 M4 教学闭环及迁移回退，以及 M5 副本独立、人工复核/角色限制、重复发布、越界授权有效期、禁复制 LAS、授权撤销、到期禁任务/提交、旧 Cookie 拒绝、审计查询和发布后拒绝重转换。

限制：PostgreSQL SQL 仅离线生成，未进行 PostgreSQL 实库/并发测试；未逐页人工验收或加载真实点云。发布是同步磁盘复制，大点云的耗时及容量需在实际环境验证；发布副本应与数据库共同备份。不会自动删除到期副本。

实际执行结果：8 项后端测试全部通过；TypeScript 检查及 Vite 生产构建通过。

## 交付

`files.md` 为修改清单；`complete-code.md` 为本模块所有改动文件完整内容；`migration.postgresql.sql` 为数据库 SQL。

建议 commit：

```text
feat(m5): add teaching publication, authorization and audit workflows
```
