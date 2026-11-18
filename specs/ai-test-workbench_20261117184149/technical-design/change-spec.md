# Change Spec

> **文档状态：draft — 2026-11-18 因跨 spec 知识库注入扩展（A101 / A102 / A103 B）变更，待用户重新确认。** 变更前版本已于 2026-11-18 10:47:44 确认。

涉及本体：无（`specs/ai-test-workbench_20261117184149/ontology-slices/tech-design.md` 不存在，项目尚无 `ontology-work/views/index.json`；业务对象名沿用 `_shared/domain-map.md`，候选领域事件见 `_shared/ontology/domain-events.md`）

> 阶段：tech-design。范围：`workbench-core` 基座（US-001 ~ US-011，AC 42 条，EARS 17 条）。
> 上游架构：`technical-design/docs/architecture-decisions.md`（architecture-locked，2026-11-18 用户重新确认）。
> 数据模型：`docs/database-schema.md`；HTTP 契约：`docs/api-spec.md`；前端组件：`docs/component-tree.md`；流程与 ER：`docs/flowchart.md`。

## 1. 改动概览

仓库现为占位（`pyproject.toml` 无依赖、`src/workbench/__init__.py` 仅版本号、`tests/conftest.py` 为空），本 spec 从零落地后端、迁移、前端与测试骨架。**不复制知识库、仓库集成任何能力**（两者已迁出至各自 spec）。

## 2. 目录结构

```text
ai-test-workbench/
├── pyproject.toml                    # 依赖与 pytest 配置（tech-tasks 落版本）
├── alembic.ini
├── migrations/
│   ├── env.py                        # 双方言、batch 模式、naming_convention
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_auth.py
│       ├── 0002_project_provider_model.py
│       ├── 0003_session_event.py
│       ├── 0004_artifact.py
│       ├── 0005_ai_call_record.py
│       └── 0006_knowledge_injection.py   # core 迁移先于 knowledge-base 的 0007
├── src/workbench/
│   ├── __init__.py
│   ├── main.py                       # create_app()：路由、静态托管、异常处理、启动钩子
│   ├── config.py                     # pydantic-settings；AW_* 环境变量与启动校验
│   ├── startup.py                    # 启动自检顺序（ADR-020）与清理任务
│   ├── api/
│   │   ├── deps.py                   # require_session、origin 校验、分页参数
│   │   ├── errors.py                 # ApiError、异常处理器、requestId
│   │   ├── schemas/                  # auth/project/provider/model/session/artifact/call
│   │   └── v1/
│   │       ├── router.py
│   │       ├── auth.py
│   │       ├── entrances.py
│   │       ├── projects.py
│   │       ├── providers.py
│   │       ├── models.py
│   │       ├── sessions.py
│   │       ├── artifacts.py
│   │       └── calls.py
│   ├── services/
│   │   ├── auth.py                   # 登录、令牌、锁定、登出、会话刷新
│   │   ├── projects.py
│   │   ├── providers.py              # 加密存储、掩码、连接测试
│   │   ├── models.py
│   │   ├── sessions.py               # 冻结签名：create / append_event
│   │   ├── artifacts.py              # 冻结签名：save
│   │   ├── calls.py                  # 调用记录查询
│   │   └── ai_gateway.py             # 冻结签名：AiGateway.complete（唯一模型出口）
│   ├── adapters/
│   │   ├── ai/
│   │   │   ├── base.py               # ProtocolAdapter 抽象、AIResult、AIError
│   │   │   ├── openai_compatible.py
│   │   │   └── anthropic.py
│   │   └── fs/
│   │       └── storage.py            # 临时文件、原子移动、包含校验、trash、孤儿扫描
│   ├── core/
│   │   ├── crypto.py                 # AES-256-GCM、掩码、解密错误
│   │   ├── password.py               # Argon2id
│   │   ├── redaction.py              # 日志脱敏过滤器
│   │   ├── entrances.py              # 6 入口配置（唯一来源）
│   │   ├── constants.py              # 200000 字符、10MB、10 个、120s 等
│   │   └── ports.py                  # InjectionPreparer 协议与注册（A103 B）
│   └── db/
│       ├── base.py                   # Declarative Base、naming_convention、类型助手
│       ├── engine.py                 # 双方言引擎与连接池（ADR-018）
│       ├── models/                   # 每表一个模块（10 张表）
│       └── repositories/             # 查询封装（projects/providers/models/sessions/events/artifacts/calls/auth）
├── web/
│   ├── package.json / vite.config.ts / tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx / router.tsx
│       ├── app/                      # AppShell、AuthGate、Providers（TanStack Query）
│       ├── features/{auth,entrances,providers,models,projects,sessions,composer,calls}/
│       ├── components/ui/            # Radix 包装与通用反馈组件
│       ├── lib/api/                  # fetch 客户端、错误映射、query keys
│       └── styles/tokens.css         # interaction-design Design Tokens
├── tests/
│   ├── conftest.py                   # app/client/db/seeded fixtures、假 AI 适配器
│   ├── test_auth_*.py
│   ├── test_projects_*.py
│   ├── test_providers_*.py
│   ├── test_models_*.py
│   ├── test_sessions_*.py
│   ├── test_artifacts_*.py
│   ├── test_calls_*.py
│   ├── test_ai_gateway_*.py
│   ├── test_storage_*.py
│   ├── test_startup_*.py
│   └── test_db_migrations.py
└── scripts/
    ├── backup.sh
    └── docker-entrypoint.sh
```

