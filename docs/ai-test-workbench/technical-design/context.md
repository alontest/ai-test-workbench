# Tech Tasks Context → test-verification

> **文档状态：draft — 2026-11-18 因跨 spec 知识库注入扩展（A101 / A102 / A103 B）变更，待用户重新确认。**
> 2026-11-18 依赖版本核实：FastAPI 0.163.2、SQLAlchemy 2.1.9、pydantic-settings 2.16.3，均为实际安装版本，无降级（见 ADR-043）。

## 模块名称

ai-test-workbench（本 spec 只覆盖 `workbench-core` 域）

## 归档路径

- spec：`specs/ai-test-workbench_20261117184149/`
- 阶段产物：`specs/ai-test-workbench_20261117184149/technical-design/`（`requirements.md`、`tasks.md`、`docs/`）
- 知识库目标（用户确认后由编排者 `kb-sync` 提升）：`docs/ai-test-workbench/technical-design/`

## 技术栈

Python 3.12+ / FastAPI 0.163.2 / Uvicorn 0.54 / Pydantic 2.14 / pydantic-settings 2.16.3 / SQLAlchemy 2.1.9 async / Alembic 1.20 / aiosqlite（开发测试）/ asyncmy（MySQL 8.4 生产）/ argon2-cffi / cryptography AES-256-GCM / openai 3.52 + anthropic 2.9 SDK；React 19.3 + TypeScript 7.0 + Vite 8.3 + React Router 8.5 + TanStack Query 5.107 + Radix Primitives；CSS 变量 + CSS Modules；测试 pytest + httpx + Vitest（必过门禁）+ Playwright（可选）。

## 数据库

- 生产 MySQL 8.4 LTS（InnoDB / utf8mb4 / `utf8mb4_0900_ai_ci`）；开发与默认测试 SQLite（aiosqlite）。
- 10 张表：`admin_credential`、`login_session`、`login_attempt`、`project_context`、`provider_config`、`model_binding`、`analysis_session`、`session_event`、`artifact`、`ai_call_record`。
- 迁移：单 Alembic 树，`0001_auth` ~ `0005_ai_call_record`，2026-11-18 追加 `0006_knowledge_injection`（先于 knowledge-base 的 `0007`）；应用只校验 `alembic_version == head`，不自动迁移。
- 删除口径：只删整个会话并级联事件/制品/调用记录；项目、提供商、模型只停用，外键 `RESTRICT`。

## API

- 基址 `/api/v1`，30 个端点（认证 3、入口 1、项目 4、提供商 5、模型 4、会话 6、文本输入 1、制品 3、调用 3）。
- 认证：除 `POST /api/v1/auth/login` 外全部要求 `aw_session` Cookie；401 不含业务字段；HTML 导航未登录 302 `/login?next=`。
- 错误体 `{code, message, details[], requestId}`；列表 `limit` + `cursor`（base64url）。
- 非安全方法校验 Origin/Referer 命中 `AW_PUBLIC_ORIGIN`，否则 403 `forbidden_origin`。

## 核心模块

`core`（常量/入口/加密/口令/脱敏）、`db`（Base/引擎/10 模型/仓储）、`services`（auth/projects/providers/models/sessions/artifacts/calls/ai_gateway）、`adapters`（ai 两协议、fs 存储）、`api`（deps/errors/pagination/schemas/v1）、`startup`、`web`（SPA；项目页含 `ProjectKnowledgeSummary` 空挂载位）。

## 任务

- 55 个任务，分 4 批（`tasks.md` §任务分组）：
  - 批次 A：TASK-TD-001 ~ 018，基座、数据层、冻结契约、CI；
  - 批次 B：TASK-TD-019 ~ 041，登录 → 项目 → 提供商/模型 → 会话 → 文本/上传 → 调用；
  - 批次 C：TASK-TD-042 ~ 050，调用查询、六入口、部署与备份。
  - 批次 D：TASK-TD-051 ~ 055，跨 spec 知识库注入扩展（迁移 0006、网关 injection、`/ai/complete`、序列化与契约测试）。
- 复杂度：XS 3 / S 18 / M 29；估算 449h（约 94 人日，4.8h/日）。
- CI：GitHub Actions 三个必过 job（SQLite pytest / MySQL pytest / 前端 Vitest），OQ-TT-01、OQ-TT-03 已确认。
- 无测试任务（`[no-test]`）：TASK-TD-001（依赖配置）、TASK-TD-018（CI 配置）、TASK-TD-048（部署工件）、TASK-TD-049（备份脚本）、TASK-TD-050（文档）。

## TC 与覆盖

