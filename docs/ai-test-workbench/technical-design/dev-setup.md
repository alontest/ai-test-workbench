# Dev Setup — ai-test-workbench（workbench-core）

> 时期说明：本文档为 2026-11-18 `workbench-core` 历史规格快照。2026-11-23 起项目已统一更名为 `vigil-workbench`，源码迁移至 `src/vigil_workbench/`，环境变量 `AW_*` / `AW_KB_*` 已切换为 `VIGIL_*` / `VIGIL_KB_*` / `VIGIL_ENCRYPTION_KEY`，Cookie 切换为 `vigil_session`，默认库切换为 `vigil.db` / `vigil`。最新实现与部署清单请以 `docs/dev-setup.md` 和 `AGENTS.md` 为准。

> 阶段：tech-tasks（步骤 8）。适用于本地开发、测试门禁与 CI。生产部署见同目录 `file-structure.md` 的部署工件与 `scripts/backup.sh` 说明。
>
> 注：本文档产出于 AlonWorkflow 时期，其中 `aw` / `.aw/` 相关命令已随该工作流移除而失效；当前以 `uv run pytest` 与 CI 三 job 为门禁，实现交付版说明见 `docs/dev-setup.md`。

## 1. 运行时与工具

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+（本机 3.14.7 可用） | 后端、迁移、测试 |
| uv | 最新稳定版 | 依赖安装与锁定（`uv.lock`） |
| Node.js | 22 LTS+ | 前端构建（`web/`） |
| npm | 随 Node | 前端依赖与脚本 |
| Docker + Compose | 可选 | MySQL 8.4 与容器化验收 |
| MySQL | 8.4 LTS（`mysql:8.4`） | 生产库与 CI 第二 job；账号需 DDL 权限 |

- 测试门禁：`uv run pytest`（`code_paths` 为 `src/`、`tests/`、`web/`）。

## 2. 环境变量

| 变量 | 必需 | 默认 | 说明 |
|------|------|------|------|
| `AW_ADMIN_PASSWORD` | 是 | — | 管理员口令；缺失或为空拒绝启动；轮换 = 改值后重启 |
| `AW_ENCRYPTION_KEY` | 是 | — | 32 字节 base64；用于 AES-256-GCM；丢失则已存提供商密钥不可解 |
| `AW_DATABASE_URL` | 生产必需 | `sqlite+aiosqlite:///<AW_DATA_DIR>/workbench.db` | MySQL 用 `mysql+asyncmy://user:<password>@host:3306/db?charset=utf8mb4`（口令通过环境变量注入，不写进仓库） |
| `AW_DATA_DIR` | 否 | `./data` | 制品目录、`.trash/`、`.tmp/`、开发 SQLite；不承载生产库 |
| `AW_PUBLIC_ORIGIN` | 远程部署必需 | 空 | 允许的 Origin 列表（CSRF 校验）；如 `https://workbench.example.com` |
| `AW_COOKIE_SECURE` | 否 | `auto` | `auto|true|false`；`auto` 按 `AW_PUBLIC_ORIGIN` 的 scheme 判定 |
| `AW_TRUST_PROXY` | 否 | `0` | `1` 时取 `X-Forwarded-For` 首跳；默认取直连对端 |
| `AW_ALLOW_REMOTE` | 否 | `0` | 非回环绑定必须显式设为 `1` 并接受启动告警 |
| `AW_AI_MAX_CONCURRENCY` | 否 | `4` | 进程内 AI 调用并发上限 |
| `AW_PROMPT_MAX_CHARS` | 否 | `200000` | 粘贴正文与调用提示共用上限 |

- `.env.example` 只写占位与说明，不写真实密钥；`.env` 加入 `.gitignore`。

## 3. 本地启动（SQLite）

```bash
uv sync --frozen
cp .env.example .env            # 填入 AW_ADMIN_PASSWORD 与 AW_ENCRYPTION_KEY
python3 -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"  # 生成加密口令
alembic upgrade head
uvicorn workbench.main:app --reload --port 8000
```

- 首次启动会写入管理员凭据并把遗留 `running` 调用归并为 `failed(interrupted)`。
- 登录页：`http://127.0.0.1:8000/login`。

## 4. 前端开发

```bash
cd web
npm ci
npm run dev        # Vite dev server，proxy 到 127.0.0.1:8000
npm run build      # 产物 web/dist，由后端同源托管
```

- 前端只消费 `web/src/styles/tokens.css`，不新增 token（需要新 token 应回到 interaction-design）。
- 必过门禁：`npm run test -- --run`（Vitest + Testing Library，OQ-TT-03 已确认）；提交前与 CI 都要求通过。
- 可选（P1，不进门禁）：`npx playwright test`（关键闭环 E2E）。

## 5. 测试与门禁

```bash
uv run pytest                            # 默认 SQLite
AW_TEST_DATABASE_URL='mysql+asyncmy://...?charset=utf8mb4' uv run pytest tests/test_db_migrations.py
cd web && npm run test -- --run          # Vitest 组件单测（必过）
```

- 用例名必须带 TC 编号：`test_tc012_upload_rejects_oversize`。
- **SQLite 绿不等于双方言通过**；MySQL 由 CI 第二 job 与本地 `AW_TEST_DATABASE_URL` 复跑（RISK-011）。
- 本地无 Docker 时 MySQL 用例应 `skip` 并在报告中标注，不能当作通过。

## 6. Docker Compose

```bash
cp .env.example .env    # 配置 AW_PUBLIC_ORIGIN / AW_COOKIE_SECURE / 口令
docker compose up --build
```

- 入口脚本先 `alembic upgrade head` 再起 Uvicorn；`app` 依赖 `db` healthy。
- 默认端口 `127.0.0.1:8000:8000`；对外暴露前必须配 TLS 反代并设置 `AW_PUBLIC_ORIGIN`（OQ-ARCH-05 A）。
- 外接 MySQL：注释/停用 `db` 服务，`AW_DATABASE_URL` 指向现有实例。

## 7. CI

- CI 由 TASK-TD-018 落地为 `.github/workflows/ci.yml`（GitHub Actions，OQ-TT-01）。
- job 1：SQLite 跑 `uv run pytest`；job 2：`mysql:8.4` service + `AW_TEST_DATABASE_URL`，先迁移后跑同一套用例；job 3：`cd web && npm ci && npm run test -- --run`（Vitest，OQ-TT-03）。三个 job 都是必过；Playwright E2E 不进必过门禁。
- 从零重跑测试与 job 1 等价：`uv run pytest -q`。

## 8. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 启动即退出，提示缺少 `AW_ADMIN_PASSWORD` | 环境变量缺失/空 | 设置后重启（AC-REQ-17） |
| 提示 `alembic upgrade head` | schema 版本不等于 head | 执行迁移；应用不自动迁移 |
| 登录一直 429 | 同来源连续失败 5 次锁定 5 分钟 | 等待 `Retry-After`；反代场景检查 `AW_TRUST_PROXY` |
| 写请求 403 `forbidden_origin` | `AW_PUBLIC_ORIGIN` 未配或与实际地址不符 | 配置为实际访问地址（含 scheme/端口） |
| 连接测试 `credential_unavailable` | `AW_ENCRYPTION_KEY` 变更导致旧密文不可解 | 重新登记提供商密钥 |
| SQLite 报 `database is locked` | 开发态并发写 | 确认 WAL + `busy_timeout`；外部调用不在事务内 |
