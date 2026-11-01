# PostgreSQL 迁移实测报告

日期：2026-11-01（Asia/Shanghai）。代码基线：M5 `70f7d60`，没有修改迁移实现。

**结论：隔离 PostgreSQL 实库迁移验证通过。没有迁移生产数据库或用户真实案件数据。**

## 环境

- PostgreSQL 16.15，Windows x64，与 Docker Compose 使用相同主版本 16。
- 二进制来源：[EDB 官方发行包](https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip)，通过 [PostgreSQL Windows 下载入口](https://www.postgresql.org/download/windows/) 提供的二进制发行方式获取。
- 独立实例仅监听 `127.0.0.1:55432`，不安装系统服务；验证结束后停止。
- 数据库 `diep_migration_check`；备份恢复目标 `diep_migration_check_restore`。
- PostgreSQL 运行时、数据文件、备份和合成点云位于已忽略的 `tmp/pg-validation/`，不上传 GitHub。
- Python 使用现有项目虚拟环境与 psycopg/SQLAlchemy/Alembic，不增加运行框架。

## 实测结果

| 检查 | 结果 |
| --- | --- |
| 从空库执行既有迁移至 M3 `202610300005` | 通过 |
| M3 pg_dump 自定义格式备份 | 通过 |
| M3 → M4 `202610310006` | 通过，旧数据逐字段一致 |
| M4 → M5 `202611010007` | 通过，旧数据逐字段一致 |
| tasks.course_id、case_versions.parent_version_id 对旧记录保持 NULL | 通过 |
| M5 → M4 → M3 回退 | 通过，旧数据逐字段一致 |
| 回退后再次升级到 M5 | 通过 |
| 备份 pg_restore 至另一空库 | 通过，所有合成 M3 记录一致 |
| 已迁移 PostgreSQL 上执行发布→任务→提交→评分→学生反馈 | 通过 |
| Decimal 两项 60.10 + 39.90 汇总 | 100.00 |
| 授权撤销后新建任务 | 返回 409，符合预期 |

旧数据覆盖 15 张表、21 条合成记录：角色、用户、角色关系、案例、源文件、版本、课程、班级、成员、任务、分配、提交、标记、测距和审计。
完整机器结果见 `postgresql-validation.json`，包括数据库版本、迁移 revision、各表条数和原始数据摘要。

## 重复验证

脚本 `backend/tests/validate_postgresql_migrations.py` 仅接受本机、数据库名以 `diep_migration_check` 开头的**空数据库**；遇到已有表立即退出。

准备隔离 PostgreSQL 实例及两个空数据库，然后从 backend 运行：

```powershell
$env:PG_VALIDATION_URL='postgresql+psycopg://<test-user>@127.0.0.1:55432/diep_migration_check'
$env:PG_VALIDATION_BIN='<PostgreSQL bin 的绝对路径>'
python tests/validate_postgresql_migrations.py
```

若指定 PG_VALIDATION_BIN，必须预先创建 `diep_migration_check_restore` 空库，脚本将测试 pg_dump/pg_restore。不指定则跳过备份恢复，仍执行迁移与接口检查。
每次验证使用新的空库；脚本不会删除已有数据库。合成账号不提供可登录密码，接口使用既有 JWT 签发流程进行验证。

## 范围与后续部署

本次没有发现需要修复的 PostgreSQL 迁移差异，既有 M4/M5 迁移可在实测 PostgreSQL 16 上执行。
这消除了此前“仅离线生成 SQL、未验证 PostgreSQL”的缺口；仍未验证生产数据规模、并发、浏览器逐页交互或真实点云转换。

真实部署时应先备份目标 PostgreSQL 和 storage，再在 M4/M5 代码版本下执行 `alembic upgrade head`。
M5 不自动发布旧 READY 版本，升级后管理员需登记授权并人工发布对应教学版本，旧任务才能继续实训。
回退测试只对无 M4/M5 业务数据的合成迁移场景验证旧数据保留；生产库回退会删除 M4/M5 新增表中的业务数据，应使用经验证的备份恢复方案。

main 未改动，验证脚本和报告随 M5 功能分支提交。
