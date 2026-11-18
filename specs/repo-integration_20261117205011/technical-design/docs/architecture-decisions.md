# Architecture Decisions Record (ADR) — repo-integration

> 编号从 ADR-201 起，避免与 workbench-core 的 ADR-001 ~ ADR-042、knowledge-base 的 ADR-101 ~ ADR-118 冲突。
> 本文件是 tech-arch 阶段的架构决策；`design.md` 是同一套决策的设计说明。每条 ADR 注明依据（AC / AMB / 上游事实），未核实的外部事实不给数值、不据此推断。
> 状态：**architecture-locked**（tech-arch 产出即锁定架构决策；阶段整体确认由编排者在 `approvals.md` 记录，用户确认前视为待复核）。

## 锁定时间

2026-11-18 11:40（tech-arch 产出；上游 requirements-analysis 与 interaction-design 已由用户确认，见 `approvals.md` 2026-11-18 10:47:44 / 11:23:18）。

## 项目扫描摘要

| 层次 | 检测结果 | 置信度 |
|------|---------|--------|
| 仓库现状 | 占位骨架：`pyproject.toml`（无运行依赖）、`src/workbench/__init__.py`、`tests/conftest.py`；无后端/前端代码、无迁移 | 高 |
| 后端 | 继承 core 的 architecture-locked 选型：Python 3.12+ / FastAPI / Pydantic 2 / SQLAlchemy 2.1 / Alembic / 单进程 Uvicorn | 高（来自 `specs/ai-test-workbench_20261117184149`） |
| 前端 | 继承 core：React 19 + TypeScript + Vite + React Router + TanStack Query + CSS 变量/CSS Modules + Radix Primitives；`dist` 由后端同源托管 | 高（同上） |
| 数据库 | MySQL 8.4 LTS（生产）+ SQLite（开发/测试），同一套 ORM 模型与迁移，双方言纪律 | 高（同上） |
| 部署 | docker-compose（app + mysql:8.4），支持外接 MySQL；默认绑定 `127.0.0.1` | 高（同上） |
| 仓库集成模块 | 尚无任何代码与迁移；本 spec 新建四张表、15 个 `/api/v1` 端点、2 个前端入口（项目上下文页区块 + 独立浏览路由） | — |
| 上游接口事实 | GitHub REST 与云效 Codeup 的鉴权、端点、分页头已联网核实；云效限流数值、单文件上限、GitHub PAT 过期头等仍未核实（见 `design.md`「未核实外部事实与处理口径」） | 高（已核实部分）/ 未知（未核实部分） |
| AlonWorkflow packs | `.aw/install.json` 的 `packs` 为空，未安装任何 pack，未套用 pack 专属约定 | 高 |
| 本体切片 | 无 `ontology-slices/tech-arch.md`（项目尚无 `ontology-work/views/index.json`）；使用 `_shared/ontology/` 的 ENT-C12 ~ ENT-C15、BR-C21 ~ BR-C27、BP-C9 ~ BP-C11 | 高 |

## 已确认决策

### ADR-201：技术栈完整继承 workbench-core，不重新选型

- **决策**：后端 Python 3.12+ / FastAPI / Pydantic 2 / SQLAlchemy 2.1 / Alembic / 单进程 Uvicorn；前端 React 19 + TS + Vite + React Router + TanStack Query + CSS 变量/CSS Modules + Radix Primitives；MySQL 8.4 生产 + SQLite 开发/测试。仓库集成作为同一进程内的垂直模块，不引入新的运行时、数据库、消息队列或前端框架。
- **来源**：继承 core（core ADR-001 / 002 / 003 / 015 / 016 / 017 / 027 / 041）
- **状态**：✅ 已锁定
- **理由**：上游已锁定「栈与 core 一致」；复用 core 的登录态、错误体、分页、凭证加密与 AppShell 是本需求的前置条件（AC-REQ-25、AC-REQ-34）。独立服务或独立前端包会把进程内契约退化成 HTTP，并引入第二套认证与部署面。
- **影响**：依赖版本以 core 的 `pyproject.toml` / `uv.lock` / `package-lock.json` 为唯一真源；本 spec 只追加模块代码、四张表与迁移 `0008`。
- **取代**：无

### ADR-202：模块边界——进程内垂直模块，只经冻结接口与 core 交互

