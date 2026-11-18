# Technical Design — Design（repo-integration）

> 阶段：tech-arch（步骤 1–3.5）。上游：`requirements-analysis/docs/context.md`（7 US / 36 AC / 11 EARS，已确认）、`interaction-design/docs/context.md`（已确认，2026-11-18 11:23:18）、`_handoff/from-workbench-core.md`（已联网核实的外部接口事实）。
> 架构决策：`docs/architecture-decisions.md`（ADR-201 ~ ADR-217，architecture-locked）。技术栈不重新选型，完整继承 workbench-core；本 spec 只做仓库集成垂直模块。
> 本体：编排者未生成 `ontology-slices/tech-arch.md`（项目尚无 `ontology-work/views/index.json`），模块划分直接对照 `_shared/ontology/` 的 ENT-C12 ~ ENT-C15、BR-C21 ~ BR-C27、BP-C9 ~ BP-C11，不新增模块边界。
> 未安装任何 AlonWorkflow pack（`.aw/install.json` 的 `packs` 为空），未套用 pack 专属约定。

## 技术选型

### 技术栈总览

| 层次 | 选型 | 版本 | 来源（已有 / 新增） | 理由摘要 |
|------|------|------|------------------|---------|
| 后端运行时 | Python + FastAPI + Uvicorn（单进程） | 3.12+；fastapi 0.163.1 / uvicorn 0.54.0 | 已有（core ADR-001） | 与 core 同进程；复用 `require_session`、错误处理器与启动自检 |
| 数据校验 | Pydantic 2 | 2.14.3 | 已有（core） | 请求/响应、供应商响应归一化后的边界校验 |
| ORM / 迁移 | SQLAlchemy 2.1 + Alembic | 2.1.9 / 1.20.1 | 已有（core ADR-003 / 015 ~ 017） | 四张新表；MySQL 8.4 与 SQLite 双方言同构；迁移从 `0008` 起 |
| 数据库 | MySQL 8.4 LTS（生产）/ SQLite（开发测试） | mysql:8.4.13 / aiosqlite 0.22.1 | 已有（core ADR-015） | 令牌密文与元数据落库；两方言必须同时通过迁移与用例 |
| 出站 HTTP 客户端 | `httpx.AsyncClient` | 随 core lock（core 测试依赖树已含 httpx） | 新增（运行时首次直接使用） | 必须读取响应头（`X-RateLimit-*`、`x-total`/`x-page`、`Link`）；禁用自动重试与重定向；不引入第二套 HTTP 栈 |
| 凭证加密 | AES-256-GCM（`cryptography` 50.x）+ 独立密钥 | cryptography 50.x | 已有（算法）/ 新增（独立密钥接线） | 沿用 core 的 `v1:<nonce>:<ciphertext>` 与掩码口径；仓库令牌密钥独立，可单独轮换 |
| 前端框架 | React 19 + TypeScript + Vite + React Router | react 19.3.1 / typescript 7.0.2 / vite 8.3.8 / react-router 8.5.1 | 已有（core ADR-002） | 复用 AppShell、AuthGate、侧边栏「基座管理」分组与同源托管 |
| 前端数据 | TanStack Query | 5.107.2 | 已有（core） | 列表/选择器/抽屉三态与失效重取；`useInfiniteQuery` 接 `nextCursor` |
| 前端 UI 原语 | CSS 变量 + CSS Modules + Radix Primitives | radix-ui 1.8.1 | 已有（core ADR-007） | 直接使用 interaction-design 的 token；抽屉与对话框焦点管理 |
| 测试 | pytest + httpx（`MockTransport`）/ Vitest + Testing Library / Playwright | core 锁定版本 | 已有（core） | 假供应商 fixture 覆盖 36 AC / 11 EARS；令牌泄漏断言；双方言迁移 |

### 详细决策

#### 决策 1：技术栈完整继承 core，不重新选型

