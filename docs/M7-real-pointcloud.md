# M7 真实点云环境与验收

## 当前执行记录

2026-11-08，本次改动位于 `feature/m7-real-pointcloud`，基础工作区只有未跟踪的 `build_prd.py`。该文件保持原样。

已在 Docker Desktop 29.9.2 / Compose v5.6.1 / WSL 2 环境完成真实构建与端到端验收。PostgreSQL、Redis、API、RQ Worker 和前端均成功启动，迁移从空库执行到 `202611050009`，后端与 Worker 健康检查通过。容器中实测 PDAL 2.8.4，PotreeConverter 2.1.1 revision 为 `d9387d52807bf8936fe98096b9992ea13b50ba94`。

本机项目虚拟环境已安装 RQ 1.16.2、redis Python 客户端 5.3.1，尚无可用的本机 PDAL、PotreeConverter。Redis 客户端版本与 Redis 服务版本独立。

## 镜像与启动

API、迁移和 Worker 使用同一后端镜像。Dockerfile 固定 PDAL 2.8.4、PotreeConverter 2.1.1，Potree 从发布 tag 编译，并保存实际 Git revision 到 `/usr/local/bin/POTREE_REVISION`。micromamba 固定为 2.0.5。工具下载和编译尚未在本会话验证，基础镜像、系统包及传递依赖仍采用上游仓库解析结果。

Compose 显式设置项目名 `scene-pointcloud`，避免中文目录名导致 `project name must not be empty`。若之前用其他项目名启动过服务，请继续使用原有 `-p` 项目名，以便关联原有命名卷。

在能访问 Engine 的 PowerShell 中，从项目根目录执行。首次构建需要联网下载编译依赖和 conda 包。

```powershell
docker compose build
docker compose up -d
docker compose ps -a
docker compose logs --no-color migrate backend worker
docker compose exec backend alembic current
docker compose exec backend pdal --version
docker compose exec backend PotreeConverter --help
docker compose exec backend cat /usr/local/bin/POTREE_REVISION
docker compose exec redis redis-server --version
docker compose exec backend python -m pip show rq redis
```

`migrate` 执行 `alembic upgrade head && python -m app.seed`，正常退出后 API 和 Worker 才启动。迁移服务状态为 `Exited (0)` 属于预期。预置演示账号密码沿用 `M0DemoPass!2026`。API readiness 检查数据库和 Redis，Worker 检查 Redis 中本容器的注册信息与心跳。数据库和 Redis 没有映射宿主机端口，API 仅绑定本机 127.0.0.1。

## 真实数据验收

`backend/scripts/demo_las.py` 使用 Python 标准库生成原创新造数据，按 CC0-1.0 提供。数据是坐标 0 到 9 的 10×10×10 彩色网格，共 1000 点，LAS 1.2 point format 2，26227 字节。它不含任何测绘地点或案件数据。

演示数据已在真实工具链中验收。LAS 与经 PDAL 生成的 LAZ 均转换为 `READY / SUCCEEDED`，点数均为 1000。DELETE BOX 派生版本为 875 点，产物哈希、独立受控路径、审计记录及后续 Potree 转换全部通过。完整报告位于 `storage/verification/m7-result.json`，其 `passed` 为 `true`。

```powershell
docker compose exec backend python scripts/verify_m7.py
docker compose exec backend cat storage/verification/m7-result.json
docker compose logs --no-color --timestamps backend worker
```

验收脚本通过真实 HTTP 请求创建案件、上传 LAS，再由真实 PDAL 生成 LAZ 并上传。两次转换均由 RQ Worker 消费。脚本轮询 API 状态，要求两次均为 1000 点且 `READY/SUCCEEDED`，随后验证物理 Potree 文件。它还探测无凭证的原始文件 URL，以及有 Viewer Cookie 的 LAS/LAZ 与路径越界请求。

DELETE BOX 使用 `min=[-0.5,-0.5,-0.5]`、`max=[4.5,4.5,4.5]`，预计删除 125 点。验收要求派生文件独立、点数恰为 875、文件 SHA-256 与数据库一致、父文件校验和保持一致、DELETE 审计写入，并生成通过校验的 Potree 成果。

脚本任何断言失败都会非零退出，JSON 的 `passed` 保持 false。报告包含工具输出、版本 ID、观察到的状态、文件大小和 DELETE 校验结果。小数据任务可能过快，轮询未必捕捉到每个中间状态，Worker 日志和审计可补充证据。脚本在容器中运行，使用生产数据库和存储配置，只新增合成验收案件。

## 状态与受控路径

| 阶段 | 版本状态 | Job 状态 |
| --- | --- | --- |
| 创建并入队 | PROCESSING | PENDING |
| Worker 转换 | PROCESSING | RUNNING |
| 工具成功且成果校验通过 | READY | SUCCEEDED |
| 队列、工具、数据或成果失败 | FAILED | FAILED |

`metadata.json` 存在不足以通过校验。Worker 还要求 Potree 2.0、metadata 点数与 PDAL 相同、属性步长有效、hierarchy chunk 完整、proxy 无循环、子节点完整、每个 tile 位于 octree 文件范围内、未压缩 tile 字节数与点数匹配、点数总和相同且数据区间不重叠。空点云会明确失败。校验检查文件结构和引用完整性，不解码压缩后的坐标内容。

RQ timeout 按工具执行次数设置，普通转换为两次工具超时加 60 秒，DELETE 为三次工具超时加 60 秒。已有成功 Job 重复调用直接返回。失败任务如已留有 Potree 输出，要求新建版本，避免旧成果被误用。

受控存储卷内的预期文件如下，实际 ID 由 API 分配。

```text
/app/storage/cases/<case-id>/raw/<file-id>.las
/app/storage/cases/<case-id>/raw/<file-id>.laz
/app/storage/cases/<case-id>/derived/<derived-version-id>/<file-id>.las
/app/storage/cases/<case-id>/versions/<version-id>/potree/metadata.json
/app/storage/cases/<case-id>/versions/<version-id>/potree/hierarchy.bin
/app/storage/cases/<case-id>/versions/<version-id>/potree/octree.bin
/app/storage/verification/m7-result.json
```

存储根目录没有公开静态映射。Viewer 接口使用版本绑定 Cookie，只允许受控成果目录中的 `.json`、`.bin`，拒绝路径越界和 `.las/.laz`。本次补齐了真实 HTTP 探测脚本，运行结果仍受 Engine 权限阻塞。

## 自动化测试

```powershell
docker compose exec backend python -m pip install -r requirements-test.txt
docker compose exec backend python -m pytest tests -q
```

在 Linux 容器中执行全量后端测试，结果为 **26 passed**；补充真实 Potree LEAF 子节结构回归后为 27 项。覆盖 M5、M6、M7，包括迁移、权限、发布、脱敏、PDAL 元数据、Potree 完整性和 Worker 失败持久化。`docker compose config --quiet`、Python 编译检查和 `git diff --check` 均通过。

## 未完成项和风险

- 当前验收数据为 1000 点合成小数据，尚未对 GB 级点云的时间、内存和磁盘占用进行压测。
- 本轮已验证 API 访问隔离与受控 Viewer 资源，但真实浏览器的完整点云渲染和大数据流式加载仍应单独验收。
- 如果 Worker 被强制终止或宿主机掉电，RQ 失败与业务数据库状态仍可能需要对账，当前没有自动恢复 RUNNING Job 的守护进程。
- PDAL/Potree 处理大文件的资源限制及恶意文件解析隔离尚未压测。当前验收规模为合成小数据。