- **决策**：后端落在 `src/workbench/repos/`（校验、加密、适配器）与 `src/workbench/services/repos/`（绑定、测试、同步、浏览、文件、生命周期服务），API 落在 `src/workbench/api/v1/repos*`；前端落在 `frontend/src/repos/`。对 core 的依赖只允许：①`require_session` 认证前置；②错误体 `{code,message,details[],requestId}` 与 `limit`+`cursor` 分页；③只读 `project_context` / `projectId`；④引用 `AW_PROMPT_MAX_CHARS=200000`（只在 core 定义，不重复定义）；⑤前端复用 AppShell/Design Tokens/`ConnectionTestBadge`。不新建 HTTP 客户端、不复刻认证、不直接读写 core 的会话、制品、`AiCallRecord`。
- **来源**：新增（依据 core ADR-041、requirements `系统集成点`、user 20:50:31 拆 spec 决策）
- **状态**：✅ 已锁定
- **理由**：单用户、单进程部署，进程内调用零网络失败面；core 已冻结认证、错误与分页契约定（AC-REQ-25、AC-REQ-34）。跨域只读接口以 `repoBindingId` 为唯一引用键，不暴露令牌、不允许其他域直连供应商。
- **影响**：与 core 同一发布单元；其他业务域只能调用跨域只读契约（`GET /baseline`、`GET /file`），不得持有令牌或调用同步/测试等会改变绑定状态的入口。
- **取代**：无

### ADR-203：数据模型与双方言映射（ENT-C12 ~ ENT-C15，迁移 `0008`）

- **决策**：新增四张表：
  - `repo_binding`：`binding_id CHAR(32)` PK、`project_id` FK → `project_context` `ON DELETE RESTRICT`、`provider`（`yunxiao` / `github`）、`api_base_url`、`org_id`、`owner`、`repo_id`、`repo_name`、`repo_key`（归一化唯一键）、`display_name`、`default_branch`、`token_ciphertext`（可空，解绑后清空）、`token_masked`、`token_expires_at`、`status`（`unverified` / `connected` / `token_invalid` / `revoked`）、`active_flag CHAR(1) NULL`、`last_verified_at`、`last_verify_result`、`last_verify_message`、`last_sync_attempt_at`、`last_sync_status`、`last_sync_success_at`、`last_sync_duration_ms`、`last_sync_error_category`、`last_sync_error_message`、`last_sync_retry_after`、`sync_started_at`、`revoked_at`、`created_at`、`updated_at`。
  - `repo_sync_record`：`sync_id CHAR(32)` PK、`binding_id` FK → `repo_binding` `ON DELETE CASCADE`、`started_at` / `finished_at`、`status`（`running` / `success` / `failed`）、`duration_ms`、`repo_count`、`branch_count`、`commit_count`、`error_category`（`auth` / `network` / `rate_limit` / `permission` / `other` / `interrupted`，可空）、`error_message`（已脱敏）、`retry_after_at`、`created_at`。
  - `repo_metadata_snapshot`：`snapshot_id CHAR(32)` PK、`binding_id` FK `ON DELETE CASCADE`、`repo_id`、`kind`（`repo` / `branch` / `commit`；`tree` 保留为合法值但按 AMB-026 从不写入）、`ref`、`payload JSON`（名称、ID、sha、标题、作者、时间、路径、文件大小）、`fetched_at`、`truncated BOOLEAN`。
  - `repo_file_read_record`：`read_id CHAR(32)` PK、`binding_id` FK `ON DELETE CASCADE`、`repo_id`、`ref`、`file_path`、`byte_size`、`encoding`（`text` / `base64`）、`status`（`success` / `refused`）、`reject_reason`（`too_large` / `binary` / `not_utf8`，可空）、`fetched_at`；**不存正文**。
  - 约束与索引：`UNIQUE(project_id, provider, repo_key, active_flag)`（在绑 `active_flag='1'`、解绑 `NULL`，两方言都允许多个 NULL，从而支持重新绑定生成新行，AC-017-3 / AC-023-6）；`(project_id, status)`、`(binding_id, started_at)`、`(binding_id, kind, fetched_at)`、`(binding_id, fetched_at)`。
  - 可移植写法：大文本用 `Text().with_variant(MEDIUMTEXT(), "mysql")`；JSON 用 `sa.JSON` 且不建索引；唯一性靠应用层写入 `repo_key`，不依赖 collation；SQLite 连接统一 `PRAGMA foreign_keys=ON`；时间统一 UTC，输出 RFC 3339。
