# Change Spec — knowledge-base

涉及本体：无（本 spec 无 `ontology-slices/tech-design.md`，编号沿用 `_handoff/from-workbench-core.md` 的 ENT-C10 / ENT-C11 / BR-C15 ~ BR-C20 / BP-C5 ~ BP-C8 / TERM-C10 ~ TERM-C12，均标注「对应图谱：未覆盖」）。

> 阶段：tech-design（步骤 4~6）。上游：`docs/architecture-decisions.md`（ADR-101 ~ ADR-118，`architecture-locked`）、`requirements-analysis/docs/context.md`、`interaction-design/docs/context.md`、`_handoff/from-tech-arch.md`。
> 本文件列本 spec 要写/改的文件与关键函数签名；知识库文档进暂存区 `technical-design/docs/`，`kb-sync` 提升时由编排者合并到 `docs/knowledge-base/`。
> 路径对齐说明（两处不改变已确认决策，只按 core 实际布局落地）：ADR-113 的 `frontend/src/knowledge/` 对应 core 既有前端根 `web/src/`，落地为 `web/src/features/knowledge/`；ADR-102 的 `src/workbench/knowledge/` 与 `src/workbench/services/knowledge/` 保持原名。本 spec 不改写任何 core ADR。

## 1. 改动文件

### 1.1 新增 — 后端（解析层，纯函数）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/knowledge/__init__.py` | 新增 | 包导出：`parse_index`、`match_bodies`、`derive_name`、`render_injection`、`KbSettings` |
| `src/workbench/knowledge/config.py` | 新增 | `KbSettings(BaseSettings, env_prefix="AW_KB_")` 与单例 `get_kb_settings()`；11 个 `AW_KB_*` 阈值（ADR-115）。`AW_PROMPT_MAX_CHARS` **不在此定义**，从 `workbench.config.get_settings()` 读取 |
| `src/workbench/knowledge/types.py` | 新增 | `EntryType` 枚举、`PREFIX_TO_TYPE` 前缀映射（`TERM→term` … `DE→domain_event`，其余 `other`）、`ParsedEntry` / `ParsedIndex` / `BodyMatchResult` / `ImportReport` 数据类 |
| `src/workbench/knowledge/index_parser.py` | 新增 | `parse_index()`：最小结构校验、前缀映射、条目级校验与跳过报告、深度/条目数/邻居/extras 护栏、生成时间与新鲜度解析 |
| `src/workbench/knowledge/body_matcher.py` | 新增 | `match_bodies()`：文件名优先 + `^### (\S+)\s*$` 切块、重复取「文件名升序 + 偏移最小」、未匹配文件与重复正文记报告 |
| `src/workbench/knowledge/naming.py` | 新增 | `derive_name()` 六级推导 + `name_key()`（`casefold(trim(name))`） |
| `src/workbench/knowledge/rendering.py` | 新增 | `render_injection()`：注入模板与 Unicode 码点计数（ADR-109），前端不共享此实现但按同一模板镜像 |
| `src/workbench/knowledge/errors.py` | 新增 | `KbDomainError` 及 `KnowledgeInvalidEntriesError` / `KnowledgeInjectionEmptyError` / `PromptBudgetExceededError` / `IndexJsonError` 等；只带错误码、计数、编号与行号，**不携带正文**（ADR-114） |