- **选择**：全部沿用 core 的运行时、框架、数据库、前端与测试栈；本 spec 只在既有工程内新增 `repo-integration` 垂直模块。
- **理由**：上游已锁定「栈与 core 一致」；仓库集成要复用 `require_session`、错误体、分页、凭证加密与 AppShell，换栈会把进程内契约退化成 HTTP 并复制登录态。
- **备选方案**：独立服务 + 独立前端包；被否，单用户单进程无收益，且会引入第二套认证与部署面。
- **权衡**：与 core 同一发布单元；四张表的迁移必须插进同一条 Alembic 链（`0008` 起），版本号协调是硬约束。

#### 决策 2：出站 HTTP 用 `httpx.AsyncClient`，必须暴露响应头

- **选择**：每个供应商适配器持有一个 `httpx.AsyncClient`（连接池复用），`follow_redirects=False`、`max_retries=0`；读取响应头与状态码后再解析 body；body 解析前做大小上限与 JSON 结构校验。
- **理由**：GitHub 的分页/限流在 `Link` 与 `X-RateLimit-*`，云效的分页在 `x-total` / `x-page`，只返回 body 的客户端无法实现 AC-019-5、AC-021-2。官方 SDK 面向模型调用，不适合通用 REST 只读浏览。
- **备选方案**：`requests`（同步、阻塞事件循环）；官方 SDK（无通用端点与响应头）。均被否。
- **权衡**：新增运行时直接使用；若 core 的生产依赖未固定 httpx，按 core lock 的版本追加，不引入第二个 HTTP 库。

#### 决策 3：无后台任务、队列与定时器

- **选择**：连通性测试与同步都在请求生命周期内完成；不引入 Celery/APScheduler/后台轮询。同步设置总预算（默认 120s），超预算即失败并保留旧快照。
- **理由**：AC-REQ-27 / AC-REQ-28 明确「不自动触发、不轮询」；单用户场景请求内完成即可，后台任务会新增任务表、重启恢复与重复执行语义。
- **备选方案**：异步任务队列 + 任务状态轮询；被否，直接违反需求口径。
- **权衡**：分支很多时同步请求较长；用分页上限、总预算与「失败保留旧快照」控制影响。

#### 决策 4：文件内容不落盘、不缓存、不建索引

- **选择**：单文件读取即取即用，只在响应与内存中存在；审计只记 `RepoFileReadRecord` 元数据；不写会话制品、不写 `AiCallRecord` 正文、不写本地缓存。
- **理由**：AC-022-4 / AC-REQ-34 的数据边界；写入文件系统会引入 `AW_DATA_DIR` 备份、清理与路径隔离的额外面。
- **备选方案**：本地临时文件缓存（减少重复请求）；被否，需求要求实时且内容不落盘，且会与解绑后的「不再请求 / 只读快照」语义冲突。
- **权衡**：同一文件反复查看会重复请求供应商；用前端内存态与查询缓存（不持久化）缓解，不改变服务端口径。

#### 决策 5：仓库令牌独立密钥，与模型密钥并存

- **选择**：AES-256-GCM 算法、`v1:<nonce>:<ciphertext>` 格式与掩码口径沿用 core；仓库令牌使用独立环境变量 `AW_REPO_TOKEN_KEY`（32 字节 base64），core 的模型密钥 `AW_ENCRYPTION_KEY` 继续只服务 AI 提供商。两个密钥各自校验，任一缺失、base64 非法或长度不足 32 字节即拒绝启动；不自动轮换、不互相派生。
- **理由**：AMB-029 已确认仓库令牌独立密钥，便于单独轮换而不牵连模型密钥；AC-REQ-25 要求服务端加密与掩码回显（`ghp_****abcd`），接口、日志、同步/读取记录与 AiCallRecord 不出现完整令牌。
- **备选方案**：与 core 共用 `AW_ENCRYPTION_KEY`；被否，轮换会同时影响模型调用与仓库访问，爆炸半径过大。
- **权衡**：多一个必须备份与管理的密钥；密钥丢失后全部仓库令牌需重填（不做密文迁移）；备份需与数据库分开保管。

## 系统架构

### 分层说明

