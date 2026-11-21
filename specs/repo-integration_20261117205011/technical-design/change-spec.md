# Change Spec — repo-integration

涉及本体：无（本 spec 无 `ontology-slices/tech-design.md`，项目尚无 `ontology-work/views/index.json`）。编号沿用 `_shared/ontology/` 的 ENT-C12 ~ ENT-C15、BR-C21 ~ BR-C27、BP-C9 ~ BP-C11、TERM-C14 ~ TERM-C16，均标注「对应图谱：未覆盖」。

> 阶段：tech-design（步骤 4~6）。上游：`technical-design/design.md`（tech-arch，architecture-locked）、`technical-design/docs/architecture-decisions.md`（ADR-201 ~ ADR-217）、`requirements-analysis/docs/context.md`（7 US / 36 AC / 11 EARS）、`interaction-design/docs/context.md`（已确认）。
> 本文件列本 spec 要新增/改动的文件与关键函数签名；落地代码路径以仓库现状为准。
> **路径对齐（不改变已确认 ADR）**：ADR-202 的前端路径 `frontend/src/repos/` 对应 core 既有前端根 `web/src/`，落地为 `web/src/features/repos/`；ADR-202 的后端 `src/workbench/repos/` 与 `src/workbench/services/repos/` 保持原名。ADR-202 的 `src/workbench/api/v1/repos*` 落地为 `repo_bindings.py` + `repo_browse.py`。本 spec 不改写任何 core ADR。

## 1. 改动文件

### 1.1 新增 — 后端基座（纯逻辑，无 DB / 无网络）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/repos/__init__.py` | 新增 | 包导出：`RepoProvider`、`ProviderError`、归一化 DTO、常量 |
| `src/workbench/repos/constants.py` | 新增 | `REPO_FILE_MAX_BYTES=1_048_576`、`REPO_COMMIT_LIMIT=100`、`REPO_CONNECT_TIMEOUT_SECONDS=10`、`REPO_HTTP_TIMEOUT_SECONDS=15`、`REPO_SYNC_BUDGET_SECONDS=120`、`REPO_SYNC_LOCK_TTL_SECONDS=900`、`REPO_PAGE_DEFAULT=30`、`REPO_PAGE_MAX=100`、`REPO_TREE_PAGE_LIMIT=100`、`REPO_METADATA_MAX_BYTES=5_242_880`、`REPO_SYNC_MAX_PAGES=200`（自设页数护栏，非供应商事实） |
| `src/workbench/repos/types.py` | 新增 | `RepoProviderName`、`BindingStatus`、`TestResult`、`ErrorCategory`、`TreeEntryType`；DTO：`RepositorySummary`、`BranchSummary`、`CommitSummary`、`TreeEntry`、`TreePage`、`FileContent`、`Page[T]`；`RepoRef` / `RepositoryRef`；`ProviderError` |
| `src/workbench/repos/errors.py` | 新增 | 领域错误族：`RepoDomainError(DomainError)`、`RepoValidationError`、`RepoProviderError`（把 `ProviderError` 映射为固定码/状态）、`RepoConcurrencyError`；错误只带分类、状态码、可重试时间，不带请求头/令牌/响应原文 |
| `src/workbench/repos/validation.py` | 新增 | `parse_repo_identifier()`、`validate_repo_path()`、`validate_ref()`、`validate_api_base_url()`、`validate_search()`、`normalize_repo_key()` |
| `src/workbench/repos/crypto.py` | 新增 | `encrypt_token()` / `decrypt_token()` / `mask_token()`：算法与 `v1:<nonce>:<ciphertext>` 格式复用 `workbench.core.crypto`，密钥由 `AW_REPO_TOKEN_KEY` 提供，禁止回落到 `AW_ENCRYPTION_KEY` |
| `src/workbench/repos/cursor.py` | 新增 | `encode_page_cursor()` / `decode_page_cursor()`：base64url(JSON) + HMAC-SHA256(16B)；游标含 `bindingId`、`provider`、`repoKey`、`ref`、`path`、检索词指纹、页码 |
| `src/workbench/repos/ssrf.py` | 新增 | `assert_public_https_origin(url)`：仅 `https`、仅 origin、仅 443；解析 A/AAAA 并拒绝私网/回环/链路本地/保留地址；GitHub 固定 `https://api.github.com` |
| `src/workbench/repos/redaction.py` | 新增 | `redact_provider_exception()` / `safe_log_fields()`：只保留 provider、bindingId、repoKey、statusCode、category |