### 1.2 新增 — 后端（数据层与服务层）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/db/models/knowledge_base.py` | 新增 | `KnowledgeBase` ORM（2 表见 `docs/database-schema.md`） |
| `src/workbench/db/models/knowledge_entry.py` | 新增 | `KnowledgeEntry` ORM |
| `src/workbench/db/repositories/knowledge.py` | 新增 | `KnowledgeRepository`：版本行锁与取号、当前版本查询、条目批量读写、检索与分页、冲突批量查询、删除逻辑库 |
| `src/workbench/adapters/fs/knowledge_storage.py` | 新增 | `KbStorage`：`.staging/` 流式写入、`sha256[:16]__slug` 命名、`resolve()` 包含校验、原子 `rename`、`.trash/` 清理、孤儿目录扫描 |
| `src/workbench/services/knowledge/import_service.py` | 新增 | `KnowledgeImportService.import_files()`：限额校验 → 暂存写盘 → 解析 → 取版本号 → rename → 单事务落库；失败整体回滚（ADR-105） |
| `src/workbench/services/knowledge/query_service.py` | 新增 | `KnowledgeQueryService`：知识库列表/详情/版本、条目浏览/检索/详情、冲突与新鲜度徽标、注入候选 |
| `src/workbench/services/knowledge/injection_service.py` | 新增 | `KnowledgeInjectionService`：`preview()` / `prepare_for_call()`（实现 core `InjectionPreparer` 协议，ADR-110 / ADR-112） |
| `src/workbench/services/knowledge/lifecycle_service.py` | 新增 | `KnowledgeLifecycleService.delete_logical()`：删全部版本 + 条目级联 + 目录移入 `.trash/`（ADR-117） |
| `src/workbench/services/knowledge/registration.py` | 新增 | `install_injection_preparer(app)`：把本服务注册到 core 的 `core/ports.py`，供 `/ai/complete` 调用 |
| `src/workbench/api/schemas/knowledge.py` | 新增 | 请求/响应 Pydantic 模型（camelCase 输出，ID 为字符串） |
| `src/workbench/api/v1/knowledge_bases.py` | 新增 | 端点 1~5（导入、列表、详情、版本、删除） |
| `src/workbench/api/v1/knowledge_entries.py` | 新增 | 端点 6~8（全局检索、库内条目、条目详情） |
| `src/workbench/api/v1/knowledge_injection.py` | 新增 | 端点 9~10（注入候选、注入预览） |
| `migrations/versions/0007_knowledge_base.py` | 新增 | 建 `knowledge_base` / `knowledge_entry`，`down_revision = "0006"`；不建指向 core 业务表的外键，不改 core 表 |

### 1.3 新增 — 前端（`web/src/features/knowledge/`）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `api/types.ts` | 新增 | 与 `docs/api-spec.md` 一致的 TS 类型（kbId/entryId 为 `string`，projectId 为 `number`） |
| `api/client.ts` | 新增 | 复用 `lib/api/client.ts` 的 fetch 封装；`preview` 用 `refs/userPrompt`，`/ai/complete` 用 `knowledgeRefs/confirmInvalidCodes` 的转换函数 `toKnowledgeRefs()` |
| `api/keys.ts` | 新增 | TanStack Query key 工厂 |
| `routes.tsx` | 新增 | 4 条路由：`/knowledge-bases`、`/knowledge-bases/import`、`/knowledge-bases/:kbId`、`/knowledge-bases/:kbId/entries/:code` |
| `pages/*.tsx` | 新增 | `KnowledgeBaseListPage` / `KnowledgeImportPage` / `KnowledgeBrowsePage` / `KnowledgeEntryPage` |
| `components/*.tsx` | 新增 | 20 个组件，见 `docs/component-tree.md`；其中 `ProjectKnowledgeSummary` 由 core 项目上下文页通过 `data-mount="knowledge-summary"` 挂载，`KbInjectPicker` / `KbCharBudget` / `KbInvalidEntryDialog` 由 core 会话调用面板引用 |
| `hooks/*.ts` | 新增 | `useKnowledgeBases` / `useKnowledgeEntries` / `useEntryDetail` / `useImportKnowledge` / `useDeleteKnowledge` / `useInjectionCandidates` / `useInjectionPreview` |
| `index.ts` | 新增 | 导出 4 个页面 + 3 个嵌入组件 + 路由，供 core 的 `router.tsx` 与两个挂载点引用 |

### 1.4 修改 — 与 core 的接入点（最小改动）

