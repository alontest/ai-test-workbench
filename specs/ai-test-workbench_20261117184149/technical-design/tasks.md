# Tech Tasks — workbench-core

> 阶段：tech-tasks。来源：`requirements.md`（AC-TECH）、`change-spec.md`、`docs/database-schema.md`、`docs/api-spec.md`、`docs/component-tree.md`、`docs/architecture-decisions.md`、`interaction-design/docs/context.md`。
> 依据：`approvals.md` 末行 `tech-design · 2026-11-18 10:47:44 · 确认`；OQ-TD-01 ~ 05 全按 A（`answers.md` 2026-11-18 10:44:10「全按建议」）。
> 本体：`specs/ai-test-workbench_20261117184149/ontology-slices/tech-tasks.md` 不存在（项目无 `ontology-work/views/index.json`），任务不附 `ENT-` / `BR-` 编号；实体名沿用 `_shared/domain-map.md`（Session / SessionEvent / Artifact / AiCallRecord / ProjectContext / ProviderConfig / ModelBinding）。
> 本文件是 aw-implementer 的唯一任务来源；复选框行不得改写。

## 任务分组

### 批次 A：基座、数据层与冻结契约（TASK-TD-001 ~ TASK-TD-018）

目标：从空仓库建立可运行骨架、双方言迁移、统一错误体、文件存储与四个冻结签名，并用契约测试锁住签名。完成后不依赖任何业务页面即可被后续 spec 引用。

- 可并行：001 →（002/003/004/005/006 并行）→ 007 → 008 → 009 → 010；011/012/013 可在 007 后并行；014/015/016 依赖 008、009、012；017 依赖 016；018 依赖 001 与 010。
- 出口条件：`pytest` 全绿；`alembic upgrade head` 在 SQLite 通过；冻结签名测试（TC-057）通过。
- 批次 A 完成后应用可启动（无业务端点），但还不满足「最小闭环」验收。

### 批次 B：最小闭环（TASK-TD-019 ~ TASK-TD-041）

目标：跑通「登录 → 建项目 → 配提供商/模型 → 建会话 → 贴文本 → 发起调用」，包含上传与时间线。批次结束即可独立验收（AC-TECH-4）。

- 依赖：批次 A 全部完成；019/020 → 021；022/023 → 024；025/026 → 027 → 028/029；030/031 → 033/034；035/036 → 037/038；039/040；041 依赖 019 ~ 040 的接口与用例。
- 出口条件：TC-001 ~ TC-050、TC-062 全绿（SQLite 默认；MySQL 由 CI job 2 复跑）；`python3 .aw/aw.py verify` 可识别全部 TC。

### 批次 C：调用查询、六入口与交付（TASK-TD-042 ~ TASK-TD-050）

目标：补齐 US-001/US-002/US-010 的界面与查询、启动归并验证、部署与备份交付。

- 依赖：批次 B 完成；042 → 043；044 → 045；046 依赖 030/031；047 依赖 013/016；048 ~ 050 依赖 018 与 042 ~ 047。
- 出口条件：TC-046 ~ TC-048、TC-031、TC-051 ~ TC-056 全绿；compose 启动与备份脚本按 `docs/dev-setup.md` 手工验收通过（[no-test] 项）。
- 批次 C 不阻塞批次 B 的独立验收。

## 任务清单

- [ ] TASK-TD-001：配置后端依赖与工具链 [no-test]
  - **描述**：在 `pyproject.toml` 写入后端运行与测试依赖，删除占位 `dependencies = []`；锁定版本并生成 `uv.lock`。
  - **涉及文件**：`pyproject.toml`、`uv.lock`、`.env.example`
  - **具体操作**：requires-python `>=3.12`；依赖 fastapi 0.163.x、uvicorn 0.54.x、pydantic 2.14.x、pydantic-settings 2.16.x、SQLAlchemy 2.1.x、alembic 1.20.x、aiosqlite 0.22.x、asyncmy 0.2.18、argon2-cffi 25.1.x、cryptography 50.x、openai 3.52.x、anthropic 2.9.x、python-multipart 0.0.34；dev 依赖 pytest、pytest-asyncio、httpx、testcontainers（可选）；pytest `testpaths=["tests"]`、`pythonpath=["src"]`、`asyncio_mode="auto"`；`.env.example` 列出 `AW_ADMIN_PASSWORD`、`AW_ENCRYPTION_KEY`、`AW_DATABASE_URL`、`AW_DATA_DIR`、`AW_PUBLIC_ORIGIN`、`AW_COOKIE_SECURE`、`AW_TRUST_PROXY`、`AW_ALLOW_REMOTE`、`AW_AI_MAX_CONCURRENCY`、`AW_PROMPT_MAX_CHARS`（值写占位，不写真实密钥）。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：无
  - **对应 AC**：AC-TECH-1
  - **TC**：无（由 TASK-TD-002 ~ TASK-TD-050 的导入与用例间接验证；见免测理由）
  - **估算**：3h [样板]，不确定性低
  - **状态**：pending
  - 免测理由：纯依赖清单与工具配置，无运行时行为；`.aw/config.json` 的 pytest 命令保持不变。

- [ ] TASK-TD-002：实现配置模块与启动期环境校验
  - **描述**：用 pydantic-settings 集中声明 `AW_*` 变量与默认值，提供 `Settings` 单例与校验错误信息。
  - **涉及文件**：`src/workbench/config.py`、`tests/test_config.py`
  - **具体操作**：`AW_ENCRYPTION_KEY` 必须为 32 字节 base64；`AW_ADMIN_PASSWORD` 非空；`AW_DATABASE_URL` 未设置时回退 `sqlite+aiosqlite:///<AW_DATA_DIR>/workbench.db`；`AW_DATA_DIR` 默认 `./data`；`AW_COOKIE_SECURE` ∈ auto/true/false；`AW_AI_MAX_CONCURRENCY` 默认 4；`AW_PROMPT_MAX_CHARS` 默认 200000。缺失/非法时抛可读错误（由启动自检转成非 0 退出）。用例 `test_tc009_missing_admin_password_refuses_start`、`test_tc057_frozen_settings_contract`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-001
  - **对应 AC**：AC-011-2、AC-TECH-1
  - **TC**：TC-009、TC-057
  - **估算**：6h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-003：定义全局常量与 6 入口配置
  - **描述**：集中阈值常量，并用代码常量定义 6 个入口（唯一来源，驱动 planned/live）。
  - **涉及文件**：`src/workbench/core/constants.py`、`src/workbench/core/entrances.py`、`tests/test_entrances.py`
  - **具体操作**：常量含 200000 字符、10MB、10 个、120s、10s、8h、5 次/5 分钟、预览 262144 字节、同名改名上限 100；入口 key 固定为 `case-library` / `bug-analysis` / `log-triage` / `sql-analysis` / `regression-list` / `test-report`，各含 name、description、domain、status；本期全部 `planned`。用例 `test_tc051_entrances_has_six_items`、`test_tc056_entrance_status_is_config_driven`。
  - **优先级**：P0
  - **复杂度**：XS（<4h）
  - **依赖**：TASK-TD-001
  - **对应 AC**：AC-001-1、AC-002-3
  - **TC**：TC-051、TC-056
  - **估算**：3h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-004：实现 AES-256-GCM 加解密与密钥掩码
  - **描述**：密文格式 `v1:<nonce_b64>:<ciphertext_b64>`；提供 `encrypt` / `decrypt` / `mask_secret`，解密失败抛统一异常。
  - **涉及文件**：`src/workbench/core/crypto.py`、`tests/test_crypto.py`
  - **具体操作**：每次加密随机 12 字节 nonce；`decrypt` 校验版本前缀、base64 与 GCM tag，失败抛 `CredentialUnavailable`（不含密文）；`mask_secret("sk-abcdef1234")` → `sk-****1234`；用例覆盖往返、篡改、格式错误、错误密钥、掩码边界。用例 `test_tc017_crypto_roundtrip_and_tamper`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-002
  - **对应 AC**：AC-003-1
  - **TC**：TC-017
  - **估算**：5h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-005：实现管理员口令哈希与校验
  - **描述**：用 argon2-cffi 默认 RFC 9106 低内存参数封装 `hash_password` / `verify_password`。
  - **涉及文件**：`src/workbench/core/password.py`、`tests/test_password.py`
  - **具体操作**：只通过 `PasswordHasher.verify` 比较，不手写字符串比较；hash 编码串整体存储；用例覆盖正确/错误口令、非法编码串返回 False。用例 `test_tc002_password_verify_contract`。
  - **优先级**：P0
  - **复杂度**：XS（<4h）
  - **依赖**：TASK-TD-001
  - **对应 AC**：AC-011-2
  - **TC**：TC-002
  - **估算**：3h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-006：实现日志脱敏过滤器
  - **描述**：统一过滤 Authorization、`sk-` 密钥、Cookie、口令字段，提供 `redact(text)` 与 logging Filter。
  - **涉及文件**：`src/workbench/core/redaction.py`、`tests/test_redaction.py`
  - **具体操作**：对 `Authorization`、`Cookie`、`apiKey`、`password`、`token` 键值替换为 `[REDACTED]`；截断超长文本；用例断言 JSON 日志、异常消息、AiCallRecord 预览均无原文。用例 `test_tc063_logs_and_responses_never_contain_secrets`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-001
  - **对应 AC**：AC-003-1、AC-011-3、AC-TECH-6
  - **TC**：TC-063
  - **估算**：4h [逻辑]，不确定性中（需覆盖 SDK 异常文本）
  - **状态**：pending