| 层次 | 职责 | 技术 |
|------|------|------|
| 前端展示层 | 项目上下文页「仓库绑定」区块、独立浏览路由、文件抽屉、失效横幅与解绑对话框 | React 19 + TS + TanStack Query + CSS Modules/Radix；复用 AppShell 与 Design Tokens |
| API 层 | 15 个 `/api/v1` 端点的路由、schema、`require_session`、错误映射、`limit`+`cursor` 分页、跨域只读契约 | FastAPI + Pydantic 2 |
| 领域服务层 | 绑定/令牌更新/测试/同步/解绑编排、状态机、快照覆盖、并发互斥、审计写入 | `services/repos/*`（纯业务，不直接拼 HTTP） |
| 供应商适配层 | 五类能力（仓库、分支、提交、目录树、单文件）的协议实现、分页翻译、响应头读取、错误归一化 | `repos/providers/{github,yunxiao}.py` + `httpx.AsyncClient` |
| 校验与安全层 | 仓库标识/域名/路径/ref 校验、SSRF 目标检查、密文加解密、掩码、日志脱敏 | `repos/validation.py`、`repos/crypto.py`、`repos/redaction.py` |
| 持久化层 | 四张新表、唯一约束、快照覆盖事务、同步 claim、读取审计 | SQLAlchemy 2.1 + Alembic（`0008_repo_integration`） |
| core 集成层 | 登录态、错误体、分页、`project_context` 只读、`AW_PROMPT_MAX_CHARS` 引用、前端 `ConnectionTestBadge` 复用 | 进程内调用；不新建 HTTP 客户端、不复刻认证 |

### 模块划分

| 模块 | 职责 | 关联 US |
|------|------|---------|
| 绑定与令牌模块（`repos/binding`） | 创建/列表/详情、唯一性、字段校验、令牌加密与更新、掩码、状态机、解绑 | US-017、US-023 |
| 连通性模块（`repos/connectivity`） | 保存前/后一次性只读测试、10s 超时、四类结果、测试结果落库（仅已保存绑定） | US-018 |
| 同步模块（`repos/sync`） | 互斥 claim、仓库/全部分支/最近 100 提交、快照覆盖、同步记录、失败保留旧基线 | US-019 |
| 浏览模块（`repos/browse`） | 仓库/分支/提交/目录树实时读取、检索、分页、truncated/has_more | US-020、US-021 |
| 文件读取模块（`repos/file`） | 路径/ref 前置校验、1 MiB 与 UTF-8 边界、单文件读取、审计 | US-022 |
| 前端仓库模块（`frontend/src/repos`） | 绑定区块与浏览页组件、独立浏览路由、480px 抽屉、失效横幅、解绑确认 | US-017 ~ US-023 |
| core 嵌入点 | 项目上下文页 `RepoBindingPanel` 挂载；`ConnectionTestBadge` 增量扩展 `permission-denied` / `stale`；「仓库地址」降级为自由备注（AMB-030） | US-017、US-018、US-023 |

### 供应商适配器契约

统一协议（Python `Protocol`，async）：

```text
RepoProvider
  list_repositories(*, search: str | None, cursor: str | None, limit: int) -> Page[RepositorySummary]
  get_repository(repo: RepositoryRef) -> RepositorySummary
  list_branches(repo, *, search: str | None, cursor: str | None, limit: int) -> Page[BranchSummary]
  list_commits(repo, *, ref: str, cursor: str | None, limit: int) -> Page[CommitSummary]
  list_tree(repo, *, ref: str, path: str, cursor: str | None, limit: int) -> TreePage
  read_file(repo, *, ref: str, path: str) -> FileContent
```