- 前端构建产物 `web/dist` 由后端同源托管；`/login`、`/api` 之外的 GET 回落到 `index.html`（SPA 刷新直达，AC-001-2）。
- `.aw/config.json` 的 `test` 保持 pytest，`code_paths` 不变。

## 3. 进程内服务接口签名（ADR-041 冻结）

> 名称与语义冻结，新 spec 只调用、不修改。参数类型由本文件展开。新增可选关键字参数视为兼容扩展；改名、改位置参数、改返回语义都属于破坏性变更，必须走本 spec 变更。

### 3.1 会话与事件（`src/workbench/services/sessions.py`）

```python
from collections.abc import Mapping
from typing import Any, Literal

EntranceKey = Literal[
    "case-library", "bug-analysis", "log-triage",
    "sql-analysis", "regression-list", "test-report",
]
EventType = Literal["input_text", "artifact", "call", "status_change", "knowledge_injection"]
SessionStatus = Literal["in_progress", "completed", "failed"]

class SessionView(TypedDict):
    session_id: int
    project_id: int
    entrance_key: EntranceKey
    title: str
    status: SessionStatus
    model_id: int
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None

async def create(
    *,
    project_id: int,
    entrance_key: EntranceKey,
    title: str,
    model_id: int,
) -> SessionView: ...

async def append_event(
    session_id: int,
    event_type: EventType,
    payload: Mapping[str, Any],
    *,
    actor: str = "local-user",
) -> EventView: ...
```

- `create`：校验项目存在、模型与提供商启用、标题与入口合法；写 `analysis_session`（`in_progress`）。前置失败抛 `DomainError`（`project_not_found` / `model_not_found` / `model_disabled` / `provider_disabled` / `validation_error`），不写任何行。
- `append_event`：会话必须 `in_progress`（否则 `session_closed`）；同一事务写事件并刷新会话 `updated_at`；`payload` 按 `event_type` 校验必需键（见 `database-schema.md` §2.8）；返回 `EventView`（`event_id/session_id/type/payload/created_at`）。
- 业务域必须经此写事件，不直接写 `session_event` 表。
- 状态流转不在此签名内：用户标记完成走 `services.sessions.complete(session_id, *, actor="local-user")`（本 spec 内部接口，未冻结）；系统失败走 `fail_session(session_id, reason)`。

### 3.2 制品（`src/workbench/services/artifacts.py`）