- [ ] TASK-TD-007：搭建 SQLAlchemy Base 与双方言引擎
  - **描述**：声明 Declarative Base、naming_convention、类型助手；按 URL 选择 SQLite/MySQL 引擎与连接池。
  - **涉及文件**：`src/workbench/db/base.py`、`src/workbench/db/engine.py`、`tests/test_engine.py`
  - **具体操作**：SQLite 用 `NullPool` + WAL + `busy_timeout=5000`，测试内存库可用 `StaticPool`；MySQL 用 `AsyncAdaptedQueuePool`（pool_size=5、max_overflow=5、pool_recycle=1800、pool_pre_ping=True、pool_timeout=10）与 `isolation_level="READ COMMITTED"`；类型助手含 `pk_type()`（BigInteger + sqlite Integer 变体）、`medium_text()`。用例 `test_tc058_engine_creation_both_dialects`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-002
  - **对应 AC**：AC-TECH-2
  - **TC**：TC-058
  - **估算**：5h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-008：实现 10 张表的 ORM 模型
  - **描述**：按 `database-schema.md` 逐表建模块，含字段、CHECK、唯一、索引、外键与级联。
  - **涉及文件**：`src/workbench/db/models/{admin_credential,login_session,login_attempt,project_context,provider_config,model_binding,analysis_session,session_event,artifact,ai_call_record}.py`、`src/workbench/db/models/__init__.py`
  - **具体操作**：主键用 `pk_type()`；时间 `DateTime`；`payload` 用 `sa.JSON`；长短文本用 `medium_text()`；唯一键落 `*_key` 且列级 `utf8mb4_bin`；枚举列全部 `CheckConstraint`；`analysis_session` 删除级联 event/artifact/call，其余外键 `RESTRICT`；`__table_args__` 写 InnoDB/utf8mb4 参数。用例 `test_tc058_models_match_schema_metadata`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-007
  - **对应 AC**：AC-TECH-2
  - **TC**：TC-058
  - **估算**：12h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-009：建立 Alembic 单一迁移树与 5 个初始 revision
  - **描述**：`alembic.ini` + `migrations/env.py`（双方言、batch 模式、compare_type）+ `0001_auth` ~ `0005_ai_call_record`。
  - **涉及文件**：`alembic.ini`、`migrations/env.py`、`migrations/script.py.mako`、`migrations/versions/0001_auth.py`、`0002_project_provider_model.py`、`0003_session_event.py`、`0004_artifact.py`、`0005_ai_call_record.py`
  - **具体操作**：一个 revision 只做一类表；SQLite `render_as_batch=True`；每个 revision 提供 `downgrade()`；不在迁移中写业务数据；命名约定与 ORM 一致。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-008
  - **对应 AC**：AC-TECH-2
  - **TC**：TC-058、TC-059
  - **估算**：10h [逻辑]，不确定性中（MySQL DDL 细节）
  - **状态**：pending

- [ ] TASK-TD-010：编写迁移与双方言约束测试
  - **描述**：从空库升级到 head；`AW_TEST_DATABASE_URL` 存在时同一用例在 MySQL 复跑。
  - **涉及文件**：`tests/test_db_migrations.py`
  - **具体操作**：断言 `alembic_version == head`；断言 10 张表存在；验证唯一（项目名大小写、模型名、文件名）、CHECK（status/entrance/protocol）、级联删除、`RESTRICT`；MySQL 下补验 `utf8mb4_bin` 行为；用例 `test_tc058_migrate_empty_db_to_head`、`test_tc059_constraints_on_test_database`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-009
  - **对应 AC**：AC-TECH-2
  - **TC**：TC-058、TC-059
  - **估算**：6h [集成]，不确定性中（本地无 MySQL 时跳过并标注）
  - **状态**：pending

- [ ] TASK-TD-011：搭建 FastAPI 应用骨架与统一错误/分页
  - **描述**：`create_app()`、路由注册、静态托管、异常处理器、`requestId`、游标编解码、Origin 校验依赖。
  - **涉及文件**：`src/workbench/main.py`、`src/workbench/api/errors.py`、`src/workbench/api/deps.py`、`src/workbench/api/v1/router.py`、`src/workbench/api/pagination.py`、`tests/test_api_skeleton.py`
  - **具体操作**：错误体 `{code,message,details[],requestId}`；`ApiError` 映射表；请求体校验失败 400 `validation_error` 逐字段；`limit` 1–100（事件 1–200）；base64url 游标编码/解码；非安全方法校验 Origin/Referer 命中 `AW_PUBLIC_ORIGIN`，否则 403 `forbidden_origin`；SPA fallback 到 `index.html`。用例 `test_tc060_error_envelope_and_cursor`、`test_tc061_origin_check_rejects_cross_site`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-002、TASK-TD-007
  - **对应 AC**：AC-TECH-3
  - **TC**：TC-060、TC-061
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-012：实现制品文件存储适配器
  - **描述**：临时文件写入、原子移动、包含校验、trash、孤儿扫描。
  - **涉及文件**：`src/workbench/adapters/fs/storage.py`、`tests/test_storage.py`
  - **具体操作**：`artifact_dir(session_id)`；`safe_artifact_path` resolve 后 `is_relative_to(session_dir)` 且链上无符号链接，否则抛 not found；`move_to_trash` 用 `os.replace`；`scan_orphans(max_age)` 清理 `.tmp` / `.trash`；存储名 `<uuid4hex>.<ext>`；用例覆盖 `../../x`、`..%2F`、符号链接、改名与清理。用例 `test_tc039_path_traversal_rejected`、`test_tc040_storage_cleanup_on_failure`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-003
  - **对应 AC**：AC-007-1、AC-007-2
  - **TC**：TC-039、TC-040
  - **估算**：8h [逻辑]，不确定性中（跨平台路径行为）
  - **状态**：pending