- **来源**：新增（重构自 `_shared/ontology/entities.md` ENT-C12 ~ ENT-C15）
- **状态**：✅ 已锁定
- **理由**：AC-017-1/3/4/6、AC-019-1/3/4/6、AC-022-4/5、AC-023-4/5/6 要求绑定、同步记录、基线快照与读取审计可分别检索；AMB-022/023/026 要求解绑保留快照、同步只存基线、提交保留 100 条。可空唯一键解决「解绑后保留历史行又不能占用唯一键」的冲突（RISK-213）。
- **影响**：迁移编号顺延——core `0006_knowledge_injection` → knowledge-base `0007` → 本 spec `0008_repo_integration`（`down_revision = 0007`），同一线性历史；`repo_binding` 的 `kind` 不含目录树写入，目录树只在实时浏览时存在于响应与内存。**head 核对说明**：当前仓库仍是占位骨架（无 `migrations/versions/`），无法从代码核对 head；head 以 core 与 knowledge-base 已锁定文档为准（core `0006`、knowledge-base `0007`），代码落地后必须复核 `alembic heads` 再把 `0008` 接上。
- **取代**：无

### ADR-204：令牌加密——AES-256-GCM + 独立密钥 `AW_REPO_TOKEN_KEY`

- **决策**：仓库令牌沿用 core 的 AES-256-GCM 与 `v1:<nonce_b64>:<ciphertext_b64>` 密文格式、掩码口径（`<prefix>****<last4>`，短令牌 `****`），但使用**独立密钥**环境变量 `AW_REPO_TOKEN_KEY`（32 字节 base64），与 core 的模型密钥 `AW_ENCRYPTION_KEY` 并存、不共用、不互相派生。启动时缺失、base64 非法或长度不足 32 字节即拒绝启动；不做自动轮换或代续期（AMB-021）。更新令牌只替换 `token_ciphertext` / `token_masked` / `updated_at`，bindingId、已同步元数据与历史记录不变（AC-017-4）；解绑清空密文与掩码（AC-023-4）。
- **来源**：新增接线（算法沿用 core ADR-005；密钥独立依据 AMB-029 / requirements answers 2026-11-18 10:44:10）
- **状态**：✅ 已锁定
- **理由**：AC-017-1 / AC-REQ-25 要求密文存储与掩码回显；AMB-029 明确独立密钥，便于单独轮换而不牵连模型密钥。两密钥并存且各自启动校验，保持与 core 相同的失败策略（ADR-216）。
- **影响**：密钥丢失不可恢复，必须重填全部仓库令牌；密钥轮换需要用户重填，不做密文迁移；备份必须与数据库分开保管。接口、日志、同步/读取记录与 AiCallRecord 永不出现完整令牌。
- **取代**：无

### ADR-205：供应商适配器契约——五类能力、六个方法、归一化 DTO

- **决策**：定义 `RepoProvider` 协议（async），五类能力：`repository`（列表 + 详情）、`branches`、`commits`、`tree`、`file`；六个方法：`list_repositories`、`get_repository`、`list_branches`、`list_commits`、`list_tree`、`read_file`。统一 DTO：`RepositorySummary`、`BranchSummary`、`CommitSummary`、`TreePage` + `TreeEntry`、`FileContent`、`Page[T]`、`ProviderError{category,statusCode?,retryAfterAt?,message}`。供应商特有参数（云效 `orgId` / `repoId` / `repoPath` / `x-yunxiao-token`；GitHub `owner` / `repo` / `Authorization: Bearer`）只存在于适配器内部。适配器必须读取响应头（`X-RateLimit-*`、`x-total` / `x-page`、`Link`），状态码与响应头先于 body 解析；错误只抛归一化 `ProviderError`，不透传供应商原文。
- **来源**：新增（依据 `_handoff/from-workbench-core.md` 第 7 节已核实事实；requirements context「系统集成点」）
- **状态**：✅ 已锁定
- **理由**：AC-018-1 ~ AC-018-4、AC-020-1/2、AC-021-1/2、AC-022-1 需要统一的仓库/分支/提交/目录树/文件读取面；分页与限流在响应头，只有暴露响应头的客户端才能实现（core ADR-041 的复用点之外不新增客户端）。五个能力对应五个用户故事域，六个方法覆盖仓库列表与详情两个调用。
- **影响**：`httpx.AsyncClient` 首次用于运行时出站 HTTP（ADR-201）；新增供应商只需实现协议并注册，不改服务层与前端；契约测试用 `MockTransport` 回放 fixture，不连真实网络。
- **取代**：无

### ADR-206：错误分类映射——四类测试结果与同步错误分类