| 文件 | 改动类型 | 改什么 |
|------|---------|--------|
| `src/workbench/api/v1/router.py` | 修改 | 挂载 `knowledge_bases` / `knowledge_entries` / `knowledge_injection` 三个 router（均依赖 `require_session`） |
| `src/workbench/main.py` | 修改 | `create_app()` 内调用 `install_injection_preparer(app)`；启动生命周期追加孤儿目录扫描（mtime > 1h） |
| `src/workbench/config.py` | 修改 | **不改** `Settings` 字段；仅在 `get_kb_settings()` 需要时已从 `AW_KB_*` 独立读取（零改动，本行留作核对） |
| `web/src/router.tsx` | 修改 | 追加 `/knowledge-bases/*` 4 条路由（在 `AuthGate` 内） |
| `web/src/app/AppShell.tsx` | 修改 | 「基座管理」分组下追加「知识库」入口（沿用现有 nav item 结构） |
| `web/src/features/projects/ProjectContextPage.tsx` | 修改 | 在既有 `data-mount="knowledge-summary"` 挂载位渲染 `<ProjectKnowledgeSummary projectId={...} />` |
| `web/src/features/calls/CallPanel.tsx` | 修改 | 嵌入 `<KbInjectPicker>` + `<KbCharBudget>` + `<KbInvalidEntryDialog>`；提交时把 `refs` 转成 `knowledgeRefs`，409 `knowledge_invalid_entries` 时打开阻塞确认，确认后带 `confirmInvalidCodes` 重试，取消则不发请求 |
| `scripts/backup.sh` | 修改 | 打包范围追加 `knowledge-bases/`；恢复后按 `manifest.json` 核对 sha256（ADR-105） |

### 1.5 新增 — 测试

`tests/test_kb_*.py` 13 个文件，用例名带 TC 编号（`test_tc101_*`），详见 `docs/test-strategy.md`；不新增测试依赖。

## 2. 关键函数签名

### 2.1 解析层（纯函数，无 DB / 无 IO）

- `parse_index(raw: bytes, *, settings: KbSettings) -> ParsedIndex`：校验最小结构、按前缀映射类型、条目级跳过并生成 `ImportReport`，超护栏抛 `IndexJsonError`。
- `match_bodies(codes: Sequence[str], files: Sequence[tuple[str, bytes]]) -> BodyMatchResult`：返回 `{code: (text, file_name)}`、`duplicate_bodies`、`unmatched_files`。
- `derive_name(explicit: str | None, index_meta: Mapping[str, Any], index_sha256: str) -> str`：六级推导，trim 后 ≤200。
- `name_key(name: str) -> str`：`casefold(trim(name))`。
- `render_injection(items: Sequence[InjectionItem], user_prompt: str, *, limit: int) -> PreparedInjection`：固定模板 + Unicode 码点计数；`text == injection_block + user_prompt`，`total_chars == len(text)`。

### 2.2 服务层

```python
class KnowledgeImportService:
    async def import_files(
        self, *, project_id: int, name: str | None,
        files: Sequence[UploadedFile],
    ) -> ImportResult: ...            # 201；任一步失败抛 KbDomainError 并清理 staging

class KnowledgeQueryService:
    async def list_bases(self, *, project_id: int | None, include_superseded: bool,
                         limit: int, cursor: str | None) -> Page[KnowledgeBaseSummary]: ...
    async def get_base(self, kb_id: str) -> KnowledgeBaseDetail: ...
    async def list_versions(self, kb_id: str) -> list[KnowledgeBaseVersion]: ...
    async def search_entries(self, *, project_id: int | None, kb_id: str | None,
                             entry_type: str | None, q: str | None,
                             include_superseded: bool, limit: int,
                             cursor: str | None) -> EntryPage: ...   # 含 countsByType / total
    async def get_entry(self, entry_id: str) -> KnowledgeEntryDetail: ...
    async def injection_candidates(self, *, session_id: str, q: str | None,
                                   entry_type: str | None, limit: int,
                                   cursor: str | None) -> EntryPage: ...

class KnowledgeInjectionService:            # 实现 core.ports.InjectionPreparer
    async def preview(
        self, *, project_id: int, refs: Sequence[KbEntryRef],
        user_prompt: str,
    ) -> PreparedInjection: ...             # 不抛失效/预算错误，返回 over_limit 与 invalid_items

    async def prepare_for_call(
        self, *, session_id: str, project_id: int, prompt: str,
        refs: Sequence[KbEntryRef],
        confirm_invalid_codes: Sequence[KbEntryRef] = (),
    ) -> PreparedInjection: ...             # 失效集非空且未精确确认 → KnowledgeInvalidEntriesError
                                            # 确认后有效集为空 → KnowledgeInjectionEmptyError
                                            # 超预算 → PromptBudgetExceededError（不截断）

class KnowledgeLifecycleService:
    async def delete_logical(self, *, project_id: int, kb_id: str) -> None: ...
```