- [ ] TASK-TD-013：实现启动自检与后台清理
  - **描述**：按 ADR-020 顺序 fail-fast；提供 `merge_running_calls()` 与清理任务入口。
  - **涉及文件**：`src/workbench/startup.py`、`tests/test_startup.py`
  - **具体操作**：顺序：加密口令 → 管理员口令 → 连接串 → 数据库连通（30s 退避）→ `alembic_version == head` → 凭据转存/轮换 → 归并 `running` → 清理过期登录会话与失败计数；任一步失败非 0 退出；清理每小时一次且失败只记日志；归并逻辑在应用层算 `latency_ms`，同事务更新记录、追加 `call` 事件、刷新会话 `updated_at`。用例 `test_tc049_startup_merges_running_calls`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-009、TASK-TD-014
  - **对应 AC**：AC-TECH-1、AC-005-1
  - **TC**：TC-049
  - **估算**：8h [逻辑]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-014：落地冻结签名 `sessions.create` / `sessions.append_event`
  - **描述**：按 `change-spec.md` §3.1 实现 TypedDict、`DomainError`、创建前置校验与事件写入。
  - **涉及文件**：`src/workbench/services/sessions.py`、`src/workbench/services/errors.py`、`src/workbench/db/repositories/sessions.py`、`src/workbench/db/repositories/events.py`、`tests/test_sessions_service.py`
  - **具体操作**：`create(*, project_id, entrance_key, title, model_id) -> SessionView`；校验项目存在、模型启用、提供商启用、入口合法、标题 1–200；失败抛 `project_not_found` / `model_not_found` / `model_disabled` / `provider_disabled` / `validation_error` 且不写行；`append_event(session_id, event_type, payload, *, actor="local-user")` 要求会话 `in_progress`，同事务写事件并刷新 `updated_at`；payload 按类型校验必需键。用例 `test_tc057_frozen_session_signatures`、`test_tc026_create_session_contract`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-008、TASK-TD-009
  - **对应 AC**：AC-009-1、AC-006-1、AC-TECH-1
  - **TC**：TC-057、TC-026
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-015：落地冻结签名 `artifacts.save`
  - **描述**：按 `change-spec.md` §3.2 实现上传校验、落盘、同名改名、行与事件同事务。
  - **涉及文件**：`src/workbench/services/artifacts.py`、`src/workbench/db/repositories/artifacts.py`、`tests/test_artifacts_service.py`
  - **具体操作**：`save(session_id, *, file_name, source, claimed_content_type=None, kind="upload") -> ArtifactView`；白名单扩展名与 ≤10MB（generated 同限）；流式写 `.tmp/<uuid>`；同名 `stem-N.ext`；原子移动到 `sessions/<session_id>/<uuid4hex>.<ext>`；插入行 + `append_event`；任一步失败清理临时/已移动文件且不留 DB 行；mime 由扩展名映射。用例 `test_tc057_frozen_artifact_signature`、`test_tc036_save_upload_success`、`test_tc038_duplicate_name_renamed`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-008、TASK-TD-012、TASK-TD-014
  - **对应 AC**：AC-007-1、AC-007-3、AC-TECH-1
  - **TC**：TC-057、TC-036、TC-038
  - **估算**：10h [逻辑]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-016：落地冻结签名 `AiGateway.complete` 与适配器协议
  - **描述**：实现 `AIResult`、`ProtocolAdapter` 协议、假适配器、并发信号量、记录生命周期与超时/重试。
  - **涉及文件**：`src/workbench/services/ai_gateway.py`、`src/workbench/adapters/ai/base.py`、`src/workbench/adapters/ai/fake.py`（测试用）、`tests/test_ai_gateway.py`
  - **具体操作**：`complete(session_id, model_id, prepared, *, temperature=None, max_tokens=None)`；prepared 1–200000；前置校验在写记录前；获取信号量后插入 `running`；每次尝试 `asyncio.timeout(120)`；仅网络错误与 5xx 重试 1 次（退避 2s）；终结 `success/failed/timeout` 并写 `latency_ms/retry_count/error_code/result_text`；同事务追加 `call` 事件；失败抛 `AIError(code,message,call_id,retry_count)`；取消时 `finally` 终结为 `failed(interrupted)`。用例 `test_tc057_frozen_gateway_signature`、`test_tc041_success_records_call`、`test_tc042_upstream_failure_recorded`、`test_tc045_retry_then_timeout`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-008、TASK-TD-009、TASK-TD-014
  - **对应 AC**：AC-005-1、AC-005-2、AC-005-5、AC-TECH-1
  - **TC**：TC-057、TC-041、TC-042、TC-045
  - **估算**：14h [逻辑]，不确定性中（超时/取消时序）
  - **状态**：pending

- [ ] TASK-TD-017：实现 OpenAI 兼容与 Anthropic 协议适配器
  - **描述**：用官方 SDK 发起非流式请求，把 SDK 异常映射为统一错误码。
  - **涉及文件**：`src/workbench/adapters/ai/openai_compatible.py`、`src/workbench/adapters/ai/anthropic.py`、`tests/test_ai_adapters.py`
  - **具体操作**：OpenAI 兼容用 `base_url` + `api_key`；Anthropic 用官方 messages API；统一返回文本与错误分类 `auth|rate_limit|server_error|timeout|unreachable|invalid_request`；不记录请求头与密钥；SDK `max_retries=0`（重试由网关控制）。用例用 httpx mock/假客户端覆盖 401/429/500/网络错误/超时。用例 `test_tc019_connection_test_timeout`、`test_tc021_connection_test_error_classification`、`test_tc042_adapter_error_mapping`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-016
  - **对应 AC**：AC-003-3、AC-005-2
  - **TC**：TC-019、TC-021、TC-042
  - **估算**：12h [集成]，不确定性中（厂商差异，RISK-002）
  - **状态**：pending

- [ ] TASK-TD-018：新增 CI 的 pytest 与 MySQL 两个 job [no-test]
  - **描述**：新增 CI 流水线，job 1 在 SQLite 上跑 `pytest`，job 2 起 MySQL 8.4 service 并以 `AW_TEST_DATABASE_URL` 跑同一套用例。
  - **涉及文件**：`.github/workflows/ci.yml`（平台待 OQ-TT-01 确认，默认 GitHub Actions）
  - **具体操作**：job 1：安装 uv、Python 3.12、`uv sync --frozen`、`python3 .aw/aw.py verify`（或等价 pytest）；job 2：`services.mysql` 镜像 `mysql:8.4`、健康检查、`AW_TEST_DATABASE_URL=mysql+asyncmy://.../workbench_test?charset=utf8mb4`、先 `alembic upgrade head` 再 pytest；两个 job 都上传测试报告；不缓存测试结果。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-001、TASK-TD-010
  - **对应 AC**：AC-TECH-2
  - **TC**：TC-058、TC-059（由 CI 运行时执行同一批用例）
  - **估算**：4h [样板]，不确定性中（平台未定）
  - **状态**：pending
  - 免测理由：CI 配置本身不产生 pytest 用例；其有效性由流水线实际运行结果验收，本地 `aw verify` 不覆盖。