- **决策**：单一映射表（`design.md`「错误分类映射」）：
  - 401 → `auth`；403 且命中限流信号（`Retry-After`、`X-RateLimit-Remaining: 0`、限流文案）→ `rate_limited`；403 其他 → `permission_denied`；404 → `not_found`；429 → `rate_limited`；连接/读取超时 → `timeout`；DNS/拒绝/TLS → `network`；5xx → `server_error`；2xx 结构非法 → `invalid_response`。
  - 连通性测试四类结果固定为 `success` / `auth-error` / `unreachable` / `permission-denied`；限流、5xx、非法响应归入 `unreachable`，但保留可读原因与 `retryAfter`。`permission_denied` 与 `not_found` 不得归为网络失败；网络异常不得归为鉴权失败；限流不得归为鉴权失败。
  - 已保存绑定的运营调用遇到 `auth` / `permission_denied` / `not_found` → 状态置 `token_invalid`，横幅统一文案「令牌失效或权限不足」；网络/限流/5xx 不改状态（AC-018-3、AC-023-1）。
- **来源**：新增（依据 AC-018-1 ~ AC-018-4、AC-019-3/5、AC-023-1/2；BR-C22、BR-C26；AMB-021/024）
- **状态**：✅ 已锁定
- **理由**：四类结果互不误归类是 AC-REQ-26 的硬要求；403 既可能是权限也可能是限流，必须先看响应头再判定；404 在私有仓库等价于无权访问，测试界面上归「权限不足」比暴露「不存在」更安全。
- **影响**：映射表由单测逐行覆盖；前端只消费固定枚举；`ConnectionTestBadge` 仅新增 `permission-denied` / `stale` 两个状态。
- **取代**：无

### ADR-207：同步策略——基线快照、单事务覆盖、数据库 claim 互斥

- **决策**：手动同步拉取仓库详情 1 条、全部分支（供应商分页拉全）、最近 100 条提交（`per_page=100`，按提交时间倒序，最多 1 页），**不拉目录树与文件内容**（AMB-023 / AMB-026）。所有请求成功后才进入写事务：单事务内删除该绑定旧的 `repo` / `branch` / `commit` 快照行、插入新行、更新绑定摘要与同步记录。任一请求失败 → 不写快照，只写失败同步记录与绑定失败字段，旧快照和上次成功时间原样保留（AC-019-3）。并发互斥以数据库原子 claim 为准：`UPDATE repo_binding SET sync_started_at = now WHERE binding_id = ? AND status != 'revoked' AND (sync_started_at IS NULL OR sync_started_at < now - 15min)`；`rowcount=0` 返回 `409 sync_in_progress`，不产生第二条记录；进程内 per-binding `asyncio.Lock` 作为快速失败。claim TTL 15 分钟；reclaim 时把遗留 `running` 记录归并为 `failed(interrupted)`。不设定时任务、后台轮询或自动重试。
- **来源**：新增（依据 AC-019-1 ~ AC-019-6、AC-REQ-27；AMB-023/026/027；BR-C23）
- **状态**：✅ 已锁定
- **理由**：AC-019-2 要求同绑定禁止并发且不产生第二条记录；AC-019-3 要求失败保留旧元数据；AC-019-6 要求只存元数据基线。先拉全量后单事务写，避免「半成品快照」。数据库 claim 对进程崩溃与重启仍成立，不依赖内存锁。
- **影响**：同步是长请求（总预算 120s）；绑定表新增 `last_sync_attempt_at` 与 `last_sync_success_at` 两列，分别展示「最近一次尝试」和「上次成功」，避免失败时掩盖成功基线；仓库与分支全量覆盖，提交滚动保留 100 条。
- **取代**：无

### ADR-208：新鲜度与分页——实时读取，`limit` + `cursor` 对外，供应商分页在适配器内翻译

- **决策**：仓库列表、分支、提交、目录树全部实时请求供应商，不读快照；快照只用于基线展示、跨域只读引用与令牌失效时的 last-known（AMB-026 / AMB-027）。对外统一 core 的 `limit` + `cursor`：`limit` 默认 30、1–100（目录树默认 100）；`cursor` 为 base64url(JSON) 不透明游标，内含供应商页码、检索词指纹与 `repoId` / `ref` / `path`，跨查询复用或篡改返回 `400 invalid_cursor`。供应商分页（云效 `page`/`perPage` + `x-total`/`x-page`；GitHub `page`/`per_page` + `Link`）只在适配器内翻译。未成功同步过时，浏览端点返回 `200 {metadataSynced:false, items:[], guide:"sync_first"}`，不返回错误页（AC-020-3）；令牌失效时实时端点返回 502，`GET /baseline` 仍返回快照并标注上次同步时间（AC-020-4）。
- **来源**：新增（依据 AC-020-1 ~ AC-020-4、AC-021-1/2、AC-REQ-29/30；AMB-026/027；BR-C24）
- **状态**：✅ 已锁定
- **理由**：用户已确认「实时读取」口径，快照不能作为分支/提交/目录树的数据源；core 前端已按 `limit`+`cursor` 消费列表，另起分页风格会分裂前端调用。未同步返回 200 空态而不是 4xx，满足 AC-020-3「不返回错误页」。
- **影响**：浏览页每次操作都有一次供应商外呼，需按 ADR-211 控制超时与限流；快照与实时数据在界面上必须视觉区分并标注时间（interaction 决策 6）。
- **取代**：无

