
## 2026-11-17 19:49:04

用户原话：

```
STK-001 A，STK-002 A，STK-003 A，STK-004 A
```

结论：

- STK-001 A：Python 3.12+ / FastAPI 0.163 + SQLAlchemy 2.1 / Alembic + SQLite（WAL）+ OpenAI / Anthropic 官方 SDK + cryptography；React 19.3 + TypeScript 7.0 + Vite 8.3 + React Router 8.5 + TanStack Query + CSS 变量 + Radix Primitives；单进程 Uvicorn 同源托管。
- STK-002 A：React 19 + Vite + TypeScript。
- STK-003 A：SQLite（WAL）单文件，位于 `AW_DATA_DIR`，无额外服务。
- STK-004 A：默认 `127.0.0.1:8000`；非本地绑定需 `AW_ALLOW_REMOTE=1` 并告警。
- 选 A 故 `.aw/config.json` 的 pytest 测试命令无需变更。

## 2026-11-17 19:52:50

用户原话：

```
打断一下，这不是本地部署的，所以需要mysql。不能只是sqllite。
```

用户选择（选项问答）：

- 数据库：**MySQL 生产 + SQLite 开发/测试**（推翻 STK-003 A 的「只用 SQLite」；两套方言需处理差异：JSON 字段、索引长度、事务隔离）。
- 访问控制：**加单用户登录**（推翻 AMB-004 A 的「无登录」；需回填需求层 AC，扩大本期范围）。
- 部署形态：**两种都支持**（提供 docker-compose 作为默认，同时支持只给连接串接外部 MySQL 实例）。

## 2026-11-17 20:09:45

用户选择（四项全按建议默认 A）：

- OQ-ARCH-01 A：MySQL 8.4 LTS（`mysql:8.4.13`），`utf8mb4` / `utf8mb4_0900_ai_ci`，兼容 8.0+。
- OQ-ARCH-02 A：compose 入口脚本显式执行 `alembic upgrade head`，应用只校验版本，不匹配拒启。
- OQ-ARCH-04 A：默认不信任 `X-Forwarded-For`，取直连对端；仅 `AW_TRUST_PROXY=1` 时取首跳。
- OQ-ARCH-05 A：compose 不含 TLS，文档要求反代（Caddy/nginx）+ `AW_PUBLIC_ORIGIN` + `AW_COOKIE_SECURE=auto`；提供 `scripts/backup.sh` 与恢复步骤。
- OQ-ARCH-03：由编排者决定按 B 处理——已派 aw-ux 回补 interaction-design 的登录页线框，不由 tech-design 越阶段出 UI。

## 2026-11-17 20:27:18

用户选择（OQ-ARCH-06~09 全部按建议默认 A）：

- OQ-ARCH-06 A：解析护栏 单库 ≤20,000 条 / 深度 ≤32 层 / 单条一跳邻居 ≤200，超限整包拒绝并报实测值。
- OQ-ARCH-07 A：检索用可移植 `LIKE`，不做 MySQL FULLTEXT / SQLite FTS5；接口与 digest 不变，后续可升级。
- OQ-ARCH-08 A：已被新版本取代的条目禁止注入（浏览只读仍可用）。**编排者核对：需求层 AC-014-4 已写明「已被新版本取代」在发起调用前阻止，AC-015-4 明确「条目已删除或已失效时按 AC-014-4 处理」，两者不冲突，按 AC-014-4 引用即可，不需要在 ADR 里写「与需求差异」。**
- OQ-ARCH-09 A：删除知识库 = 删除同项目同名逻辑库的全部版本与文件，名称可重新使用。

## 2026-11-18 10:44:10

用户原话：「全按建议」。

- OQ-TD-01 主键形态：自增整数 `int`。
- OQ-TD-02 删除：本期不提供项目/提供商/模型删除，只停用。
- OQ-TD-03 调用记录：冗余提供商名与模型名快照，历史不随改名变化。
- OQ-TD-04 制品磁盘文件名：uuid，原名只存库。
- OQ-TD-05 网关错误映射：上游 5xx → 502，超时 → 504。

## 2026-11-18 11:23:27

用户原话：「A101 A、A102 A、A103 B」（跨 spec 扩展，由编排者转达）。

- **A101 A**：`ai_call_record` 追加 `knowledge_injection`（JSON NULL）、`injected_chars`、`prompt_chars`、`total_chars`；`session_event.type` 的 CHECK 增加 `knowledge_injection`；core 的调用记录与时间线序列化暴露 `knowledgeInjection` 与 `kbDeleted`（按 `kbId` 左连接 `knowledge_base`，该表由 knowledge-base spec 建）。
- **A102 A**：`AiGateway.complete(...)` 追加 keyword-only 可选参数 `injection: InjectionSnapshot | None = None`，缺省行为与现状完全一致；插入 `running` 记录时同事务写上述列并追加 `knowledge_injection` 事件。
- **A103 B**：不新增 `/knowledge-injection/calls` 端点；扩展 core 的 `POST /api/v1/sessions/{sessionId}/ai/complete` 请求体，接受知识库引用（`knowledgeRefs`、`confirmInvalidCodes`），由 core 在调用前调用 knowledge-base 的进程内服务做失效重校验、组装与字符预算。
- **迁移顺序**：core 新增 revision `0006`（现有 head `0005`）；knowledge-base 的表迁移从 `0007` 起。
- **状态说明**：tech-design 已于 2026-11-18 10:47:44 确认；本次为确认后的跨 spec additive 变更，`technical-design/` 相关文档标注「2026-11-18 因跨 spec 扩展变更，待用户重新确认」，不视为已确认。

## 2026-11-18 11:02:41

用户原话：「TT-01 A 建 GitHub 公开仓库并 push 走 Actions，配置好 .gitignore ，其他按建议」

- OQ-TT-01 CI 平台：**A = GitHub Actions**。需要建 GitHub 公开仓库并 push，同时配置好 `.gitignore`。
- OQ-TT-02 端点口径：30（以 api-spec.md 端点总览表为准，1–30 连续，29 为误计）。
- OQ-TT-03 前端测试：单测（vitest）进 CI 必过门禁；E2E（Playwright）不进必过门禁。
- OQ-TT-04 备份恢复：本期交付 `scripts/backup.sh` + 手工演练记录，不做自动恢复演练。

## 2026-11-18 依赖版本核实记录（实现侧反馈，非用户决策）

实现侧两次报错版本：先报 FastAPI 0.162.5，再报「SQLAlchemy 2.1 不可用」；均已由编排者运行时核实更正。

- **最终版本**：FastAPI **0.163.2**（`fastapi.__version__` 与 `uv.lock` 一致，pyproject 约束 `>=0.162,<0.164`）、SQLAlchemy **2.1.9**（`pyproject.toml` 为 `sqlalchemy>=2.1.9,<2.2`）、pydantic-settings **2.16.3**。
- **验证**：`uv lock`/`uv sync` 实装 2.1.9；`pytest` 36 passed；`alembic upgrade head` 在 SQLite 上 0001→0006 全过；`aw.py verify` 36 通过 / 0 失败；生产代码零改动。
- **结论**：本次没有任何降级；记录见 `docs/architecture-decisions.md` ADR-043。