- [ ] TASK-TD-019：实现认证服务（登录、令牌、锁定、登出）
  - **描述**：实现 `login` / `authenticate` / `logout` / `current_source_ip` 与 `login_attempt` 行锁计数。
  - **涉及文件**：`src/workbench/services/auth.py`、`src/workbench/db/repositories/auth.py`、`tests/test_auth_service.py`
  - **具体操作**：`login(password, source_ip)`：锁定期直接 429；Argon2 校验；成功删 `login_attempt` 行、写 `login_session`（只存 SHA-256 哈希）、返回 token 与 idle 过期时间；失败同事务自增，窗口 5 分钟，达 5 次写 `locked_until=now+5min`；`authenticate(token)` 查哈希、`revoked_at IS NULL`、`now-last_seen_at <= 8h`，命中刷新 `last_seen_at`；`logout` 写 `revoked_at`。用例 `test_tc001_unauthorized_without_session`、`test_tc002_login_issues_token_hash_only`、`test_tc003_wrong_password_uniform_error`、`test_tc004_lock_after_five_failures`、`test_tc005_concurrent_failures_counted`、`test_tc006_idle_expiry_and_refresh`、`test_tc007_logout_revokes_token`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-009、TASK-TD-013
  - **对应 AC**：AC-011-1 ~ AC-011-7
  - **TC**：TC-001 ~ TC-007
  - **估算**：14h [逻辑]，不确定性中（并发计数）
  - **状态**：pending

- [ ] TASK-TD-020：实现认证 API、路由级鉴权与 Cookie 属性
  - **描述**：3 个认证端点、`require_session` 依赖、HTML 导航 302、Cookie 设置、Origin 校验接入。
  - **涉及文件**：`src/workbench/api/v1/auth.py`、`src/workbench/api/deps.py`、`src/workbench/api/schemas/auth.py`、`tests/test_auth_api.py`
  - **具体操作**：`POST /auth/login` 白名单；`POST /auth/logout` 204 并清 Cookie；`GET /auth/session` 返回 `authenticated/lastSeenAt/idleExpiresAt`；Cookie `aw_session` HttpOnly、SameSite=Lax、Path=/、`AW_COOKIE_SECURE` 决定 Secure；未认证 API 401 统一体、HTML 导航 302 `/login?next=`（只接受站内路径）；401 不返回业务字段。用例 `test_tc001_api_401_and_html_redirect`、`test_tc008_cookie_attributes`、`test_tc010_login_next_is_internal_only`、`test_tc011_expired_session_redirects`、`test_tc012_next_rejects_external_url`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-011、TASK-TD-019
  - **对应 AC**：AC-011-1、AC-011-2、AC-011-5、AC-011-6、AC-011-7、AC-TECH-3
  - **TC**：TC-001、TC-002、TC-007、TC-008、TC-010、TC-011、TC-012、TC-061
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-021：搭建前端 SPA 脚手架、Design Tokens 与通用原子组件
  - **描述**：Vite + React + TS + Router + TanStack Query；tokens.css 映射 design-system；AuthGate、LoginPage、AppShell 与基础 UI 组件。
  - **涉及文件**：`web/package.json`、`web/vite.config.ts`、`web/tsconfig.json`、`web/index.html`、`web/src/main.tsx`、`web/src/router.tsx`、`web/src/app/{AppShell,AuthGate,Providers}.tsx`、`web/src/styles/tokens.css`、`web/src/components/ui/{Button,Input,Select,Switch,Badge,Loading,Tooltip,FormField,ConfirmDialog,Feedback}.tsx`、`web/src/features/auth/{LoginPage,PasswordField,AuthBanner,useLogin,useLogout}.tsx`、`web/src/lib/api/{client,errors,keys}.ts`
  - **具体操作**：tokens.css 只声明变量，不新增/改名；API 客户端 `credentials:'same-origin'`，401 统一跳登录；AuthGate 启动调 `/auth/session`，未认证带 `next`；LoginPage 状态 default/submitting/error/locked/expired/logged-out，锁定 `mm:ss` 倒计时；AppShell 侧边栏 248px、顶栏 64px、≤768px 抽屉。前端行为由批次 B 冒烟与人工/Playwright 验证；TC 复用服务端用例，不单独产生 pytest 用例。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-020
  - **对应 AC**：AC-011-1 ~ AC-011-7、AC-001-1
  - **TC**：TC-001、TC-008、TC-010（服务端断言；UI 状态人工验收）
  - **估算**：14h [样板]，不确定性中（TS 7 / Vite 8 生态，RISK-007）
  - **状态**：pending