### ADR-209：目录树逐级浏览与 `truncated` / `hasMore` 双信号

- **决策**：目录树按层级懒加载，每次只请求当前 `path` 的直接子项；`TreePage` 同时返回 `truncated`（供应商明确标记或达到供应商单页上限）与 `hasMore`（还有下一页）。GitHub 使用 `contents` 目录列表（条目含 `name` / `path` / `type` / `size` / `sha`），达到单页上限（1,000 条）视为不完整；云效使用 `/files/tree`（`path` / `ref` / `type=DIRECT`）并按 `x-total` 与返回条数判断。任一不完整信号都必须展示「目录树不完整，请逐级浏览」或「还有更多」，不得当作完整结果（AC-021-2/3）。
- **来源**：新增（依据 AC-021-2/3；AMB-026；`_handoff` 第 7 节已核实端点）
- **状态**：✅ 已锁定
- **理由**：AMB-026 决定浏览时实时逐级拉取、同步不拉全树；逐级浏览避免递归树 100,000 条目 / 7MB 上限与整树内存峰值。GitHub `contents` 对目录返回直接子项且带 `sha` / `size`，比逐级解析 tree sha 少一次往返；其 1,000 条上限没有 `truncated` 字段，按上限保守置 `truncated=true`，宁可提示不完整也不冒充完整。
- **影响**：前端 `RepoTree` 按 `hasMore` / `truncated` 分别渲染；适配器 fixture 必须覆盖满页与截断两种响应；不引入递归树缓存。
- **取代**：无

### ADR-210：文件读取边界——先校验、后请求、1 MiB、仅 UTF-8、审计不存正文

- **决策**：读取前完成路径与 ref 校验（ADR-213）；随后经适配器读取，响应体流式限制在 1,048,576 字节 + 1，超限立即中止。`size > 1,048,576` → `413 repo_file_too_large`（details 含实际大小与上限，不截断）；base64 或含 NUL / UTF-8 解码失败 → `415 repo_file_binary` / `422 repo_file_not_utf8`，不展示乱码。成功与「超限/二进制/非 UTF-8」拒绝写 `repo_file_read_record`；**非法路径/ref 在请求前拒绝且不写记录**（AC-022-5）。正文不入库、不落盘、不写会话制品与 AiCallRecord；若被引用进分析，按 core 的 200,000 字符口径计入（不重复定义常量）。
- **来源**：新增（依据 AC-022-1 ~ AC-022-5、AC-REQ-31/34；AMB-020；BR-C25）
- **状态**：✅ 已锁定
- **理由**：1 MiB 是 AMB-020 已确认的硬上限，且与 GitHub contents API 的 1MB 完整支持边界对齐；先校验再外呼满足「非法路径不产生读取记录」；拒绝时保留大小与原因便于用户判断，不截断冒充完整内容。
- **影响**：文件内容只存在于单次请求与前端内存；云效单文件上限未核实，统一用本 spec 的 1 MiB 上限，不假设云效数值。
- **取代**：无

### ADR-211：限流与重试——零自动重试、零轮询、响应头驱动

- **决策**：连接测试、同步、浏览、读文件一律 **0 次自动重试**；不启动后台轮询或定时任务。连接测试总超时 10s（AC-018-1）；普通浏览单请求 15s；同步总预算 120s。`429`、`X-RateLimit-Remaining: 0`、`Retry-After`、`X-RateLimit-Reset` 统一转成 `retryAfterAt`（RFC 3339）；无响应头则 `retryAfterAt=null`，只展示「供应商限流」，不猜时间（AC-019-5、AC-REQ-28）。5xx 不重试；超时归 `timeout`；同步超预算立即中止且不写半成品。用户再次点击才触发下一次请求。
- **来源**：新增（依据 AC-019-5、AC-REQ-28；AMB-024；core ADR-004 的「仅网络错误/5xx 重试 1 次」不适用于本模块）
- **状态**：✅ 已锁定
- **理由**：需求明确「不自动循环重试、不启动后台轮询」；仓库浏览是用户驱动的只读操作，重试会把限流放大并让界面出现不可解释的延迟。响应头是唯一可信的限流依据，未核实数值不得硬编码。
- **影响**：前端在限流时展示可重试时间与建议操作；同步失败保留旧快照；适配器超时值集中为具名常量（ADR-216）。
- **取代**：无