### 1.2 新增 — 供应商适配器（出站 HTTP）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/repos/providers/__init__.py` | 新增 | `build_provider(binding) -> RepoProvider` 注册表；`yunxiao` / `github` 两个实现 |
| `src/workbench/repos/providers/base.py` | 新增 | `RepoProvider` 协议（async，六方法）；`BaseProvider`：持有 `httpx.AsyncClient(follow_redirects=False, max_retries=0)`、统一读响应头、`_classify(status, headers, body)` → `ProviderError`、`_bounded_json()`（5 MiB 上限）、`_bounded_stream()`（1 MiB+1） |
| `src/workbench/repos/providers/github.py` | 新增 | `GitHubProvider`：`/user/repos`、`/repos/{owner}/{repo}`、`/branches`、`/commits`、`/contents/{path}`（目录列表即 tree）、contents 单文件；解析 `Link rel="next"`、`x-ratelimit-*`、`retry-after`、`GitHub-Authentication-Token-Expiration` |
| `src/workbench/repos/providers/yunxiao.py` | 新增 | `YunxiaoProvider`：`/organizations/{orgId}/repositories`、`/repositories/{repoId}`、`/branches`、`/commits`、`/files/tree`、`/files/blobs`；解析 `x-page`/`x-per-page`/`x-next-page`/`x-total`/`x-total-pages`；中心站/地域站两种路径形态 |

### 1.3 新增 — 数据层

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/db/models/repo_binding.py` | 新增 | `RepoBinding` ORM（表 `repo_binding`，见 `docs/database-schema.md` §2.1） |
| `src/workbench/db/models/repo_sync_record.py` | 新增 | `RepoSyncRecord` ORM（表 `repo_sync_record`） |
| `src/workbench/db/models/repo_metadata_snapshot.py` | 新增 | `RepoMetadataSnapshot` ORM（表 `repo_metadata_snapshot`） |
| `src/workbench/db/models/repo_file_read_record.py` | 新增 | `RepoFileReadRecord` ORM（表 `repo_file_read_record`） |
| `src/workbench/db/models/__init__.py` | 修改 | 导入四个新模型，保证 `Base.metadata` 与 Alembic autogenerate 可见 |
| `src/workbench/db/repositories/repos.py` | 新增 | `RepoRepository`：绑定 CRUD/唯一性、同步 claim 与释放、快照单事务覆盖、同步记录分页、读取审计写入、baseline 查询 |
| `migrations/versions/0008_repo_integration.py` | 新增 | 建四张表；`revision="0008"`、`down_revision="0007"`；不建指向 core 业务表之外的依赖 |

### 1.4 新增 — 服务层

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/services/repos/__init__.py` | 新增 | 导出五个服务与序列化函数 |
| `src/workbench/services/repos/binding_service.py` | 新增 | `RepoBindingService`：创建/列表/详情/更新令牌/解绑；唯一性、加密、掩码、状态机 |
| `src/workbench/services/repos/connectivity_service.py` | 新增 | `RepoConnectivityService`：已保存/未保存测试；10s 预算；四类结果；仅已保存绑定落库 |
| `src/workbench/services/repos/sync_service.py` | 新增 | `RepoSyncService`：claim、拉仓库/全部分支/最近 100 提交、单事务覆盖、记录与失败保留 |
| `src/workbench/services/repos/browse_service.py` | 新增 | `RepoBrowseService`：实时仓库/分支/提交/目录树；分页游标；`truncated`/`hasMore`；baseline |
| `src/workbench/services/repos/file_service.py` | 新增 | `RepoFileService`：路径/ref 前置校验、大小/编码、审计、拒绝分类 |
| `src/workbench/services/repos/serializers.py` | 新增 | ORM → API camelCase DTO；密文列永不进入 DTO；时间 RFC 3339 |
| `src/workbench/services/repos/registration.py` | 新增 | `install_repo_services(app)`：向 `app.state` 注册 provider 工厂与服务，供跨域只读调用 |