- [ ] TASK-TD-022：实现项目服务与仓储
  - **描述**：项目创建、编辑、详情、列表；名称唯一（casefold）与 `updated_at` 维护。
  - **涉及文件**：`src/workbench/services/projects.py`、`src/workbench/db/repositories/projects.py`、`tests/test_projects_service.py`
  - **具体操作**：`create` 去首尾空白、`name_key=casefold()`、冲突抛 `project_name_duplicate`；`update` 支持部分字段与显式 null 清空，刷新 `updated_at`；列表按 `updated_at DESC, project_id DESC` 游标分页。用例 `test_tc013_create_project_and_duplicate`、`test_tc014_update_reflects_and_touches`、`test_tc016_name_validation`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-009
  - **对应 AC**：AC-008-1、AC-008-2
  - **TC**：TC-013、TC-014、TC-016
  - **估算**：6h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-023：实现项目 API（4 个端点）
  - **描述**：`GET/POST /projects`、`GET/PATCH /projects/{id}`，逐字段校验与错误映射。
  - **涉及文件**：`src/workbench/api/v1/projects.py`、`src/workbench/api/schemas/project.py`、`tests/test_projects_api.py`
  - **具体操作**：`name` 1–100；`repoUrl` http(s) 绝对地址且无 userinfo；409 冲突带 `details[].field`；404 `project_not_found`；不提供 DELETE。用例覆盖 200/201/400/404/409。用例 `test_tc013_api_create_and_conflict`、`test_tc014_api_patch`、`test_tc015_session_requires_project`、`test_tc016_api_validation_fields`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-011、TASK-TD-022
  - **对应 AC**：AC-008-1、AC-008-2、AC-008-3
  - **TC**：TC-013、TC-014、TC-015、TC-016
  - **估算**：6h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-024：实现项目页面与表单
  - **描述**：项目列表、新建/编辑对话框、重名与校验错误定位。
  - **涉及文件**：`web/src/features/projects/{ProjectsPage,ProjectList,ProjectForm,ProjectDialog}.tsx`
  - **具体操作**：三态 loading/empty/error；`FormField` 按 `details[].field` 标错；保存后失效 `['projects']`；不出现删除按钮（OQ-TD-02 A）。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-021、TASK-TD-023
  - **对应 AC**：AC-008-1、AC-008-2
  - **TC**：TC-013、TC-014、TC-016（服务端断言；UI 人工验收）
  - **估算**：8h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-025：实现提供商服务（加密、掩码、连接测试）
  - **描述**：创建/编辑/启停、密钥加密与掩码、凭据解析、10s 连接测试。
  - **涉及文件**：`src/workbench/services/providers.py`、`src/workbench/db/repositories/providers.py`、`tests/test_providers_service.py`
  - **具体操作**：`apiKey` 加密为 `v1:...`；响应只给 `apiKeyMasked`；`update` 空密钥不改；`resolve_credentials` 解密失败抛 `provider_credential_unavailable`；连接测试用独立 10s 超时，不写会话/制品/记录，返回 `{ok,latencyMs,modelCount,errorCode}`；停用提供商不级改模型行。用例 `test_tc017_provider_key_encrypted_and_masked`、`test_tc018_provider_validation`、`test_tc019_connection_test_timeout`、`test_tc020_disabled_provider_blocks_models`、`test_tc021_connection_test_error_codes`、`test_tc022_update_key_blank_keeps`、`test_tc050_credential_decrypt_failure_no_record`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-004、TASK-TD-017、TASK-TD-009
  - **对应 AC**：AC-003-1 ~ AC-003-4、AC-005-2
  - **TC**：TC-017 ~ TC-022、TC-050
  - **估算**：14h [逻辑]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-026：实现提供商 API（5 个端点）
  - **描述**：列表、创建、编辑/启停、已保存与未保存两种连接测试。
  - **涉及文件**：`src/workbench/api/v1/providers.py`、`src/workbench/api/schemas/provider.py`、`tests/test_providers_api.py`
  - **具体操作**：任何响应不含 `apiKey`/密文；`PATCH` 缺省 apiKey 不改；连接测试上游失败仍 200；参数校验逐字段。用例 `test_tc017_api_never_returns_secret`、`test_tc018_api_validation`、`test_tc019_api_connection_test`、`test_tc021_api_connection_test_failure`、`test_tc022_api_patch_key`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-011、TASK-TD-025
  - **对应 AC**：AC-003-1 ~ AC-003-3
  - **TC**：TC-017 ~ TC-022
  - **估算**：8h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-027：实现模型服务与 API（4 个端点）
  - **描述**：模型登记、编辑/启停、提供商内列表、跨提供商列表（含启用过滤）。
  - **涉及文件**：`src/workbench/services/models.py`、`src/workbench/db/repositories/models.py`、`src/workbench/api/v1/models.py`、`src/workbench/api/schemas/model.py`、`tests/test_models.py`
  - **具体操作**：`model_name_key=casefold()`，同提供商重名 409；temperature 0–2、max_tokens 1–1,000,000；`enabled=true` 查询同时要求提供商启用；`modelName` 不可改。用例 `test_tc023_create_model_and_ranges`、`test_tc024_duplicate_model_name`、`test_tc025_default_params_used_and_override_not_persisted`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-025
  - **对应 AC**：AC-004-1 ~ AC-004-3
  - **TC**：TC-023、TC-024、TC-025
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-028：实现提供商页面与表单
  - **描述**：列表、新建/编辑对话框、SecretField、ConnectionTestBadge 七态。
  - **涉及文件**：`web/src/features/providers/{ProvidersPage,ProviderTable,ProviderDialog,ProviderForm,SecretField,ConnectionTestBadge}.tsx`
  - **具体操作**：掩码展示；编辑留空不改；表单变更后测试结果回到 idle；停用开关乐观更新；错误按字段定位；协议只给两个选项。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-021、TASK-TD-026
  - **对应 AC**：AC-003-1 ~ AC-003-4
  - **TC**：TC-017、TC-018、TC-021（服务端断言；UI 人工验收）
  - **估算**：12h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-029：实现模型页面与表单
  - **描述**：提供商下模型列表、新增/编辑、启停与参数校验。
  - **涉及文件**：`web/src/features/models/{ModelsPage,ModelTable,ModelDialog,ModelForm}.tsx`
  - **具体操作**：显示名与模型名分离；temperature 步进与范围提示；重名提示 `model_name_duplicate`；停用后从可选列表消失。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-021、TASK-TD-027
  - **对应 AC**：AC-004-1 ~ AC-004-3
  - **TC**：TC-023、TC-024（服务端断言；UI 人工验收）
  - **估算**：8h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-030：实现会话服务（完成、失败、列表、详情、删除）
  - **描述**：在冻结 `create/append_event` 之上补状态流转、查询与级联删除。
  - **涉及文件**：`src/workbench/services/sessions.py`、`src/workbench/db/repositories/sessions.py`、`tests/test_sessions_service.py`
  - **具体操作**：`complete` 写 `status_change(local-user)`、置 `closed_at`；`fail_session` 写 `system`；终态拒绝事件/调用；`list` 支持 projectId/status 与游标；`delete_session` 先 `move_to_trash`，再单事务删行，失败回滚文件；`model_id` 创建后不可改。用例 `test_tc026_create_session`、`test_tc027_list_filters`、`test_tc028_timeline_order`、`test_tc029_terminal_state_rejects`、`test_tc030_delete_cascades`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-014、TASK-TD-012
  - **对应 AC**：AC-009-1 ~ AC-009-5
  - **TC**：TC-026 ~ TC-030
  - **估算**：10h [逻辑]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-031：实现会话 API（6 个端点）
  - **描述**：列表、创建、详情、完成、删除、事件列表。
  - **涉及文件**：`src/workbench/api/v1/sessions.py`、`src/workbench/api/schemas/session.py`、`tests/test_sessions_api.py`
  - **具体操作**：`GET /sessions` 支持 projectId/status/limit/cursor，首页用 `limit=10`；创建失败映射 404/409/400；完成重复调用 409；删除 204；事件默认 50 最大 200 升序；会话对象含项目与模型摘要。用例 `test_tc026_api_create_session`、`test_tc027_api_filters`、`test_tc028_api_events_order`、`test_tc029_api_complete_idempotent`、`test_tc030_api_delete`、`test_tc031_recent_sessions_limit10`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-011、TASK-TD-030
  - **对应 AC**：AC-009-1 ~ AC-009-5、AC-001-3
  - **TC**：TC-026 ~ TC-031
  - **估算**：10h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-032：接入 500 未捕获异常的会话失败标记
  - **描述**：会话作用域端点出现未捕获异常时 best-effort 调用 `fail_session`。
  - **涉及文件**：`src/workbench/api/errors.py`、`tests/test_fail_session_hook.py`
  - **具体操作**：异常处理器识别会话作用域与 `session_id`；DB 不可用则跳过并记日志；业务错误 400/404/409/502/504 不改状态；写 `status_change(actor=system, reason="unhandled error")`。用例 `test_tc029_unhandled_error_marks_failed`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-030
  - **对应 AC**：AC-009-4
  - **TC**：TC-029
  - **估算**：4h [逻辑]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-033：实现会话列表、筛选与新建对话框
  - **描述**：`/sessions` 页面、项目/状态筛选、创建会话（项目与启用模型为硬前置）。
  - **涉及文件**：`web/src/features/sessions/{SessionsPage,SessionFilters,SessionTable,CreateSessionDialog,SessionHeader,StatusPill}.tsx`
  - **具体操作**：缺项目/缺模型禁用创建并给配置引导；创建后失效 `['sessions']` 与 `['sessions', id]`；状态徽标带文字；列表区分 empty 与 filtered-empty。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-021、TASK-TD-031、TASK-TD-024
  - **对应 AC**：AC-009-1、AC-009-2、AC-009-4、AC-008-3
  - **TC**：TC-026、TC-027、TC-029（服务端断言；UI 人工验收）
  - **估算**：14h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-034：实现会话详情与时间线
  - **描述**：`/sessions/:id` 头部、四类事件卡、只读态、滚动/分页加载。
  - **涉及文件**：`web/src/features/sessions/{SessionDetailPage,SessionTimeline,TimelineEvent,InputEventCard,CallEventCard,ArtifactEventCard,StatusChangeEvent}.tsx`
  - **具体操作**：事件升序；输入卡折叠/展开全文；调用卡显示模型/耗时/状态/摘要与失败重试次数；制品卡显示文件名/大小/预览；终态只读；`useInfiniteQuery` 用 `nextCursor`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-033、TASK-TD-035、TASK-TD-036、TASK-TD-039
  - **对应 AC**：AC-009-3、AC-005-4
  - **TC**：TC-028、TC-044（服务端断言；UI 人工验收）
  - **估算**：14h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-035：实现文本输入接口
  - **描述**：`POST /sessions/{id}/inputs/text`，追加 `input_text` 事件。
  - **涉及文件**：`src/workbench/api/v1/sessions.py`、`src/workbench/api/schemas/input.py`、`tests/test_inputs_api.py`
  - **具体操作**：标题 1–200；正文去空白后非空（`text_empty`）；`len(text) <= 200000`（`text_too_long`，details 含 charCount/maxChars）；终态 409；201 返回事件并刷新会话。用例 `test_tc032_append_text_event`、`test_tc033_empty_text_rejected`、`test_tc034_text_over_limit_rejected`、`test_tc035_updated_at_bumped`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-031
  - **对应 AC**：AC-006-1 ~ AC-006-3
  - **TC**：TC-032 ~ TC-035
  - **估算**：6h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-036：实现制品上传、元数据与内容接口
  - **描述**：`POST /sessions/{id}/artifacts`、`GET /artifacts/{id}`、`GET /artifacts/{id}/content`。
  - **涉及文件**：`src/workbench/api/v1/artifacts.py`、`src/workbench/api/schemas/artifact.py`、`tests/test_artifacts_api.py`
  - **具体操作**：multipart 重复 `files`，1–10 个；整批校验（类型/大小/数量）后逐个 `artifacts.save`；响应含 items 与 events；元数据不含路径；content 支持 inline/download、`max_bytes` 默认/上限 262144；Content-Type 服务端映射、`nosniff`、RFC 5987 文件名；行在文件缺 410。用例 `test_tc036_upload_success_and_preview`、`test_tc037_batch_validation_rejects_all`、`test_tc038_duplicate_names_renamed`、`test_tc039_traversal_rejected_via_api`、`test_tc040_disk_failure_returns_507`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-015、TASK-TD-031
  - **对应 AC**：AC-007-1 ~ AC-007-3
  - **TC**：TC-036 ~ TC-040
  - **估算**：14h [逻辑]，不确定性中（磁盘故障注入）
  - **状态**：pending