### ADR-212：HTTP API 契约——15 个端点，复用 core 错误体与分页

- **决策**：全部端点挂 `require_session`，前缀 `/api/v1`：
  - 绑定：`GET|POST /projects/{projectId}/repo-bindings`；`GET /repo-bindings/{bindingId}`；`PATCH /repo-bindings/{bindingId}/token`；`POST /repo-bindings/{bindingId}/test-connection`；`POST /repo-bindings/test-connection`（未保存表单值，不落库）；`POST /repo-bindings/{bindingId}/sync`；`GET /repo-bindings/{bindingId}/sync-records`；`POST /repo-bindings/{bindingId}/unbind`。
  - 实时浏览：`GET /repo-bindings/{bindingId}/repositories|branches|commits|tree|file`。
  - 跨域只读：`GET /repo-bindings/{bindingId}/baseline` 与 `GET /repo-bindings/{bindingId}/file`（仅按 `bindingId` 引用，不暴露令牌）。
  - 错误体沿用 `{code,message,details[],requestId}`；列表沿用 `limit`+`cursor`。新增错误码：400 `invalid_provider` / `invalid_repo_identifier` / `invalid_api_base_url` / `invalid_path` / `invalid_ref` / `token_required` / `invalid_cursor`；404 `project_not_found` / `binding_not_found`；409 `repo_binding_duplicate` / `sync_in_progress` / `binding_revoked` / `repo_not_synced`；413 `repo_file_too_large`；415 `repo_file_binary`；422 `repo_file_not_utf8`；502 `provider_auth_failed` / `provider_permission_denied` / `provider_rate_limited` / `provider_unreachable` / `provider_timeout` / `provider_invalid_response`。
  - 连通性测试与同步返回 `200` +结构化结果（测试：`result` 四类枚举；同步：同步记录 + 绑定摘要），与 core 的提供商测试返回 200 的口径一致；并发同步返回 409，不产生记录。
- **来源**：新增（依据 AC-017-1 ~ AC-017-4、AC-018-5、AC-019-2/4、AC-023-4；core ADR-009/041）
- **状态**：✅ 已锁定
- **理由**：前端只消费一套错误与分页；测试失败与同步失败是「已完成的业务结果」，用 200 + 结构体让界面展示分类、原因与可重试时间，避免通用错误 Toast 覆盖具体原因；认证/权限/网络等运营失败仍用 502 + 固定码，便于统一横幅。
- **影响**：tech-design 按本 ADR 逐端点展开请求/响应 schema；跨域调用方只允许使用 `baseline` 与 `file`；其他端点不承诺跨域兼容。
- **取代**：无

### ADR-213：路径 / ref 校验与 SSRF 防护