```python
from typing import BinaryIO, Literal

class ArtifactView(TypedDict):
    artifact_id: int
    session_id: int
    kind: Literal["upload", "generated"]
    file_name: str
    mime_type: str
    byte_size: int
    created_at: datetime

async def save(
    session_id: int,
    *,
    file_name: str,
    source: BinaryIO,
    claimed_content_type: str | None = None,
    kind: Literal["upload", "generated"] = "upload",
) -> ArtifactView: ...
```

- `file_name` 只作展示名与扩展名判定，不参与路径拼接；`source` 由调用方保证可读，服务读取 ≤10MB（`kind="generated"` 同限）。
- 行为：校验白名单/大小 → 流式写 `AW_DATA_DIR/.tmp/<uuid>` → 同会话同名自动改名 → 原子移动到 `sessions/<sessionId>/<uuid4hex>.<ext>` → 插入 `artifact` 行 → 追加 `artifact` 事件（同一事务）。任一步失败清理临时与已移动文件，抛 `artifact_write_failed` / `file_type_not_allowed` / `file_too_large` / `session_closed`，不留下 DB 行。
- 返回前 `byte_size` 为实际落盘字节数；`mime_type` 由扩展名映射。

### 3.3 AI 网关（`src/workbench/services/ai_gateway.py`）

```python
@dataclass(frozen=True)
class InjectionItem:
    kb_id: int
    kb_name: str
    kb_version: int
    entry_codes: tuple[str, ...]
    injected_chars: int

@dataclass(frozen=True)
class InjectionSnapshot:
    items: tuple[InjectionItem, ...]
    prompt_chars: int
    injected_chars: int
    total_chars: int
    excluded_codes: tuple[str, ...] = ()

@dataclass(frozen=True)
class AIResult:
    call_id: int
    text: str
    status: Literal["success"]
    latency_ms: int
    retry_count: int
    model_id: int
    model_display_name: str
    knowledge_injection: tuple[InjectionItem, ...] | None = None

class AiGateway:
    async def complete(
        self,
        session_id: int,
        model_id: int,
        prepared: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        injection: InjectionSnapshot | None = None,
    ) -> AIResult: ...
```

- `prepared` 是调用方已组装好的完整提示正文（上下文拼装在业务域，本域不解释）；1–200,000 字符，超限抛 `prompt_too_long`，**不产生 AiCallRecord**。
- 前置校验（会话存在且 `in_progress`、模型存在且启用、提供商启用、凭据可解密）在写记录与外部请求之前；`session_not_found` / `session_closed` / `model_disabled` / `provider_disabled` / `provider_credential_unavailable` 均不产生记录。
- 参数合并：`temperature`/`max_tokens` 为 `None` 时取 `model_binding` 默认值；非 `None` 时只影响本次，不回写模型。
- 记录语义：获取并发信号量后插入 `running` → 调适配器（每次尝试 `asyncio.timeout(120)`；仅网络错误与 5xx 重试 1 次，退避 2s）→ 终结为 `success` / `failed` / `timeout`，写 `latency_ms`、`retry_count`、`error_code`、`result_text`（仅成功）→ 同一事务追加 `call` 事件并刷新会话 `updated_at`。
- 知识库注入（A102 / ADR-042）：`injection is None` 时行为、记录与事件与扩展前完全一致；非空时先校验 `injected_chars == sum(items.injected_chars)` 且 `total_chars == prompt_chars + injected_chars == len(prepared)`，不符抛 `injection_snapshot_mismatch`（不写记录）。插入 `running` 的同事务写 `knowledge_injection` / `injected_chars` / `prompt_chars` / `total_chars`，并追加 `session_event(type="knowledge_injection")`；后续失败/超时/中断不回滚这两处留痕。
- `AIResult.knowledge_injection` 回传快照供 HTTP 序列化；`prepared` 仍由调用方组装（core 的 `/ai/complete` 在带 `knowledgeRefs` 时调用 `InjectionPreparer` 组装，网关不解析知识库）。
- 失败抛 `AIError(code, message, call_id, retry_count)`；不返回空串冒充成功；不自动切模型（AC-005-2 / AC-005-5）。