- [ ] TASK-TD-037：实现文本输入面板与字数计数
  - **描述**：会话详情右栏 TextComposer，实时计数、超限禁用。
  - **涉及文件**：`web/src/features/composer/{TextComposer,CharacterCounter}.tsx`
  - **具体操作**：上限常量从模块导出（200000）；>90% 警告色、超限危险色且禁用提交；空正文就地错误；成功后清空并失效事件 query。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-034、TASK-TD-035
  - **对应 AC**：AC-006-1 ~ AC-006-3
  - **TC**：TC-032、TC-033、TC-034（服务端断言；UI 人工验收）
  - **估算**：8h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-038：实现文件上传与制品卡
  - **描述**：拖拽/选择上传，前端三查，逐文件标红，同名改名前提示。
  - **涉及文件**：`web/src/features/composer/{FileUploader}.tsx`、`web/src/features/composer/ArtifactCard.tsx`
  - **具体操作**：白名单/10MB/10 个；前端拒绝不阻止用户移除后重提；预览按纯文本转义，禁止 `dangerouslySetInnerHTML`；下载用 content `mode=download`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-034、TASK-TD-036
  - **对应 AC**：AC-007-1 ~ AC-007-3
  - **TC**：TC-036、TC-038（服务端断言；UI 人工验收）
  - **估算**：10h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-039：实现发起调用接口
  - **描述**：`POST /sessions/{id}/calls`，调用 `AiGateway.complete` 并映射错误。
  - **涉及文件**：`src/workbench/api/v1/calls.py`、`src/workbench/api/schemas/call.py`、`tests/test_calls_api.py`
  - **具体操作**：prompt 1–200000（`prompt_too_long`）；temperature/maxTokens 可选；前置拒绝 404/409 且无记录；成功 200 返回 callId/resultText/latencyMs/retryCount/模型摘要；失败 502 `ai_*`、504 `ai_timeout`、502 `provider_credential_unavailable`，details 含 callId/retryCount。用例 `test_tc041_api_call_success`、`test_tc042_api_call_failure`、`test_tc043_precondition_rejections_no_record`、`test_tc044_call_event_payload`、`test_tc045_api_retry_and_timeout`、`test_tc050_api_credential_unavailable`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-016、TASK-TD-025、TASK-TD-031
  - **对应 AC**：AC-005-1 ~ AC-005-5
  - **TC**：TC-041 ~ TC-045、TC-050
  - **估算**：10h [逻辑]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-040：实现调用面板与本次参数覆盖
  - **描述**：会话详情 CallPanel：提示输入、字数、高级参数、调用中禁用、失败展示。
  - **涉及文件**：`web/src/features/calls/{CallPanel,AdvancedParams}.tsx`
  - **具体操作**：提示与文本共用 200000 上限；本次 temperature/max_tokens 不写回模型；前端超时 300s；成功后失效时间线与调用记录；失败保留面板内容并展示错误码。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-034、TASK-TD-039
  - **对应 AC**：AC-005-1、AC-005-4、AC-004-3
  - **TC**：TC-025、TC-041、TC-044（服务端断言；UI 人工验收）
  - **估算**：12h [样板]，不确定性中（长请求体验）
  - **状态**：pending

- [ ] TASK-TD-041：编写批次 B 最小闭环冒烟测试
  - **描述**：用 httpx ASGITransport 串起登录 → 建项目 → 提供商/模型 → 会话 → 贴文本 → 调用，断言各步返回与记录。
  - **涉及文件**：`tests/test_batch_b_smoke.py`
  - **具体操作**：假 AI 适配器返回固定文本；断言 Cookie 建立、201/200、时间线含 input_text 与 call、`ai_call_record` 一行成功、会话 `updated_at` 变化；不依赖浏览器与外部网络。用例 `test_tc062_batch_b_minimal_loop`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-019 ~ TASK-040
  - **对应 AC**：AC-TECH-4
  - **TC**：TC-062
  - **估算**：6h [集成]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-042：实现调用记录查询 API
  - **描述**：`GET /calls` 与 `GET /calls/{callId}`，支持会话/项目/状态/时间筛选。
  - **涉及文件**：`src/workbench/services/calls.py`、`src/workbench/db/repositories/calls.py`、`src/workbench/api/v1/calls.py`、`src/workbench/api/schemas/call.py`、`tests/test_calls_query.py`
  - **具体操作**：排序 `created_at DESC, call_id DESC`；游标 `(created_at, call_id)`；列表不返回 resultText；详情返回；空结果 `items: []`；错误与摘要不含密钥。用例 `test_tc046_query_calls_ordering`、`test_tc047_failed_call_detail`、`test_tc048_empty_result_not_error`。
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-039
  - **对应 AC**：AC-010-1 ~ AC-010-3
  - **TC**：TC-046、TC-047、TC-048
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-043：实现调用记录页面
  - **描述**：`/calls` 筛选（项目→会话级联、状态、默认近 7 天）、表格与行展开核对。
  - **涉及文件**：`web/src/features/calls/{CallsPage,CallFilters,CallRecordTable,CallRecordRow}.tsx`
  - **具体操作**：空态与 filtered-empty 区分；失败行展开显示错误与重试次数；成功行展开显示结果全文；不展示密钥。
  - **优先级**：P1
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-042、TASK-TD-033
  - **对应 AC**：AC-010-1 ~ AC-010-3
  - **TC**：TC-046、TC-047、TC-048（服务端断言；UI 人工验收）
  - **估算**：12h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-044：实现入口配置 API、首页与入口卡片
  - **描述**：`GET /entrances`；首页 6 卡片与最近 10 条会话；点击进入对应路径。
  - **涉及文件**：`src/workbench/api/v1/entrances.py`、`web/src/features/entrances/{HomePage,EntranceGrid,EntranceCard,RecentSessionTable}.tsx`
  - **具体操作**：配置来自 `core/entrances.py`；卡片含名称、用途、所属域、planned/live；整卡链接；最近会话复用 `GET /sessions?limit=10`，空态；未知 key 返回 `entrance_unknown`；SPA 刷新直达由后端 fallback 保证。用例 `test_tc051_api_entrances_six`、`test_tc052_spa_fallback_entrance_route`、`test_tc053_unknown_entrance_rejected`、`test_tc031_home_recent_sessions`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-021、TASK-TD-031
  - **对应 AC**：AC-001-1 ~ AC-001-3
  - **TC**：TC-051、TC-052、TC-053、TC-031
  - **估算**：12h [样板]，不确定性中（SPA fallback 与鉴权顺序）
  - **状态**：pending