- 五类能力、六个方法：`repository`（列表 + 详情）、`branches`、`commits`、`tree`、`file`。
- 归一化 DTO：
  - `RepositorySummary{repoId, fullName, displayName, defaultBranch?, webUrl?}`
  - `BranchSummary{name, isDefault, headSha?, committedAt?}`
  - `CommitSummary{sha, shortSha, title, authorName, committedAt}`
  - `TreePage{path, ref, entries[], truncated, hasMore, nextCursor?, total?}`；`TreeEntry{name, path, type: file|dir, sizeBytes?}`
  - `FileContent{path, ref, sizeBytes, encoding: text, content, fetchedAt}`
  - `Page[T]{items[], nextCursor?, total?}`
  - `ProviderError{category, statusCode?, retryAfterAt?, message}`；`category ∈ auth | permission_denied | rate_limited | not_found | network | timeout | server_error | invalid_response`
- 供应商特有参数（云效 `orgId` / `repoId` / `repoPath` / `x-yunxiao-token`；GitHub `owner` / `repo` / `Authorization: Bearer`）只存在于适配器内部，服务层与前端只看到归一化 DTO。
- 适配器必须把所有响应头与状态码交给统一错误映射后再抛 `ProviderError`；错误消息只含可读分类与供应商状态码，不含请求头、令牌、响应原文。

### 错误分类映射

| 供应商信号 | `ProviderError.category` | 连通性测试四类结果 | 绑定状态副作用 | 同步记录 `errorCategory` |
|-----------|--------------------------|-------------------|---------------|--------------------------|
| 401 | `auth` | `auth-error`（鉴权失败） | `token_invalid` | `auth` |
| 403 且命中限流信号（`Retry-After`、`X-RateLimit-Remaining: 0`、限流文案） | `rate_limited` | `unreachable`（附限流原因与可重试时间） | 不变 | `rate_limit` |
| 403 其他 | `permission_denied` | `permission-denied`（权限不足） | `token_invalid`（横幅文案「令牌失效或权限不足」） | `permission` |
| 404（读仓库/分支/文件） | `not_found` | `permission-denied`（无权访问或不存在） | `token_invalid` | `permission` |
| 429 | `rate_limited` | `unreachable`（附限流原因与可重试时间） | 不变 | `rate_limit` |
| 连接超时 / 读取超时 | `timeout` | `unreachable`（网络失败） | 不变 | `network` |
| DNS 失败 / 连接被拒 / TLS 失败 | `network` | `unreachable`（网络失败） | 不变 | `network` |
| 5xx | `server_error` | `unreachable`（上游不可用） | 不变 | `other` |
| 2xx 但结构非法/JSON 解析失败 | `invalid_response` | `unreachable`（上游返回异常） | 不变 | `other` |
| 200 且 `X-RateLimit-Remaining: 0` | `rate_limited`（不再继续翻页/请求） | `unreachable`（限流） | 不变 | `rate_limit` |

四条不误归类规则：权限不足不得归为网络失败；网络失败不得归为鉴权失败；限流不得归为鉴权失败；5xx/非法响应不得伪装成成功。测试结果按四类固定枚举返回；限流与 5xx 在四类中归入「网络失败」，但 `message` 与 `retryAfter` 保留可读原因。

### 同步、并发与新鲜度

- **同步范围（基线快照）**：仓库详情 1 条、全部分支（供应商分页拉全）、最近 100 条提交（`per_page=100`，按提交时间倒序，最多 1 页）；**不拉目录树、不拉文件内容**（AMB-023 / AMB-026）。
- **写入语义**：所有供应商请求成功后才进入写事务；单事务内删除该绑定旧的 `repo` / `branch` / `commit` 快照行并插入新行，再更新绑定摘要与同步记录。任一请求失败 → 不写快照，只写失败同步记录与绑定失败字段，**旧快照与上次成功时间原样保留**（AC-019-3）。
- **并发互斥**：以数据库原子 claim 为准（`UPDATE repo_binding SET sync_started_at = now WHERE binding_id = ? AND status != 'revoked' AND (sync_started_at IS NULL OR sync_started_at < now - TTL)`）；`rowcount=0` 返回 `409 sync_in_progress`，不产生第二条同步记录（AC-019-2）。进程内再加一层 per-binding `asyncio.Lock` 作为快速失败。claim TTL 15 分钟；后续同步 reclaim 时把遗留 `running` 记录归并为 `failed(interrupted)`。
- **时间展示**：区分「上次成功同步时间」`last_sync_success_at` 与「最近一次尝试」`last_sync_attempt_at` / `last_sync_status`。失败时 UI 同时展示「上次成功：<时间>」与「最近一次：失败 <时间> · 原因」，满足 AC-019-3 / AC-019-4 又不掩盖失败。
- **新鲜度（实时）**：仓库列表、分支、提交、目录树全部实时请求供应商；快照只用于基线展示、跨域只读引用与令牌失效时的 last-known（AMB-026 / AMB-027）。未成功同步过时，浏览端点返回 `200 {metadataSynced: false, items: [], guide: "sync_first"}`，不返回错误页（AC-020-3）；UI 显示空态与「去同步」。
- **令牌失效时**：实时端点返回 `502 provider_auth_failed` / `provider_permission_denied`，`GET /baseline` 仍返回快照并标注 `lastSyncAt` 与 `revoked` 状态（AC-020-4）；UI 用快照兜底并置灰操作。