- 70 个 TC：功能 AC 42 条全覆盖（TC-001 ~ TC-056），AC-TECH 6 条全覆盖（TC-057 ~ TC-063），跨 spec 扩展 TC-064 ~ TC-070（A101 ~ A103）。
- 测试框架：pytest + pytest-asyncio + httpx `ASGITransport`；用例名带 `test_tcNNN_*`。
- TC 与实现：70 个 TC 全部由 pytest 给出权威结果（含 TC-064 ~ TC-070）；前端 Vitest 用例复用**同一 TC 编号**作为 UI 层第二实现（如 `TC-026 创建会话缺模型时禁用提交`），不产生专属 TC，也不存在只由 Vitest 提供结果的 TC。知识库自身逻辑的用例属 knowledge-base spec。
- 结果可见性：`aw.py verify` / `aw close` 只解析 pytest，Vitest 结果**不进入** `.aw` 证据；UI 用例的通过与失败只能从 CI 必过 job 3（`frontend-tests`）及其测试报告看到，靠分支保护兜底。评审必须同时看 CI 三个 job 全绿 + `aw verify` 绿。
- MySQL 覆盖：`tests/test_db_migrations.py` 在 `AW_TEST_DATABASE_URL` 存在时复跑；CI job 2（`mysql-tests`）必须绿，不新增 TC。
- Playwright E2E 不进必过门禁。

## 风险

| 风险 | 影响 | 测试关注 |
|------|------|---------|
| RISK-001 密钥泄露 | Critical | TC-063、TC-017：响应/日志/摘要无密钥 |
| RISK-002 协议差异 | Critical | TC-019、TC-021、TC-042、TC-045：错误分类与超时 |
| RISK-005 路径穿越/伪装 | Critical | TC-037、TC-039、TC-040 |
| RISK-009 范围蔓延 | Critical | 只验 In Scope；P1 可裁 |
| RISK-010 登录绕过/TLS | Critical | TC-001、TC-008、TC-010、TC-061 |
| RISK-011 双方言漂移 | Critical | TC-058、TC-059；SQLite 绿不等于通过 |
| RISK-012 口令/令牌泄露 | Critical | TC-003、TC-004、TC-005、TC-008 |
| RISK-003 长调用 | Medium | TC-045 超时/重试；前端 300s 超时人工验收 |
| RISK-006 删除残留 | Medium | TC-030 trash 与孤儿 |
| RISK-013 CSRF | Medium | TC-061 三类 Origin |

## 关键约定

- 时间由应用写 UTC naive；禁止 `NOW()` / `CURRENT_TIMESTAMP` / 方言函数。
- ID 为自增整数，API JSON number，进程内 `int`（OQ-TD-01 A）。
- `name_key` / `model_name_key` / `file_name_key` 存 `casefold()`，列级 `utf8mb4_bin`。
- 制品磁盘名 `<uuid4hex>.<ext>`，原名只存库；读取做解析后包含校验并拒绝符号链接（OQ-TD-04 A）。
- 上游 5xx/鉴权/限流/不可达/参数错误 → 502；120s 无响应 → 504 且 `status=timeout`；仅网络错误与 5xx 重试 1 次（OQ-TD-05 A）。
- 停用提供商/模型只改 `enabled`，不修改历史行；`ai_call_record` 冗余模型/提供商名称快照（OQ-TD-03 A）。
- 阈值常量集中 `core/constants.py`：200,000 字符、10MB、10 个、120s、10s、8h、5 次/5 分钟。
- UI 只消费 interaction-design 的 Design Tokens，不新增变量。

## 跨域依赖

- 冻结签名（ADR-041）：`sessions.create`、`sessions.append_event`、`artifacts.save`、`AiGateway.complete(session_id, model_id, prepared, *, temperature, max_tokens)`；名称与语义冻结，新 spec 只调用。
- `projectId` / `sessionId` / `artifactId` 为跨域引用键；其他域不跨域查询 core 数据表。
- `knowledge-base` 与 `repo-integration` 两个 spec 依赖上述签名；本 spec 的任何签名变更都属破坏性变更。
- `knowledge-base` 的项目关联知识库区块由该 spec 提供组件：本 spec 只在项目上下文页预留 `ProjectKnowledgeSummary` 空占位（`data-mount="knowledge-summary"`），不实现内容、不新增端点、不改数据模型，不影响 AC-008 系列验收（UXAMB-004，2026-11-18 11:02）。
- 200,000 字符常量由本 spec 定义一次（`AW_PROMPT_MAX_CHARS`），知识库注入沿用同一口径。

## 状态

pending（2026-11-18 产出；等待用户确认 tech-tasks，确认前不进入 test-verification。OQ-TT-01 ~ OQ-TT-04 已确认：GitHub Actions、30 端点、Vitest 必过门禁、备份手工演练）