- [ ] TASK-TD-045：实现入口占位页
  - **描述**：`/entrances/:key` 按配置渲染占位或 live 挂载点，占位页说明所属域与状态并可返回首页。
  - **涉及文件**：`web/src/features/entrances/{EntrancePage,PlaceholderPanel}.tsx`
  - **具体操作**：planned 不创建会话、不调用模型、不产生记录；live 预留域功能挂载点；配置缺失显示错误态；状态由 `GET /entrances` 驱动，改配置即可切换。用例 `test_tc054_placeholder_metadata`、`test_tc055_placeholder_has_no_side_effects`、`test_tc056_entrance_status_switch`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-044
  - **对应 AC**：AC-002-1 ~ AC-002-3
  - **TC**：TC-054、TC-055、TC-056
  - **估算**：6h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-046：实现删除会话的前端确认流程
  - **描述**：会话头部与列表提供删除，ConfirmDialog 列出级联范围（事件、制品目录、调用记录）。
  - **涉及文件**：`web/src/features/sessions/SessionHeader.tsx`、`web/src/components/ui/ConfirmDialog.tsx`
  - **具体操作**：二次确认、确认中 loading、成功后回列表并失效 `['sessions']`/`['calls']`；失败展示 `session_delete_failed`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-033、TASK-TD-030
  - **对应 AC**：AC-009-5
  - **TC**：TC-030（服务端断言；UI 人工验收）
  - **估算**：4h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-TD-047：补充启动归并与调用取消的故障用例
  - **描述**：覆盖进程重启归并、取消终结、并发上限与排队不计 latency。
  - **涉及文件**：`tests/test_startup.py`、`tests/test_ai_gateway.py`
  - **具体操作**：插入 `running` 后重启 → `failed(interrupted)`、`finished_at`/`latency_ms` 非空、时间线有 call 事件、会话仍可输入；取消任务 → `failed(interrupted)`；信号量阻塞期间不产生记录。用例 `test_tc049_restart_merges_running`、`test_tc045_cancellation_finalizes_record`。
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-013、TASK-TD-016、TASK-TD-030
  - **对应 AC**：AC-005-1、AC-005-5
  - **TC**：TC-049、TC-045
  - **估算**：5h [集成]，不确定性中
  - **状态**：pending

- [ ] TASK-TD-048：交付部署工件（compose/Dockerfile/入口脚本） [no-test]
  - **描述**：app + mysql:8.4 的 compose、多阶段构建、迁移后启动、静态托管 `web/dist`。
  - **涉及文件**：`Dockerfile`、`docker-compose.yml`、`scripts/docker-entrypoint.sh`、`.dockerignore`
  - **具体操作**：Node 阶段构建 `web/dist`，Python 3.14-slim 运行且非 root；入口脚本 `alembic upgrade head` 后起 uvicorn；端口默认 `127.0.0.1:8000:8000`；`AW_ALLOW_REMOTE` 显式开启；db 健康检查；不把密钥写入镜像。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-TD-018、TASK-TD-041
  - **对应 AC**：AC-TECH-1
  - **TC**：无（容器构建与启动手工验收）
  - **估算**：10h [集成]，不确定性中
  - **状态**：pending
  - 免测理由：部署工件无法在 pytest 内验证；由 `docker compose up` 启动与健康检查手工验收，验收步骤写入 `docs/dev-setup.md`。

- [ ] TASK-TD-049：交付备份与恢复脚本 [no-test]
  - **描述**：`scripts/backup.sh` 执行 mysqldump + 制品目录打包，排除 `.trash/` 与 `.tmp/`，并写明恢复顺序。
  - **涉及文件**：`scripts/backup.sh`、`docs/dev-setup.md`（恢复步骤）
  - **具体操作**：`--single-transaction --routines --triggers`；制品 `tar`；输出文件含时间戳；恢复先库后制品；提示 `AW_ENCRYPTION_KEY` 需独立保管。
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-048
  - **对应 AC**：AC-TECH-6（RISK-015）
  - **TC**：无（恢复演练手工验收）
  - **估算**：4h [样板]，不确定性低
  - **状态**：pending
  - 免测理由：备份/恢复依赖真实 MySQL 与文件系统，pytest 内无法可信模拟；以一次恢复演练作为验收证据。

- [ ] TASK-TD-050：整理环境说明与上线验收清单 [no-test]
  - **描述**：补全 `docs/dev-setup.md`（本地与容器两路径、环境变量、迁移、测试、TLS 反代要求）与上线验收清单。
  - **涉及文件**：`docs/dev-setup.md`、`README.md`
  - **具体操作**：列出 uv/node 版本、`pytest`、`aw verify`、MySQL 用例、compose 启动、备份恢复、`AW_PUBLIC_ORIGIN`/`AW_COOKIE_SECURE`/`AW_TRUST_PROXY` 配置、TLS 反代要求；标注「SQLite 绿不等于双方言通过」。
  - **优先级**：P1
  - **复杂度**：XS（<4h）
  - **依赖**：TASK-TD-048、TASK-TD-049
  - **对应 AC**：AC-TECH-4
  - **TC**：无（文档）
  - **估算**：2h [样板]，不确定性低
  - **状态**：pending
  - 免测理由：纯文档整理，无运行时行为。

## TC ↔ AC 映射

> `aw.py verify` 从测试报告用例名中读取 `TC-NNN`。所有 TC 均由 pytest 用例断言（前端任务引用同一 TC，不额外产生 pytest 用例；UI 视觉/交互由人工或 Playwright 记录，不计入 TC 结果）。