### 3.4 其他内部接口（不冻结，供本 spec 的 API 层使用）

```python
# services/auth.py
async def login(password: str, source_ip: str) -> tuple[str, datetime]      # token, idle_expires_at
async def authenticate(token: str) -> LoginSessionView                       # 刷新 last_seen_at
async def logout(token: str) -> None
async def current_source_ip(request: Request) -> str                         # AW_TRUST_PROXY 语义

# services/providers.py
async def create_provider(data: ProviderCreate) -> ProviderView
async def update_provider(provider_id: int, data: ProviderUpdate) -> ProviderView
async def test_connection(*, protocol: str, base_url: str, api_key: str | None,
                          provider_id: int | None) -> ConnectionTestResult
async def resolve_credentials(provider_id: int) -> ResolvedCredentials         # 解密失败抛 provider_credential_unavailable

# services/sessions.py
async def complete(session_id: int, *, actor: str = "local-user") -> SessionView
async def fail_session(session_id: int, *, reason: str) -> SessionView
async def delete_session(session_id: int) -> None

# adapters/fs/storage.py
def artifact_dir(session_id: int) -> Path
def safe_artifact_path(session_id: int, relative_path: str) -> Path            # 包含校验 + 符号链接拒绝
def move_to_trash(session_id: int) -> Path | None
def scan_orphans(max_age: timedelta) -> int

# core/ports.py（A103 B：knowledge-base 实现并注册，core 只依赖协议）
@dataclass(frozen=True)
class KnowledgeRef:
    kb_id: int
    entry_codes: tuple[str, ...]

@dataclass(frozen=True)
class InvalidCodeRef:
    kb_id: int
    code: str

@dataclass(frozen=True)
class PreparedInjection:
    prepared: str
    snapshot: InjectionSnapshot

class InjectionPreparer(Protocol):
    async def prepare_for_call(
        self, *, session_id: int, project_id: int, prompt: str,
        knowledge_refs: Sequence[KnowledgeRef],
        confirm_invalid_codes: Sequence[InvalidCodeRef],
    ) -> PreparedInjection: ...          # 返回 prepared 文本 + InjectionSnapshot；失效/空集/超预算抛领域错误

def register_injection_preparer(impl: InjectionPreparer | None) -> None
def get_injection_preparer() -> InjectionPreparer | None
```

- `fail_session` 的触发：会话作用域端点出现**未捕获异常（500）**时，异常处理器 best-effort 调用 `fail_session(session_id, reason="unhandled error")`，写 `status_change(actor="system")`；数据库不可用则跳过并记日志。可预期的业务错误（400/404/409/502/504）不改变会话状态；启动归并 `running` 也不改变会话状态（会话仍可继续输入）。

## 4. 显式设计要求对照

| 要求 | 落点 |
|------|------|
| 并发 `running` 回收 | `startup.py` 启动归并用例 + `ai_gateway.py` 取消/异常 `finally` 终结 + `database-schema.md` §7.1/§7.2 |
| 超时与重试的记录语义 | `AiGateway.complete` 契约 + `ai_call_record.status/latency_ms/retry_count/error_code` + `api-spec.md` 调用端点错误映射 |
| 密钥解密失败 | `core/crypto.py`、`services/providers.resolve_credentials`、502 `provider_credential_unavailable`、不写 AiCallRecord（`database-schema.md` §7.3） |
| 磁盘写失败与半成品清理 | `adapters/fs/storage.py` 临时文件 + 原子移动 + 回滚；507 `artifact_write_failed`；启动孤儿扫描（§7.4 / §6） |
| 路径穿越防护 | `safe_artifact_path` 解析后包含校验 + 拒绝符号链接；存储名服务端生成（`database-schema.md` §7.4） |
| 登录限流 | `login_attempt` 行锁计数、5 次/5 分钟、成功清零、429 + `Retry-After`（ADR-025 / `database-schema.md` §2.3） |
| 知识库注入留痕与唯一入口 | `InjectionSnapshot`、`AiGateway.complete` 可选 `injection`、四列 + `knowledge_injection` 事件同事务、`/ai/complete` 的 `knowledgeRefs`/`confirmInvalidCodes`、`InjectionPreparer` 协议与 `kbDeleted` 序列化（ADR-042 / `database-schema.md` §7.5 / `api-spec.md` 调用端点） |