- **决策**：路径必须为非空相对路径，不含 `..` 段、不以 `/` 或 `\` 开头、不含 `\0` 与控制字符、段长 ≤255、总长 ≤1024；ref 使用保守字符集（字母数字与 `._/-`），拒绝 `..`、`@{`、空白、`~^:?*[` 与超长值。所有路径/ref 作为查询参数统一 URL 编码，禁止拼接未编码内容。`apiBaseUrl` 仅允许 `https`、仅 origin（无路径/查询/片段）、仅 443；保存与每次请求前解析主机名，拒绝私网/回环/链路本地/保留地址；`follow_redirects=False`；GitHub 固定 `https://api.github.com`，不接受自定义域名。供应商响应只回显归一化字段或固定错误消息，不原样透传。
- **来源**：新增（依据 AC-022-5、AC-017-2、AC-REQ-25/31/35；AMB-024）
- **状态**：✅ 已锁定
- **理由**：路径穿越与 ref 注入是读文件入口的直接攻击面（BR-C25）；自定义域名是服务端发起请求的 SSRF 入口，用户可填地域域名但不应能指向内网；需求只要求 `https://`，本 ADR 在不改变用户可用性的前提下收紧到公网 origin。
- **影响**：地域版云效域名只要是公网 https 即可使用；内网自建实例（如需）需要显式放开策略，不在本期范围；错误消息由固定码生成，供应商异常原文不进入响应。
- **取代**：无

### ADR-214：前端边界——复用 AppShell / Design Tokens，增量扩展 `ConnectionTestBadge`

- **决策**：项目上下文页在项目详情表单下方新增纵向 `RepoBindingPanel` 区块；新增独立路由 `/projects/:projectId/repos/:bindingId`；文件查看为右侧 480px 抽屉（≤768px 全宽）；已解绑行留在列表末尾置灰只读。全部复用 core 的 `AppShell`、`StatusPill`、`EmptyState`、`ErrorState`、`Skeleton`、`Toast`、`ConfirmDialog`、`FormField` 与 Design Tokens；只新增 `--color-overlay`、`--spacing-5`、`--repo-drawer-width` 三个 token。`ConnectionTestBadge` 只做增量扩展（新增 `permission-denied` / `stale`），不改既有状态语义。TanStack Query 负责列表/选择器/抽屉三态与失效重取；不新增全局状态库。错误分级：字段级就近、区块级 ErrorState + 重试、页面级 Banner、全局 Toast 仅成功、模态仅解绑确认。
- **来源**：新增（依据 interaction-design `design.md` / `docs/context.md`；UXAMB-011 ~ UXAMB-015；AC-017-5、AC-018-1/5、AC-023-1）
- **状态**：✅ 已锁定
- **理由**：interaction 已确认纵向区块（不是左右分栏）与独立路由；core 的视觉与组件原语已覆盖绝大多数状态，重画会分裂设计系统并增加无障碍回归面。`stale` 态直接实现「改字段即失效」，避免用户误信旧测试结果。
- **影响**：前端只读消费本 spec 的 API；`ConnectionTestBadge` 的扩展需与 core 的组件契约测试一起跑；不在前端持久化令牌或文件内容。
- **取代**：无

### ADR-215：安全与日志边界——令牌零明文出口，审计只存元数据

- **决策**：令牌只在请求头（`x-yunxiao-token` / `Authorization: Bearer`）出现，禁止进入 URL、查询参数、日志、错误消息、同步记录、读取记录与 AiCallRecord；解密只在适配器调用前发生，密文列永不进入 API DTO；日志只允许 `bindingId`、`provider`、仓库标识、状态码与错误分类；前端不写 localStorage / sessionStorage；错误按固定码生成，不透传供应商响应原文。`repo_file_read_record` 只记路径、ref、大小、编码、状态与拒绝原因，不存正文。解绑清空密文与掩码，此后所有外呼入口先查 `status='revoked'` 并拒绝。
- **来源**：新增（依据 AC-017-1、AC-018-2、AC-022-4、AC-023-4、AC-REQ-25/34；AMB-005/029；BR-C21）
- **状态**：✅ 已锁定
- **理由**：需求把「完整令牌出现次数为 0」列为商业目标验收口径；令牌一旦进入日志或记录就不可撤回。解绑后不再请求是 AC-023-4 的硬要求，必须在服务入口统一拦截，而不是只靠 UI 置灰。
- **影响**：日志采集与错误处理需要统一的脱敏出口；测试必须扫描响应、错误体、日志与记录表断言无令牌；备份与密钥分开保管（ADR-204）。
- **取代**：无

### ADR-216：配置、常量与启动自检

- **决策**：新增具名常量（`src/workbench/repos/constants.py`）：`REPO_FILE_MAX_BYTES = 1_048_576`、`REPO_COMMIT_LIMIT = 100`、`REPO_CONNECT_TIMEOUT_SECONDS = 10`、`REPO_HTTP_TIMEOUT_SECONDS = 15`、`REPO_SYNC_BUDGET_SECONDS = 120`、`REPO_SYNC_LOCK_TTL_SECONDS = 900`、`REPO_PAGE_DEFAULT = 30`、`REPO_PAGE_MAX = 100`、`REPO_TREE_PAGE_LIMIT = 100`、`REPO_METADATA_MAX_BYTES = 5_242_880`。唯一新增环境变量是 `AW_REPO_TOKEN_KEY`；启动自检：密钥存在且为 32 字节 base64、数据库 schema 版本等于 Alembic head（含 `0008`）、`AW_PROMPT_MAX_CHARS` 由 core 提供；任一失败拒绝启动。不新增其它可调密钥或数值型环境变量；未核实项（云效限流数值、单文件上限等）不写成配置默认值。
- **来源**：新增（依据 AC-017-2、AC-019-5、AC-022-2；core ADR-005/020；AMB-020/024）
- **状态**：✅ 已锁定
- **理由**：有含义的阈值集中为常量，避免魔法数字散落在适配器与服务层；密钥与 schema 在启动时失败，比运行到第一次同步才暴露更安全，也与 core 的启动策略一致。未核实数值不落地，满足「不得编造数值」的上游约束。
- **影响**：tech-design 可把超时/分页常量映射为模块常量或只读配置；任何数值调整都要同步用例与文档；新增环境变量需走变更并更新部署说明。
- **取代**：无

### ADR-217：测试与门禁——36 AC / 11 EARS，双方言 + 假供应商 + 令牌泄漏断言

- **决策**：pytest 用例名带 TC 编号（`test_tc017_1_...` / `TC-017-1`），映射 36 条 AC 与 11 条 EARS；后端在 SQLite 与 MySQL 两方言跑迁移与关键用例；供应商调用统一用 `httpx.MockTransport` + 录制 fixture，不连真实网络；前端用 Vitest + Testing Library 覆盖组件状态，关键流程（绑定 → 测试 → 同步 → 浏览 → 读文件 → 解绑）用 Playwright；每个涉及令牌的用例断言响应、错误体、日志与同步/读取记录中完整令牌出现次数为 0；门禁沿用 `.aw/config.json` 的 pytest preset 与 `python3 .aw/aw.py verify`。不新增 pack 专属测试约定。
- **来源**：新增（依据 36 AC / 11 EARS；AGENTS.md 测试命名；core ADR-041 的双方言纪律）
- **状态**：✅ 已锁定
- **理由**：需求把令牌零明文、四类连通性结果、并发同步、失败保留、限流、truncated、1 MiB、二进制/非 UTF-8、路径穿越、令牌失效恢复与解绑后不再请求列为重点验证项；假供应商让错误映射与边界可重复回放，双方言避免迁移漂移（RISK-207）。
- **影响**：tech-design / tech-tasks 需把每条 AC 映射到具体 TC；fixture 要覆盖 401/403/404/429/超时/5xx/截断/满页/大文件/非 UTF-8；不引入真实令牌或真实仓库做 CI。
- **取代**：无

## 约束条件

- 技术栈与 core 一致，版本以 core 的 `pyproject.toml` / `uv.lock` / `package-lock.json` 为唯一真源；不引入第二运行时、数据库或前端框架（ADR-201）。
- 仓库令牌使用独立密钥 `AW_REPO_TOKEN_KEY`（AES-256-GCM），与 core 的 `AW_ENCRYPTION_KEY` 并存、不共用；缺失或非法即拒绝启动；仅回显掩码（ADR-204 / ADR-216）。
- 迁移顺序固定：core `0006_knowledge_injection` → knowledge-base `0007` → 本 spec `0008_repo_integration`（`down_revision = 0007`），同一线性 Alembic 历史（ADR-203）。
- 四张表：`repo_binding`、`repo_sync_record`、`repo_metadata_snapshot`、`repo_file_read_record`；双方言同构，大文本用 `MEDIUMTEXT` 变体，JSON 用 `sa.JSON`，唯一键含可空 `active_flag`（ADR-203）。
- 令牌不得出现在接口响应、日志、错误消息、同步记录、读取记录与 AiCallRecord；前端不持久化令牌；解绑后不再发起任何供应商请求（ADR-215）。
- 单文件 ≤1,048,576 字节、仅 UTF-8；超限/二进制/非 UTF-8 拒绝并说明；路径含 `..`、绝对路径或非法 ref 在请求前拒绝且不写读取记录（ADR-210 / ADR-213）。
- 同步只由用户手动触发；同绑定禁止并发；仓库与分支全量覆盖、提交保留最近 100 条；不含目录树与文件内容；失败保留上次成功元数据与时间；不自动重试、不轮询、无定时任务（ADR-207 / ADR-211）。
- 分支、提交、目录树与仓库列表实时读取；快照只作基线与 last-known 展示；未同步时返回空态而非错误页；令牌失效时仍可读基线（ADR-208）。
- 复用 core 的登录态、错误体 `{code,message,details[],requestId}`、`limit`+`cursor` 分页、`project_context` 只读与 `AW_PROMPT_MAX_CHARS=200000`；不新建认证、错误或分页体系（ADR-202 / ADR-212）。
- 跨域只读契约仅 `GET /repo-bindings/{bindingId}/baseline` 与 `/file`；其他业务域不得持有令牌或直连供应商（ADR-202 / ADR-212）。
- `apiBaseUrl` 仅 https 公网 origin、仅 443、禁重定向；GitHub 固定 `https://api.github.com`；私网/回环/链路本地地址拒绝（ADR-213）。
- 未核实外部事实（云效限流数值、云效单文件上限、云效权限文案、GitHub PAT 过期头、fine-grained PAT 映射、地域域名细节）不得写成硬编码数值或推测性 UI（`design.md`「未核实外部事实与处理口径」）。
- 未安装任何 AlonWorkflow pack，未套用 pack 专属约定。

## 状态

architecture-locked（2026-11-18 11:40 tech-arch 产出；ADR-201 ~ ADR-217 共 17 条；阶段确认由编排者记录于 `approvals.md`，用户确认前视为待复核。无旧 ADR 被取代。）