| TC | AC | 主要任务 | 验证点 |
|----|----|---------|--------|
| TC-001 | AC-011-1 | 019/020/021 | 未登录 API 401、页面 302，无业务字段 |
| TC-002 | AC-011-2 | 005/019/020 | 正确口令登录、只存令牌哈希、响应无口令 |
| TC-003 | AC-011-3 | 019 | 错误口令统一提示、不签发、日志无原文 |
| TC-004 | AC-011-4 | 019 | 5 次失败锁 5 分钟、Retry-After、成功清零 |
| TC-005 | AC-011-4 | 019 | 并发失败计数不丢 |
| TC-006 | AC-011-5 | 019 | 空闲 8h 失效、请求刷新 lastSeenAt |
| TC-007 | AC-011-6 | 019/020 | 登出吊销，旧令牌 401 |
| TC-008 | AC-011-7 | 020/021 | Cookie HttpOnly/SameSite/Secure |
| TC-009 | AC-011-2 | 002 | `AW_ADMIN_PASSWORD` 缺失/空拒启 |
| TC-010 | AC-011-1 | 020/021 | HTML 导航 302 并保留站内 next |
| TC-011 | AC-011-5 | 020 | 过期后 API 401 与页面跳转 |
| TC-012 | AC-011-1 | 020 | next 只接受站内路径 |
| TC-013 | AC-008-1 | 022/023/024 | 创建项目、重名 409（大小写不敏感） |
| TC-014 | AC-008-2 | 022/023/024 | 编辑回显与 updatedAt |
| TC-015 | AC-008-3 | 023 | 无项目不可创建会话 |
| TC-016 | AC-008-1 | 022/023/024 | 名称空/超长逐字段 400 |
| TC-017 | AC-003-1 | 004/025/026/028 | 密文落库、掩码、响应无密钥 |
| TC-018 | AC-003-2 | 025/026/028 | 必填/baseUrl 非法拒绝且不写库 |
| TC-019 | AC-003-3 | 017/025/026 | 连接测试 10s 超时、无副作用 |
| TC-020 | AC-003-4 | 025 | 停用提供商后模型不可选、历史可查 |
| TC-021 | AC-003-3 | 017/025/026/028 | 连接测试失败分类 |
| TC-022 | AC-003-1 | 025/026 | 空密钥不改、新值重加密 |
| TC-023 | AC-004-1 | 027/029 | 新增模型与参数范围 |
| TC-024 | AC-004-2 | 027/029 | 同提供商同名 409 |
| TC-025 | AC-004-3 | 027/040 | 默认参数生效、覆盖不回写 |
| TC-026 | AC-009-1 | 014/030/031/033 | 创建会话、进行中、置顶 |
| TC-027 | AC-009-2 | 030/031/033 | 项目/状态筛选与倒序 |
| TC-028 | AC-009-3 | 030/031/034 | 时间线按 event_id 升序 |
| TC-029 | AC-009-4 | 030/031/032/033 | 完成/失败终态拒绝写入 |
| TC-030 | AC-009-5 | 030/031/046 | 级联删除 DB 与文件、其他会话不受影响 |
| TC-031 | AC-001-3 | 031/044 | 最近 10 条会话与空态 |
| TC-032 | AC-006-1 | 035/037 | 提交文本追加 input_text 事件 |
| TC-033 | AC-006-2 | 035/037 | 空/纯空白正文拒绝 |
| TC-034 | AC-006-3 | 035/037 | 超 200,000 拒绝并给字数 |
| TC-035 | AC-006-1 | 035 | 追加后刷新会话 updated_at |
| TC-036 | AC-007-1 | 015/036/038 | 上传成功、事件、元数据与预览 |
| TC-037 | AC-007-2 | 036 | 白名单/10MB/10 个整批拒绝 |
| TC-038 | AC-007-3 | 015/036/038 | 同名自动改名保留两份 |
| TC-039 | AC-007-2 | 012/036 | 路径穿越/符号链接拒绝 |
| TC-040 | AC-007-1 | 012/036 | 磁盘失败 507、无残留与无 DB 行 |
| TC-041 | AC-005-1 | 016/039/040 | 成功调用返回文本+callId、写记录与事件 |
| TC-042 | AC-005-2 | 016/017/039 | 上游失败写记录并可读错误 |
| TC-043 | AC-005-3 | 039 | 前置拒绝不产生记录 |
| TC-044 | AC-005-4 | 034/039/040 | 时间线/详情展示摘要，无密钥 |
| TC-045 | AC-005-5 | 016/039/047 | 重试 1 次、超时不重试 |
| TC-046 | AC-010-1 | 042/043 | 按会话/项目/时间查询倒序 |
| TC-047 | AC-010-2 | 042/043 | 失败详情含错误与重试次数，无密钥 |
| TC-048 | AC-010-3 | 042/043 | 无匹配空列表 |
| TC-049 | AC-005-1 | 013/047 | 启动归并 running → failed(interrupted) |
| TC-050 | AC-005-2 | 025/039 | 凭据解密失败 502 且无记录 |
| TC-051 | AC-001-1 | 003/044 | 6 入口含名称与用途 |
| TC-052 | AC-001-2 | 044 | 入口路由 SPA 刷新直达 |
| TC-053 | AC-001-2 | 044 | 未知入口 key 拒绝 |
| TC-054 | AC-002-1 | 045 | 占位页数据含域名/状态/返回入口 |
| TC-055 | AC-002-2 | 045 | 占位页无会话/调用/记录副作用 |
| TC-056 | AC-002-3 | 003/045 | 入口 planned/live 由配置驱动 |
| TC-057 | AC-TECH-1 | 002/014/015/016 | 四个冻结签名契约 |
| TC-058 | AC-TECH-2 | 007/008/009/010/018 | SQLite 空库迁移到 head |
| TC-059 | AC-TECH-2 | 009/010/018 | MySQL 关键约束复验 |
| TC-060 | AC-TECH-3 | 011 | 错误体/requestId/游标分页 |
| TC-061 | AC-TECH-3 | 011/020 | Origin 校验 403 |
| TC-062 | AC-TECH-4 | 041 | 批次 B 最小闭环冒烟 |
| TC-063 | AC-TECH-6 | 006 | 日志/响应无密钥与口令 |

覆盖统计：42 条功能 AC 全覆盖（US-001 ~ US-011），6 条 AC-TECH 全覆盖；共 63 个 TC。

## Critical 风险对照

| 风险 | 对应用例 | 应急预案落点 |
|------|---------|-------------|
| RISK-001 密钥泄露 | TC-063、TC-017 | 响应 schema 无密钥；统一掩码；日志过滤器；发布前扫描日志与响应快照 |
| RISK-002 协议差异 | TC-019、TC-021、TC-042、TC-045 | 适配层错误映射固定；连接测试降级为鉴权可达性；差异不入 UI |
| RISK-005 上传穿越/伪装 | TC-037、TC-039、TC-040 | 服务端存储名；解析后包含校验；失败清理；必要时加文件头校验 |
| RISK-009 范围蔓延 | 范围表（`requirements.md` §1） | P1 项（调用记录界面、参数覆盖、筛选、备份脚本）可删减，P0 基座保留 |
| RISK-010 登录绕过/TLS | TC-001、TC-008、TC-010、TC-061 | 路由级鉴权；Cookie 属性；Origin 校验；文档要求 TLS 反代 |
| RISK-011 双方言漂移 | TC-058、TC-059 | CI 两个 job；禁止方言语法；只在一种方言通过视为缺陷 |
| RISK-012 口令/令牌泄露 | TC-003、TC-004、TC-005、TC-008 | Argon2 参数；令牌只存哈希；锁定；统一错误；脱敏 |

## 估点摘要

- 技术栈：Python 3.12+/FastAPI/SQLAlchemy 2.1/Alembic/MySQL 8.4+SQLite；React 19/TS/Vite/TanStack Query/Radix；pytest + httpx，MySQL 走 CI 第二 job。
- 任务总数：50（XS 3 / S 18 / M 29），无 L/XL。
- 批次工时：A 131h、B 228h、C 63h，合计 422h；按每日 4.8h 有效开发折算约 88 人日。
- 风险与前置：CI 平台待确认（OQ-TT-01）；MySQL 用例依赖 service 容器（本地缺 Docker 时跳过并在报告标注）；前端 UI 状态以人工/Playwright 验收，不计入 pytest TC；`RISK-007` 依赖锁定由 `uv.lock` / `package-lock.json` 保证。
- 批次验收：批次 A（pytest 全绿 + 迁移到 head）、批次 B（TC-001 ~ TC-050、TC-062）、批次 C（TC-046 ~ TC-048、TC-031、TC-051 ~ TC-056 + 手工验收项）。