## 5. 改动文件

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `pyproject.toml` | 修改 | 写入后端依赖（fastapi/uvicorn/sqlalchemy/alembic/asyncmy/aiosqlite/argon2-cffi/cryptography/openai/anthropic/pydantic-settings/python-multipart）与 pytest 配置；删除占位 `dependencies = []` |
| `alembic.ini`、`migrations/env.py`、`migrations/versions/0001~0006` | 新增 | 双方言迁移树与 10 张表；`0006` 为知识库注入留痕列（先于 knowledge-base 的 `0007`） |
| `src/workbench/config.py`、`startup.py`、`main.py` | 新增 | 环境变量、启动自检、应用装配 |
| `src/workbench/core/*` | 新增 | 加密、口令、脱敏、入口配置、常量 |
| `src/workbench/db/*` | 新增 | Base、引擎、10 个 ORM 模型、仓储 |
| `src/workbench/services/*` | 新增 | 认证、项目、提供商、模型、会话、制品、调用查询、AI 网关 |
| `src/workbench/adapters/ai/*` | 新增 | 两类协议适配与领域错误映射 |
| `src/workbench/adapters/fs/storage.py` | 新增 | 落盘、改名、trash、包含校验、孤儿扫描 |
| `src/workbench/api/*` | 新增 | 29 个端点、依赖、错误处理、schema |
| `web/*` | 新增 | React SPA：登录、首页、入口、提供商、模型、项目、会话、制品、调用记录 |
| `tests/*` | 新增 | 见 §6；`tests/conftest.py` 由空文件改为 fixture 入口 |
| `scripts/docker-entrypoint.sh`、`scripts/backup.sh` | 新增 | 迁移后启动；备份与恢复（tech-tasks 产物，接口在 ADR-017/019 已定） |
| `docker-compose.yml`、`.env.example`、`Dockerfile` | 新增 | app + mysql:8.4；环境变量清单 |

> 组件级拆分见 `docs/component-tree.md`；端点清单见 `docs/api-spec.md`；表清单见 `docs/database-schema.md`。tech-tasks 再拆到可独立开发的任务粒度。

## 6. 测试策略

### 6.1 分层

| 层 | 工具 | 覆盖 |
|----|------|------|
| 单元 | pytest | `core.crypto`（加解密/篡改/格式）、`core.password`、脱敏过滤器、入口配置、游标编解码、`storage` 路径校验与改名 |
| 服务 | pytest + 内存/临时 SQLite | 各 service 的正常/前置失败/事务回滚；`AiGateway` 用假适配器注入成功/401/429/5xx/网络错误/超时/取消 |
| 接口 | httpx `ASGITransport` + FastAPI app | 每个端点的 200/400/401/403/404/409/429/502/504/507；Cookie 属性；401 无业务字段 |
| 方言 | pytest，`AW_TEST_DATABASE_URL` | `test_db_migrations.py` 从空库升级到 head；关键约束（唯一、CHECK、级联）在 MySQL 上复验 |
| 前端组件 | Vitest + Testing Library | 三态、表单校验、字数计数、掩码、锁定倒计时、只读态 |
| E2E（可选，P1） | Playwright | 登录 → 建项目 → 配提供商/模型 → 建会话 → 贴文本/上传 → 调用 → 标记完成 → 删除 |

### 6.2 必测故障路径（与 §4 对应）