### 2.3 数据传输对象

```python
@dataclass(frozen=True)
class KbEntryRef:                 # 扁平引用，内部与 preview 使用
    kb_id: str
    code: str

@dataclass(frozen=True)
class InjectionItem:
    kb_id: str; kb_name: str; kb_version: int
    code: str; title: str; chars: int
    source: Literal["body", "summary"]

@dataclass(frozen=True)
class InvalidItem:
    kb_id: str; code: str
    reason: Literal["kb_deleted", "entry_not_found", "superseded"]

@dataclass(frozen=True)
class PreparedInjection:
    text: str                     # 注入块 + 用户提示，可直接交给 AiGateway.complete
    injection_block: str          # 仅注入块（前端展示与测试基线）
    prompt_chars: int
    injected_chars: int           # 含块尾分隔符，保证 total_chars == len(text)
    total_chars: int
    limit: int
    items: tuple[InjectionItem, ...]
    invalid_items: tuple[InvalidItem, ...]   # 确定性排序 (kb_id, code)
    warnings: tuple[InjectionWarning, ...]   # stale / conflict，只提示
    over_limit: bool
    snapshot: InjectionSnapshot   # core.ports.InjectionSnapshot，只含标识与字符数
```

### 2.4 与 core 的进程内契约

- core 的 `POST /api/v1/sessions/{sessionId}/ai/complete` 在调用 `AiGateway` 前调用 `prepare_for_call(...)`，把 `knowledgeRefs: [{kbId, entryCodes[]}]` 展平为 `[KbEntryRef(kb_id, code)]`，把 `confirmInvalidCodes: [{kbId, code}]` 原样映射；`session_id` 与 `project_id` 从会话行取得。
- 返回的 `PreparedInjection.text` 作为 `AiGateway.complete(..., prepared=text, injection=snapshot)` 的 `prepared` 实参；`total_chars` 必须等于 `len(text)`，否则 core 返回 400 `injection_snapshot_mismatch`。
- 域错误映射（由 core 完成）：`KnowledgeInvalidEntriesError` → 409 `knowledge_invalid_entries`（`details.invalidItems=[{kbId, code, reason}]`）；`KnowledgeInjectionEmptyError` → 409 `knowledge_injection_empty`；`PromptBudgetExceededError` → 400 `prompt_budget_exceeded`（`details={promptChars, injectedChars, totalChars, limit}`）。三者都在发起外部请求前抛出，不写 AiCallRecord。
- 注册：`core/ports.py` 暴露 `InjectionPreparer` 协议与注册点；本 spec 的 `install_injection_preparer()` 在 `create_app()` 中把 `KnowledgeInjectionService` 注册进去。core 未注册时携带 `knowledgeRefs` 返回 409 `knowledge_unavailable`（core 侧行为）。

## 3. 不改动的部分

- core 的冻结签名：`AiGateway.complete`（仅按 A102 追加 keyword-only `injection`）、`sessions.create` / `append_event`、`artifacts.save`；本 spec 不改其语义。
- core 的表结构：`ai_call_record` 四列与 `session_event.type` 扩展归 core 的 `0006`；本 spec 不建、不改、不加外键，只读调用记录。
- `AW_PROMPT_MAX_CHARS`（200,000）：由 core `src/workbench/core/constants.py` 单点定义，本 spec 只读取。
- 本体生成、仓库集成、AI 网关、凭证加密、登录与访问控制、AppShell 与设计 token：全部保持 core 现状；不新增 design token、不新增第三方依赖。
- 制品的落盘根与限额：知识库只用 `$AW_DATA_DIR/knowledge-bases/` 与 `.trash/`，不复用 `sessions/`。