### 分页、限流与重试

- 对外统一 `limit` + `cursor`：`limit` 默认 30、1–100（目录树默认 100）；`cursor` 为 base64url(JSON) 的不透明游标，内含供应商页码、检索词指纹、`repoId` / `ref` / `path`；跨查询复用或篡改返回 `400 invalid_cursor`。
- 供应商分页翻译：云效 `page` / `perPage` + `x-total` / `x-page`；GitHub `page` / `per_page` + `Link` 的 `rel="next"`。适配器负责页码起点与终止条件，服务层不感知。
- 限流：不自动重试、不循环、不轮询（AC-REQ-28）。`429`、`X-RateLimit-Remaining: 0`、`Retry-After` / `X-RateLimit-Reset` 统一转成 `retryAfterAt`（RFC 3339）并回传；无响应头则 `retryAfterAt=null`，UI 只显示「供应商限流」不猜时间。
- 超时与预算：连接测试总超时 10s（AC-018-1）；普通浏览单请求 15s；同步总预算 120s。超时归 `timeout`，同步中止且不写半成品。
- 重试策略：**0 次自动重试**（连接测试、同步、浏览、读文件一致）；重试只由用户显式操作触发。

### 文件读取与安全边界

- 前置校验（发起任何外部请求之前）：路径非空、相对路径、不含 `..` 段、不以 `/` 或 `\` 开头、不含 `\0` 与控制字符、段长 ≤255、总长 ≤1024；ref 限保守字符集（字母数字与 `._/-`），拒绝 `..`、`@{`、空白、`~^:?*[` 与超长值。校验失败返回 `400 invalid_path` / `invalid_ref`，**不写读取记录**（AC-022-5）。
- 大小与编码：文件 >1,048,576 字节 → `413 repo_file_too_large`（details 含实际大小与上限，不截断）；供应商返回 base64 或内容含 NUL / UTF-8 解码失败 → `415 repo_file_binary` / `422 repo_file_not_utf8`；拒绝时写 `repo_file_read_record(status=refused, reject_reason=...)`，成功时写 `status=success`，正文一律不入库、不入日志。
- SSRF：`apiBaseUrl` 仅允许 `https`、仅 origin（无路径/查询/片段）、仅 443；保存与每次请求前解析主机名并拒绝私网/回环/链路本地/保留地址；`follow_redirects=False`；GitHub 固定 `https://api.github.com`，不接受自定义域名。供应商响应不得回显到界面（只展示归一化字段或固定错误消息）。
- 令牌：只在请求头（`x-yunxiao-token` / `Authorization: Bearer`）出现，禁止拼进 URL/查询参数；解密只在适配器调用前发生，令牌变量不进入日志上下文；错误消息按固定码生成，不透传供应商原文。

### 关键数据流

**绑定**：`POST /projects/{projectId}/repo-bindings` → 校验提供商/仓库标识/域名/令牌非空 → 计算 `repo_key` → 加密令牌与掩码 → 唯一性检查（`UNIQUE(project_id, provider, repo_key, active_flag)`）→ 写绑定（`status=unverified`）→ 返回 `bindingId` 与掩码；任何失败不写行。

**测试连接**：已保存 → 解密令牌 → 适配器 `get_repository`（10s）→ 结果分类 → 已保存绑定更新 `status` / `lastVerifiedAt` / `lastVerifyResult`（网络失败不改状态）；未保存 → 表单值直接测试，**零落库、零日志正文**。全程不写同步记录、会话、制品、AiCallRecord。

**同步**：`POST /repo-bindings/{id}/sync` → claim → 插入 `repo_sync_record(running)` → 拉仓库详情 → 分页拉全部分支 → 拉最近 100 提交 → 单事务覆盖快照 + 更新绑定摘要 + 记录成功 → 释放 claim。失败 → 记录失败分类/消息/可重试时间，保留旧快照与 `last_sync_success_at`。

**浏览**：选择器/提交/目录树 → 校验绑定未解绑与已同步基线 → 实时调供应商（分页翻译为 `limit`+`cursor`）→ 归一化返回；`truncated=true` 或达到供应商单页上限时置 `hasMore`/`truncated`，UI 显示「还有更多」/「目录树不完整，请逐级浏览」。

**读文件**：校验路径/ref → 未解绑 → 适配器读取（流式限制 1 MiB+1）→ 大小/编码判定 → 成功返回内容与元数据、写审计；拒绝写审计（非法路径除外）。

**解绑**：`POST /repo-bindings/{id}/unbind` → 状态 `revoked`、`active_flag=NULL`、清空密文与掩码、写 `revoked_at` → 此后所有需要供应商请求的端点返回 `409 binding_revoked`；快照与同步/读取记录只读保留；重新绑定生成新 `bindingId`（AC-023-4 ~ AC-023-6）。

### 未核实外部事实与处理口径

| 项 | 状态 | 本方案处理 |
|----|------|-----------|
| 云效官方速率限制数值 | 未核实 | 不硬编码任何数值；只按 `429` / 响应头 / 限流信号判断，展示可重试时间（若有） |
| 云效单文件大小上限 | 未核实 | 统一按本 spec 的 1 MiB 客户端上限拒绝；不假设云效上限，不据此放行 |
| 云效令牌最小权限官方表述 | 未核实 | UI 只使用需求原文的「代码库读取」提示，不生成更细的权限映射 |
| GitHub PAT 过期时间响应头名称与语义 | 未核实 | `tokenExpiresAt` 默认 `null`；只有 tech-design 核实到确定响应头后才读取；无数据不推测、不提示「即将过期」 |
| GitHub fine-grained PAT 的 Contents / Metadata 精确映射 | 未核实 | UI 只复制需求建议文案，不做自动权限校验或推断 |
| 云效地域版域名形态与路径差异 | 部分核实（仅知地域版路径不带 `organizations/{orgId}`） | `apiBaseUrl` 作为不透明 origin 存储；路径形态由适配器按「中心站/地域站」两种既定形态处理，不新增猜测 |
| 五类适配器契约、错误映射、分页游标与限流读取 | 本阶段结论 | 见「供应商适配器契约」「错误分类映射」「分页、限流与重试」 |
| 快照表结构、保留策略、`truncated` 表示、并发互斥 | 本阶段结论 | 见 ADR-203 / ADR-207 / ADR-209；`truncated` 与 `hasMore` 同时保留，供应商截断信号优先 |

> 涉及本体：ENT-C12 ~ ENT-C15、BR-C21 ~ BR-C27、BP-C9 ~ BP-C11、TERM-C14 ~ TERM-C16（来源 `_shared/ontology/`；无 `ontology-slices/tech-arch.md`）。模块划分沿用对象所属模块，不新增跨域依赖。

## 风险登记表

> 编号从 RISK-201 起，避免与 core 的 RISK-001 ~ RISK-016、knowledge-base 的 RISK-101 ~ RISK-113 冲突。评分矩阵：影响 × 概率 → 🔴 Critical / 🟡 Medium / 🟢 Low。

| ID | 风险 | 类别 | 影响 | 概率 | 评分 | 缓解措施 |
|----|------|------|------|------|------|---------|
| RISK-201 | 令牌原文经接口响应、日志、错误消息、同步/读取记录或前端持久缓存泄露 | 安全 | 高 | 中 | 🔴 Critical | 密文列永不进 DTO；错误按固定码生成；日志只允许 bindingId/provider/repo/status/category；前端不落 localStorage；用例扫描日志、错误体、记录表与响应断言无令牌 |
| RISK-202 | 自定义 `apiBaseUrl` 被用于 SSRF（内网探测、云元数据、DNS rebinding） | 安全 | 高 | 中 | 🔴 Critical | 仅 https + 仅 origin + 仅 443；解析后拒绝私网/回环/链路本地/保留地址；禁重定向；GitHub 固定域名；保存与请求前各校验一次 |
| RISK-203 | 路径穿越 / ref 注入 / 未编码参数导致越权读文件或供应商侧注入 | 安全 | 高 | 中 | 🔴 Critical | 请求前白名单校验路径与 ref；拒绝 `..`、绝对路径、控制字符；作为查询参数统一 URL 编码；非法输入不产生读取记录与外呼 |
| RISK-204 | 401 / 403 / 404 / 429 / 超时 / 5xx 互相误归类，导致用户按错误方向修复 | 业务 | 高 | 高 | 🔴 Critical | 单一映射表（ADR-206）；限流信号优先于 403；网络异常先于状态码判断；四类测试结果固定枚举；映射表单测逐行覆盖 |
| RISK-205 | 并发同步或进程崩溃留下 claim，导致重复同步、丢记录或永久锁定 | 技术 | 中 | 中 | 🟡 Medium | 数据库原子 claim + 进程内锁；claim TTL 15 分钟；reclaim 时把遗留 running 归并 failed(interrupted)；409 不产生第二条记录；用例覆盖双击与崩溃恢复 |
| RISK-206 | 同步失败时部分写入或覆盖旧快照，导致用户丢失上次成功基线 | 数据 | 高 | 低 | 🟡 Medium | 先拉全量后单事务覆盖；失败只写同步记录与失败字段；快照行按 binding 原子替换；用例注入分支分页中途失败断言旧快照不变 |
| RISK-207 | 双方言漂移：`TEXT` 静默截断、可空唯一索引语义、JSON 列、CHECK 与时间精度 | 技术 | 高 | 中 | 🔴 Critical | 大文本用 `Text().with_variant(MEDIUMTEXT, "mysql")`；唯一性用 `active_flag` 可空唯一；JSON 用 `sa.JSON` 且不建索引；CHECK 变更在 SQLite 用 batch；CI 两方言从空库迁到 head |
| RISK-208 | 目录树分页/截断被当作完整结果展示，用户据此得出错误结论 | 业务 | 中 | 中 | 🟡 Medium | `truncated` 与 `hasMore` 双字段；达到供应商单页上限也置提示；UI 固定文案「目录树不完整，请逐级浏览」；fixture 覆盖截断与满页 |
| RISK-209 | 大文件 / 大响应导致内存峰值或长请求 | 技术 | 中 | 中 | 🟡 Medium | 文件流式读取并在 1 MiB+1 中止；元数据响应 5 MiB 上限；同步总预算 120s；超限快速失败 |
| RISK-210 | 独立密钥缺失、长度错误或轮换后旧令牌全部不可解密 | 运维 | 中 | 低 | 🟡 Medium | 启动自检密钥（32 字节 base64），缺失/非法拒绝启动；不做自动轮换；密钥变更需用户重填令牌；文档写明备份与轮换步骤 |
| RISK-211 | 供应商 API 漂移或未核实数值（云效分页起点、限流、单文件上限）导致行为偏差 | 外部 | 中 | 中 | 🟡 Medium | 适配器隔离端点与参数；以响应头/状态码为准不硬编码数值；录制 fixture 回归；未核实项在 tech-design 继续核实 |
| RISK-212 | 解绑后仍能解密令牌或仍发起请求 | 安全 | 高 | 低 | 🟡 Medium | 解绑清空密文与掩码并置 `revoked`；所有外呼入口先查状态；解密函数拒绝 revoked；用例断言解绑后 provider 调用次数为 0 |
| RISK-213 | 重新绑定时旧解绑行占用唯一键导致无法绑定 | 技术 | 低 | 中 | 🟢 Low | 唯一键含可空 `active_flag`（在绑 `'1'`、解绑 `NULL`）；两方言验证多 NULL 行为；重新绑定生成新行 |
| RISK-214 | 跨域只读接口被滥用或绕过登录态读取元数据/文件 | 安全 | 中 | 低 | 🟢 Low | 只读契约仅 `baseline` + `file`；全部挂 `require_session`；不暴露令牌/密文；文件仍受大小、编码、路径校验 |
| RISK-215 | 改表单字段后仍显示旧测试结果，用户误信「已连接」 | 体验 | 低 | 中 | 🟢 Low | 复用 `ConnectionTestBadge` 的 `stale` 态；任一字段变更即置灰标「已失效（时间 · 结果）」；保存前测试不入库 |
| RISK-216 | 迁移顺序错位（`0008` 早于 knowledge-base 的 `0007`）导致从零迁移失败 | 集成 | 中 | 低 | 🟡 Medium | `0008_repo_integration.down_revision = 0007`；CI 从空库按 `0001 → 0008` 迁移；合并前核对三方 head；不合并孤立迁移 |

### Critical 风险应急预案

- **RISK-201**：发现令牌进入任何出口时，立即关闭出站日志中的请求/响应体记录，按 `bindingId` 扫描并清除受影响日志；轮换 `AW_REPO_TOKEN_KEY` 并要求全部绑定重填令牌；补回归用例后重新评审。
- **RISK-202**：出现可疑外呼时立即禁用自定义域名（退回默认域名），阻断出站并审计 `api_base_url` 变更；修正解析校验与 DNS rebinding 防护后重跑安全用例。
- **RISK-203**：发现越界读取时下线文件读取端点，修正路径/ref 校验与编码后重跑穿越用例；审计读取记录与供应商访问日志。
- **RISK-204**：若测试结果误分类，暂停绑定状态自动更新（保持原状态），修正映射表并回放 fixture 后再启用；已误标状态可由成功测试恢复。
- **RISK-207**：某方言出现截断、唯一索引不生效或 CHECK 失败时停止发布，新增修正迁移（不改历史迁移）；必要时用 batch 重建表并重跑双方言用例。

## 扩展计划

| 阶段 | 用户规模 | 架构变化 |
|------|---------|---------|
| 本期（元数据 + 按需文件） | 1 人、单进程 | 四张表；实时浏览 + 手动同步基线；无后台任务；文件不落盘 |
| 仓库数量与历史增长 | 单项目多绑定、提交历史更长 | 同步记录/快照按时间分区或归档；提交改为按需实时翻页（快照只保留基线 sha）；不改变 API 契约 |
| 供应商扩展（GitLab / Gitee） | 单用户 | 新增 `RepoProvider` 实现与端点映射，复用归一化 DTO、错误映射、分页与安全校验；不新增表 |
| 多用户 / 多副本 | 2–10 人 | 绑定归属接入账号权限；同步 claim 改为数据库行锁 + 租约；出站客户端加按绑定配额；文件内容可评估对象存储短期缓存（需重新评审数据边界） |
| 代码索引 / 向量检索 | 后续独立需求 | 另立 spec；本 spec 的元数据与读取审计可作为输入，但不在本期建索引、不克隆仓库 |

> 未安装任何 AlonWorkflow pack（`.aw/install.json` 的 `packs` 为空），未套用 pack 专属约定；如需 React/.NET 等 pack 约定，可 `alonwf pack add <pack>` 后重跑本阶段。