- **running 回收**：插入 `running` 后重启 app → 断言记录变 `failed(interrupted)`、`finished_at`/`latency_ms` 非空、时间线新增 `call` 事件、会话仍可继续输入。
- **超时/重试记录**：假适配器先网络错误后成功 → `retry_count=1`、`status=success`；两次 5xx → `failed(server_error)`、`retry_count=1`；120s 无响应（用可注入的短超时参数 0.05s）→ `status=timeout`、`error_code=timeout`、不重试。
- **调用前置拒绝**：会话不存在/终态、模型停用、提供商停用 → 无 `ai_call_record` 行；解密失败 → 502 且无记录。
- **磁盘失败**：monkeypatch 临时文件写入抛 `OSError(ENOSPC)`、`os.replace` 抛错 → 507、会话目录无残留、无 DB 行、临时目录清空。
- **路径穿越**：`file_name="../../x"`、`storage_name="..%2F"`、符号链接指向目录外 → 404，且不访问目录外文件。
- **登录限流**：5 次失败 → 429 + `Retry-After`；锁定期正确口令仍 429；6 分钟后成功并清零；并发 2 请求同时失败计数不丢。
- **会话失效**：`last_seen_at` 拨回 8h+ → 401；请求后 `last_seen_at` 刷新；登出后旧 Cookie 401。
- **CSRF**：缺 Origin、错 Origin、跨站 POST → 403；同源 → 通过。
- **级联删除**：会话删除后事件/制品/调用记录 0 行、目录不存在；其他会话不受影响；trash 重命名失败时 DB 不动。
- **同名上传**：`app.log` 两次 → `app.log` + `app-1.log`，两文件都在。
- **注入兼容与留痕**：`injection=None` 时记录四列为 NULL/0 且不追加 `knowledge_injection` 事件；`injection` 非空时 `running` 同事务写四列并追加事件，调用失败仍保留；`total_chars != len(prepared)` → 400 且无记录。
- **失效确认与预算**：假 `InjectionPreparer` 返回失效集 → 未带/不等 `confirmInvalidCodes` 时 409 `knowledge_invalid_entries`（无上游请求、无 AiCallRecord）；精确匹配后成功；有效集为空 → 409 `knowledge_injection_empty`；超 200,000 → 400 `prompt_budget_exceeded`（含分段字数）。
- **kbDeleted 序列化**：快照 `kbId` 在 `knowledge_base` 有行 → false；行不存在或表不存在 → true；历史快照字段不被改写。
- **迁移顺序**：`0006` 在空库升级中先于 `0007`；core 测试只验证 `0006`，knowledge-base 测试从 `0007` 继续。

### 6.3 命名与门禁

- 用例名带 TC 编号：`test_tc012_upload_rejects_oversize`；与测试验证阶段的 TC 一一对应。
- `.aw/config.json` 的 `test` 不变；`python3 .aw/aw.py verify` 默认跑 SQLite；MySQL 由第二 job / `AW_TEST_DATABASE_URL` 覆盖。
- 不把「SQLite 绿」当作双方言通过；评审把「只在一种方言跑过」视为缺陷（RISK-011）。

## 7. 不改动的部分

- ADR-041 冻结的 `sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete(session_id, model_id, prepared, *, temperature, max_tokens)` 的名称、参数顺序与语义；本文件只展开类型。2026-11-18 按 A102 在 `complete` 末尾追加 keyword-only 可选参数 `injection=None`，缺省行为与扩展前完全一致（ADR-042）。
- core 不实现知识库导入、检索、失效判定与正文组装；`InjectionPreparer` 的具体实现由 knowledge-base spec 提供，core 只定义协议与错误映射。
- `projectId` 作为跨域主数据：其他域只引用 ID，不跨域查询项目表。
- `technical-design/docs/architecture-decisions.md` 全部决策原文（仅恢复文档状态为 architecture-locked）。
- 知识库与仓库集成：不新增其表、端点、组件或依赖；两者在各自 spec 中扩展本 spec 的加密、错误体、分页、认证与双方言约定。
- `.aw/`、`specs/ai-test-workbench_20261117184149/evidence/` 及上游阶段产物。