### 1.5 新增 — API 层

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/api/schemas/repo.py` | 新增 | 请求/响应 Pydantic 模型（camelCase 输出；`bindingId` 字符串、`projectId` number） |
| `src/workbench/api/v1/repo_bindings.py` | 新增 | 端点 1~9：绑定列表/创建/详情、更新令牌、已保存测试、未保存测试、同步、同步记录、解绑 |
| `src/workbench/api/v1/repo_browse.py` | 新增 | 端点 10~15：repositories / branches / commits / tree / file / baseline |
| `src/workbench/api/v1/router.py` | 修改 | 挂载两个 router（沿用 core 全局 `require_session` 中间件与 `require_same_origin`） |

### 1.6 新增 — 前端（`web/src/features/repos/`）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `api/types.ts` | 新增 | 与 `docs/api-spec.md` 一致的 TS 类型；`projectId: number`、`bindingId: string` |
| `api/client.ts` | 新增 | 复用 `lib/api/client.ts` 的 `apiFetch`；封装 15 个端点与 `queryString` |
| `api/keys.ts` | 新增 | TanStack Query key 工厂（bindings / syncRecords / browse / tree / file / baseline） |
| `hooks/*.ts` | 新增 | `useRepoBindings` / `useRepoBinding` / `useCreateRepoBinding` / `useUpdateRepoToken` / `useTestRepoConnection` / `useSyncRepo` / `useSyncRecords` / `useUnbindRepo` / `useRepositories` / `useBranches` / `useCommits` / `useRepoTree` / `useRepoFile` / `useRepoBaseline` |
| `pages/RepoBrowsePage.tsx` | 新增 | 独立浏览路由页：绑定摘要 + 选择器 + 目录树 + 提交 + 文件抽屉 + 已解绑只读态 |
| `components/*.tsx` | 新增 | 26 个组件，见 `docs/component-tree.md`；含 `RepoBindingPanel`（`data-mount="repo-binding-panel"`）、`RepoBindingForm`、`RepoBindingRow`、`SyntaxPane`、`UnbindDialog` |
| `routes.tsx` | 新增 | 1 条路由：`/projects/:projectId/repos/:bindingId`（在 core `AuthGate` 内） |
| `index.ts` | 新增 | 导出页面、嵌入组件与路由 |

### 1.7 修改 — 与 core / 既有工程的接入点（最小改动）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/config.py` | 修改 | 新增 `repo_token_key: SecretStr \| None`（`AW_REPO_TOKEN_KEY`）；启动校验 32 字节 base64；提供 `repo_token_key_bytes` |
| `src/workbench/startup.py` | 修改 | 启动自检追加：`AW_REPO_TOKEN_KEY` 存在/合法、Alembic head 包含 `0008`；失败拒绝启动 |
| `src/workbench/main.py` | 修改 | `create_app()` 调 `install_repo_services(app)`；注册 provider 工厂与两个服务 |
| `pyproject.toml` | 修改 | 把 `httpx` 从 dev 组提升为运行时依赖（`httpx>=0.28,<0.29`，与 dev 同范围，不升级版本）；不新增其它依赖 |
| `web/src/router.tsx` | 修改 | 追加 `/projects/:projectId/repos/:bindingId` 路由 |
| `web/src/app/AppShell.tsx` | 修改 | 「基座管理」分组追加「仓库浏览」入口 |
| `web/src/features/projects/ProjectsPage.tsx` | 修改 | 在项目详情表单下方渲染 `<RepoBindingPanel projectId={...} />`，挂载位 `data-mount="repo-binding-panel"` |
| `web/src/features/providers/ConnectionTestBadge.tsx` | 修改 | 增量扩展 `permission-denied` 与 `stale` 两个状态；不改既有 `auth-error` / `unreachable` / `timeout` 语义 |
| `web/src/features/projects/ProjectForm.tsx` | 修改 | 「仓库地址」字段降级为自由备注，hint 改为「人工备注，实际拉取以下方「仓库绑定」为准（AMB-030）」；字段仍按 core 语义保存，不参与仓库请求 |

### 1.8 新增 — 测试

`tests/test_repo_*.py` 约 16 个文件，用例名带 TC 编号（`test_tc201_*`），详见 `docs/test-strategy.md`；前端测试放 `web/src/features/repos/*.test.tsx` 与 `web/e2e/repo.spec.ts`。不新增测试依赖（`httpx.MockTransport` 已在 dev 依赖中）。

## 2. 关键函数签名

### 2.1 适配器协议与 DTO

```python
class RepoProvider(Protocol):
    name: RepoProviderName
    async def list_repositories(self, *, search: str | None, cursor: str | None,
                                limit: int) -> Page[RepositorySummary]: ...
    async def get_repository(self, repo: RepositoryRef) -> RepositorySummary: ...
    async def list_branches(self, repo: RepositoryRef, *, search: str | None,
                            cursor: str | None, limit: int) -> Page[BranchSummary]: ...
    async def list_commits(self, repo: RepositoryRef, *, ref: str,
                           cursor: str | None, limit: int) -> Page[CommitSummary]: ...
    async def list_tree(self, repo: RepositoryRef, *, ref: str, path: str,
                        cursor: str | None, limit: int) -> TreePage: ...
    async def read_file(self, repo: RepositoryRef, *, ref: str,
                        path: str) -> FileContent: ...

@dataclass(frozen=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    next_cursor: str | None = None
    total: int | None = None

@dataclass(frozen=True)
class TreePage:
    path: str
    ref: str
    entries: tuple[TreeEntry, ...]
    truncated: bool = False
    has_more: bool = False
    next_cursor: str | None = None
    total: int | None = None

@dataclass(frozen=True)
class ProviderError(Exception):
    category: Literal["auth", "permission_denied", "rate_limited", "not_found",
                      "network", "timeout", "server_error", "invalid_response"]
    status_code: int | None = None
    retry_after_at: datetime | None = None
    message: str = ""              # 固定可读文案，不含供应商原文
```

### 2.2 服务层

```python
class RepoBindingService:
    async def list(self, *, project_id: int, limit: int,
                   cursor: str | None) -> Page[RepoBindingSummary]: ...
    async def create(self, *, project_id: int, provider: str, repo_identifier: str,
                     org_id: str | None, api_base_url: str | None,
                     token: str) -> RepoBindingSummary: ...      # 201；重复 → 409
    async def get(self, binding_id: str) -> RepoBindingSummary: ...
    async def update_token(self, binding_id: str, *, token: str) -> RepoBindingSummary: ...
    async def unbind(self, binding_id: str) -> RepoBindingSummary: ...

class RepoConnectivityService:
    async def test_saved(self, binding_id: str) -> TestConnectionResult: ...
    async def test_unsaved(self, *, provider: str, repo_identifier: str,
                           org_id: str | None, api_base_url: str | None,
                           token: str) -> TestConnectionResult: ...   # 零落库

class RepoSyncService:
    async def sync(self, binding_id: str) -> SyncOutcome: ...     # 409 sync_in_progress

class RepoBrowseService:
    async def list_repositories(self, binding_id: str, *, search: str | None,
                                limit: int, cursor: str | None) -> BrowsePage[RepositorySummary]: ...
    async def list_branches(self, binding_id: str, *, repo_id: str | None,
                            search: str | None, limit: int,
                            cursor: str | None) -> BrowsePage[BranchSummary]: ...
    async def list_commits(self, binding_id: str, *, repo_id: str | None, ref: str,
                           limit: int, cursor: str | None) -> BrowsePage[CommitSummary]: ...
    async def list_tree(self, binding_id: str, *, repo_id: str | None, ref: str,
                        path: str, limit: int, cursor: str | None) -> TreePage: ...
    async def baseline(self, binding_id: str) -> BaselineView: ...

class RepoFileService:
    async def read(self, binding_id: str, *, repo_id: str | None, ref: str,
                   path: str) -> FileReadResult: ...
```

### 2.3 会话与生命周期守卫

- 所有服务入口先取绑定行：不存在 → `404 binding_not_found`；`status='revoked'` → `409 binding_revoked`（read/baseline 除外，baseline 允许读快照）。
- `sync_started_at` claim：`UPDATE repo_binding SET sync_started_at=:now WHERE binding_id=:id AND status!='revoked' AND (sync_started_at IS NULL OR sync_started_at < :now - TTL)`；`rowcount=0` → `409 sync_in_progress`，不写同步记录。
- 解密只发生在适配器调用前一瞬；`status='revoked'` 或 `token_ciphertext IS NULL` 时拒绝解密（`CredentialUnavailable` → 固定 `binding_revoked` / `token_required`）。
- 任何供应商异常先经 `BaseProvider._classify()` 转 `ProviderError`，再由服务层映射为 API 错误或测试结果；适配器不抛原始异常文本。

### 2.4 四张表（详见 `docs/database-schema.md`）

| 表 | 一行含义 | 关键列 | 保留/级联 |
|----|---------|--------|-----------|
| `repo_binding` | 项目 × 供应商 × 仓库的只读绑定 | `binding_id` PK、`project_id` FK RESTRICT、`provider`、`repo_key`、`token_ciphertext`、`token_masked`、`status`、`active_flag`、`last_*` 同步/测试摘要、`sync_started_at` | 解绑不删行：`status='revoked'`、`active_flag=NULL`、密文与掩码清空 |
| `repo_sync_record` | 一次手动同步 | `sync_id` PK、`binding_id` FK CASCADE、`status`、`duration_ms`、`repo/branch/commit_count`、`error_category`、`retry_after_at` | 失败也写失败记录；解绑保留 |
| `repo_metadata_snapshot` | 同步基线的一行（仓库/分支/提交） | `snapshot_id` PK、`binding_id` FK CASCADE、`kind`、`ref`、`payload JSON`、`fetched_at`、`truncated` | 每次成功同步单事务全量替换；解绑保留只读 |
| `repo_file_read_record` | 一次按需读取审计 | `read_id` PK、`binding_id` FK CASCADE、`ref`、`file_path`、`byte_size`、`encoding`、`status`、`reject_reason` | 只存元数据，不存正文；解绑保留 |

唯一性：`UNIQUE(project_id, provider, repo_key, active_flag)`；在绑 `active_flag='1'`、解绑 `NULL`，两方言均允许多个 `NULL`，支持重新绑定生成新行（AC-017-3 / AC-023-6）。

## 3. 不改动的部分

- core 冻结契约：`require_session`、错误体 `{code,message,details[],requestId}`、`limit`+`cursor` 分页、`AW_PROMPT_MAX_CHARS=200000`、`workbench.core.crypto` 的算法与密文格式、`workbench.core.redaction` 的日志出口。
- core 的表：`project_context` / `session_event` / `artifact` / `ai_call_record` 等；本 spec 只加 `project_id` 外键，不改 core 表。
- knowledge-base 的 `0007`：本 spec 不创建、不修改，只把 `0008.down_revision` 指向它。
- 不新增：消息队列、定时任务、后台轮询、第二套 HTTP 栈、第二套认证、前端全局状态库、设计 token（仅追加 interaction-design 的 3 个 token）。
- 不落盘：文件正文、目录树整树、供应商原始响应；只写四张表与结构化审计元数据。

## 4. 路径对齐、ADR 偏差与开放问题

### 4.1 路径对齐（只记录，不改 ADR）

| ADR 原文 | 实际落地 | 说明 |
|----------|---------|------|
| `frontend/src/repos/`（ADR-202 / ADR-214） | `web/src/features/repos/` | core 前端根是 `web/src/`，`features/<domain>/` 是既有约定（knowledge-base 同法） |
| `src/workbench/api/v1/repos*`（ADR-202） | `repo_bindings.py` + `repo_browse.py` | 按端点域拆两个文件，路由前缀不变 |
| `src/workbench/repos/providers/{github,yunxiao}.py`（design.md） | 保留，增加 `base.py` / `__init__.py` | 便于共用错误映射与响应头上限 |

### 4.2 ADR 偏差（需用户拍板，本期按 ADR 执行）

1. **云效目录树分页**：ADR-209 写「云效按 `x-total` 与返回条数判断」，但官方 `ListFiles` 无 `page`/`perPage`/`x-total`。本期实现：云效 `hasMore=false`、`nextCursor=null`、`truncated=false`；若响应可能被上游截断，只在适配器内按固定上限记录 `truncated=true`，不伪造分页。建议后续修订 ADR-209 的云效分支。
2. **404 语义**：ADR-206 把「404（读仓库/分支/文件）」统一归 `not_found` → 测试「权限不足」→ 绑定置 `token_invalid`。对「文件路径不存在」这会把有效令牌误标失效。本期按 ADR 执行（文件 404 也返回 `502 provider_permission_denied`、不改更细状态），在 UI 文案上区分「文件不存在或无权访问」；建议 ADR-206 增补「文件路径 404 不改变绑定状态」。
3. **`repo_not_synced` 错误码**：ADR-212 列出 409 `repo_not_synced`，但 ADR-208 / AC-020-3 要求未同步浏览返回 `200 {metadataSynced:false, items:[], guide:"sync_first"}`。本期不返回该码（保留为跨域调用方的预留码），未同步一律 200 空态。建议确认是否删除该码。

### 4.3 开放问题（需用户拍板）

- **OQ-RI-01**：解绑后 `GET /baseline` 是否仍允许读（本期允许，`revoked=true` 只读）；跨域调用方是否也允许调 baseline（本期允许，仅 `baseline` 与 `file` 两个只读端点）。
- **OQ-RI-02**：文件路径 404 是否按 4.2-2 修订 ADR-206（本期按 ADR 执行，用户误标风险已知）。
- **OQ-RI-03**：`repo_not_synced` 保留还是删除（本期不返回）。
- **OQ-RI-04**：GitHub fine-grained PAT 的过期响应头是否与 classic PAT 同名（官方现行文档未单列；本期按同名容忍读取，缺失为 `null`）。
- **OQ-RI-05**：同步前是否强制要求绑定 `status='connected'`（AC-019-1 的 GIVEN 是「已连接」；本期允许 `unverified` 直接同步，成功后不自动置 `connected`，避免把同步当连通性测试）。
