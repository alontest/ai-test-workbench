# Tech Tasks — knowledge-base

> 阶段：tech-tasks。来源：`requirements-analysis/requirements.md`（5 US / 24 AC / 7 EARS，已确认）、`interaction-design/docs/`（已确认）、`technical-design/design.md`、`change-spec.md`、`docs/{api-spec,database-schema,architecture-decisions,component-tree,file-structure,test-strategy,flowchart}.md`（ADR-101 ~ ADR-118，architecture-locked）。
> 跨 spec 拍板（`technical-design/answers.md` 2026-11-18 11:23:18）：OQ-ARCH-101 A（core 落 `0006`）、102 A（`complete` 追加可选 `injection`）、103 B（复用 core 的 `/ai/complete`，不新增 calls 端点）。
> 任务格式对齐 `specs/ai-test-workbench_20261117184149/technical-design/tasks.md`；TC 编号占用 **TC-101 ~ TC-150**（core 已用 TC-001 ~ TC-071，repo-integration 计划 TC-201 起）。
> 代码基线：`src/workbench/`、`migrations/0001 ~ 0006`、`web/src/`、`tests/`（131 pytest / 62 vitest 全绿）。**文件位置与命名以代码为准**；与已锁定文档不一致处只在本文件「1. 路径对齐」记录，不改任何 ADR。
> 本文件是后续 aw-implementer 的唯一任务来源；任务状态统一 `pending`，实施时逐条勾选。

## 1. 路径对齐

> 只做「文档路径 → 仓库实际路径/签名」的落点核对，不改变已确认的 ADR 与需求口径。除第 6 条外均不影响范围。

| # | 文档写法 | 仓库实际 | 处理 | 影响任务 |
|---|---------|---------|------|---------|
| 1 | `design.md` 决策 2 / ADR-113 写 `frontend/src/knowledge/` | 前端根为 `web/src/`，页面按 `web/src/features/<域>/` 组织；仓库无 `frontend/` 目录 | 按 `change-spec.md` 与 `component-tree.md` 已对齐的 `web/src/features/knowledge/` 落地；不改 ADR-113 原文 | KB-015 ~ KB-018 |
| 2 | `change-spec.md` §1.4 写修改 `web/src/features/projects/ProjectContextPage.tsx` | 该文件不存在；项目上下文页实际是 `web/src/features/projects/ProjectsPage.tsx`，且已在第 47 行渲染空占位 `<ProjectKnowledgeSummary />`（`data-testid` / `data-mount="knowledge-summary"`，见 `ProjectKnowledgeSummary.tsx`） | 知识库侧新增 `web/src/features/knowledge/components/ProjectKnowledgeSummary.tsx`；把 `web/src/features/projects/ProjectKnowledgeSummary.tsx` 改为转发导出（或由 `ProjectsPage.tsx` 直接引用知识库组件），保留 `data-mount` 属性与现有占位用例 | KB-018 |
| 3 | `change-spec.md` §1.4 与 §2.4 写 `install_injection_preparer(app)`，`main.py` 内调用 | core 实际暴露 `src/workbench/core/ports.py::register_injection_preparer(impl)`（无 `app` 参数），并提供 `get_injection_preparer()`；`main.py` 目前无注册调用 | 新增 `registration.py::install_injection_preparer(app)` 作为薄包装，内部调用 core 的 `register_injection_preparer`；在 `create_app()` 完成 DB 装配后调用。不修改 core 的 Protocol 定义 | KB-013 |
| 4 | `change-spec.md` §2.2 / §2.4 写 `prepare_for_call(*, refs=..., confirm_invalid_codes=...)` 且返回本 spec 的 `PreparedInjection(text, ...)` | core `core/ports.py::InjectionPreparer` 的实参是 `knowledge_refs=`，返回 `core.ports.PreparedInjection(prepared: str, snapshot: InjectionSnapshot)`；`services/calls.py` 已按此调用 | 实现按 core 协议签名；本 spec 内部的 `PreparedInjection` 作为服务层结果，进入 core 前转换为 `core.ports.PreparedInjection`。转换函数写在 `registration.py` 或 `injection_service.py` | KB-012 / KB-013 |
| 5 | `design.md` §扩展计划与 `change-spec.md` §3 写 `AW_PROMPT_MAX_CHARS` 由 `core/constants.py` 定义 | 实际有 `src/workbench/config.py::Settings.prompt_max_chars`（默认 200000，受 `AW_PROMPT_MAX_CHARS` 覆盖）与 `core/constants.py::PROMPT_MAX_CHARS` 两个来源；`AiGateway` 使用 `settings.prompt_max_chars` | 统一读 `get_settings().prompt_max_chars`，保证环境变量覆盖与网关一致；不在知识库重复定义常量 | KB-001 / KB-012 |
| 6 | `database-schema.md` / `api-spec.md` 定义 `kbId` 为 `CHAR(32)` hex、JSON string；core 的 `api-spec.md` 示例与已实现代码用 number | 实际 code：`core/ports.py` 的 `InjectionItem.kb_id: int`、`KnowledgeRef.kb_id: int`、`InvalidCodeRef.kb_id: int`；`api/schemas/call.py` 的 `kb_id: int`；`services/calls.py::_as_knowledge_ref` 执行 `int(kb_id)`；但 `services/injection_snapshot.py` 又把 `knowledge_base.kb_id` 转成 `str` 比较 | **真阻塞项**：两套已确认文档的类型口径冲突，无法用实现层“兼容”同时成立。已记入 `open-questions.md` OQ-TD-04，批次 D 的联调与验收以该结论为前提；批次 A ~ C 不受影响 | KB-009 / KB-012 / KB-013 |
| 7 | `component-tree.md` §复用清单列出 `web/src/components/ui/` 的 15 个原语 | 原语均存在，但分散在 6 个模块：`Textarea` 在 `Input.tsx`，`EmptyState` / `ErrorState` / `Toast` 在 `Feedback.tsx`，`Spinner` / `Skeleton` 在 `Loading.tsx`，`StatusPill` 在 `Badge.tsx` | 按实际模块导入，不新建重复原语 | KB-016 ~ KB-018 |
| 8 | `change-spec.md` §1.4 写 `scripts/backup.sh` «打包范围追加 `knowledge-bases/`» | 现有脚本已 `tar -C "$AW_DATA_DIR" .` 整体打包（排除 `.trash/` / `.tmp/`），`knowledge-bases/` 天然包含 | 不新增打包路径；任务改为核对 `manifest.json` 的 sha256 恢复校验说明，并确认 `.trash/` 排除 | KB-018 |
| 9 | `change-spec.md` §1.2 新增两张 ORM 模型 | `src/workbench/db/models/__init__.py` 目前显式导入并注册 10 张表，测试 `Base.metadata.create_all` 依赖它 | 追加 `KnowledgeBase` / `KnowledgeEntry` 的导入与 `__all__`，否则测试建表缺表 | KB-005 |
| 10 | 组件数量口径：`design.md` 写 17 个组件、`change-spec.md` 写 20 个、`file-structure.md` 实际列 19 个组件文件 + 4 个页面 | 以 `file-structure.md` 的 19 个文件为实施清单；数量差异是文档统计口径不同，不改变范围 | 不新增/不删减组件 | KB-016 ~ KB-018 |

## 2. 批次划分

### 批次 A：解析层与数据层（TASK-KB-001 ~ TASK-KB-006）

目标：完成无 IO 的解析/渲染纯函数、两张表 ORM、仓储骨架与 `0007` 迁移。完成后导出、浏览、注入三个上层模块都有稳定依赖。

- 可并行：001 →（002 / 005 并行）→ 003 / 004；005 → 006。
- 出口条件：TC-101 ~ TC-110、TC-127、TC-128、TC-150 全绿；`alembic upgrade head` 在 SQLite 从空库到 `0007` 通过，`downgrade 0006` 再 `upgrade head` 通过；`Base.metadata.create_all` 含两张新表；解析层无 DB / 无文件系统导入。
- 本批次不暴露 HTTP 端点。

### 批次 B：导入闭环（TASK-KB-007 ~ TASK-KB-009）

目标：跑通「上传 → 校验 → 暂存 → 解析 → 版本化 → 落库 → 报告」，失败零残留。

- 依赖：批次 A 完成；007 → 008 → 009。
- 出口条件：TC-111 ~ TC-117、TC-145 全绿；导入失败路径断言「无目录、无行、无 staging」；同名重导 `version=2` 且旧版本 `superseded`；`POST /knowledge-bases` 返回 201 + 导入报告。

### 批次 C：浏览检索（TASK-KB-010 ~ TASK-KB-011）

目标：提供知识库列表/详情/版本、条目全局与库内浏览、编号/关键词检索、详情与徽标。

- 依赖：批次 A 完成；010 → 011（011 只做 HTTP 层与参数校验）。
- 出口条件：TC-118 ~ TC-126、TC-143 全绿；检索排序、`countsByType` 与游标翻页稳定；冲突查询 SQL 次数为常数；正文缺失返回 `body=null` + 摘要。

### 批次 D：注入与 core 嵌入（TASK-KB-012 ~ TASK-KB-014）

目标：实现注入预览、失效重校验、阻塞确认、字符预算与快照组装；把服务注册进 core 的 `InjectionPreparer`；完成删除生命周期。

- 依赖：批次 A + C 完成；012 → 013；012 与 014 可并行（014 另需 007、010）。
- 前置：OQ-TD-04（`kbId` 类型）必须先有结论，否则 013 的联调与验收阻塞；012/014 的业务逻辑可先按本 spec 的 `CHAR(32)` 实现。
- 出口条件：TC-129 ~ TC-142、TC-149 全绿；TC-136 证明经 core `/ai/complete` 的 409/400 路径不写 `AiCallRecord`、不调网关；确认后有效集为空 → 409；删除后历史记录不变且 `kbDeleted=true`。

### 批次 E：前端与验收（TASK-KB-015 ~ TASK-KB-018）

目标：4 条路由页面、7 个 hooks、19 个组件、3 个 core 嵌入组件与项目摘要挂载；完成手工端到端验收与备份核对。

- 依赖：批次 B/C/D 的 HTTP 契约稳定；015 →（016 / 017 并行）→ 018；013 与 018 的 CallPanel 接入同步。
- 出口条件：`cd web && npm run build` 通过；`npm run test -- --run` 全绿（按 `test-strategy.md` 为 P1 可选，不进门禁）；手工走通「导入 → 列表 → 浏览 → 会话勾选注入 → 409 确认 → 调用留痕 → 删除 → 历史标已删除」；`scripts/backup.sh` 产物包含 `knowledge-bases/` 且恢复说明可核对 `manifest.json`。
- 本批次前端用例标题沿用 TC 编号只作追溯，TC 结果仍由 pytest 提供。

### 依赖图

```text
001 ──► 002 ──► 003 ─┐
  │       └────► 004 ─┼──► 008 ──► 009 ──► 010 ──► 011 ─┐
  └──► 005 ──► 006 ──┘                     │              │
                 └──► 007 ─────────────────┘              │
                                            └──► 012 ──► 013 ──┐
                 005 + 007 + 010 ─────────────► 014 ────────────┼──► 018
                 009 ──► 015 ──► 016 / 017 ──────────────────────┘
```

## 3. 迁移链约束（写死）

- 本 spec 的首个且唯一迁移文件为 `migrations/versions/0007_knowledge_base.py`：
  - `revision = "0007"`
  - `down_revision = "0006"`（core 已落地的 `0006_knowledge_injection.py`）
- 只新增 `knowledge_base`、`knowledge_entry` 两张表；**不修改** core 的 10 张表，**不建**指向 `ai_call_record` / `session_event` 的外键。
- 升级顺序先父表 `knowledge_base`、再子表 `knowledge_entry`（`ON DELETE CASCADE`）；降级反序。
- 发布顺序固定：core `0006` → 本 spec `0007`。`0007` 不引用 `0006` 新增的列，因此代码可并行，但迁移不能乱序。
- 不在 `0007` 中写业务数据、不建方言专属 DDL、不对 JSON 列建索引。

## 4. 任务清单

- [ ] TASK-KB-001：实现知识库配置、类型与域错误
  - **描述**：集中声明 `AW_KB_*` 阈值与纯类型定义，建立只带错误码/数量/编号/行号的域错误族，供解析、导入、注入、生命周期共享。
  - **涉及文件**：`src/workbench/knowledge/__init__.py`、`src/workbench/knowledge/config.py`、`src/workbench/knowledge/types.py`、`src/workbench/knowledge/errors.py`、`tests/test_kb_config.py`
  - **具体操作**：`KbSettings(BaseSettings, env_prefix="AW_KB_")` 声明 11 项：`max_index_bytes=20MB`、`max_file_bytes=10MB`、`max_files=50`、`max_total_bytes=100MB`、`max_entries=20000`、`max_json_depth=32`、`max_neighbors=200`、`max_extras_bytes=65536`、`stale_days=30`、`conflict_sources=20`、`report_max_items=200`；`get_kb_settings()` 用 `lru_cache`，测试需可 `cache_clear()`；`AW_PROMPT_MAX_CHARS` 不在此定义，读 `workbench.config.get_settings().prompt_max_chars`。`EntryType` 枚举与 `PREFIX_TO_TYPE`：`TERM→term`、`ENT→entity`、`ST→state`、`BR→rule`、`BP→process`、`API→api`、`DE→domain_event`，其余 `other`。数据类 `ParsedEntry` / `ParsedIndex` / `BodyMatchResult` / `ImportReport`。错误族 `KbDomainError` 及 `IndexJsonError` / `KnowledgeInvalidEntriesError` / `KnowledgeInjectionEmptyError` / `PromptBudgetExceededError` 等，只承载 `code`、计数、编号与行号，**不携带正文**。用例 `test_tc146_kb_settings_defaults_and_overrides`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：无
  - **对应 AC**：AC-012-2、AC-REQ-18（限额与配置口径）
  - **TC**：TC-146
  - **估算**：5h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-002：实现 `index.json` 解析器与解析护栏
  - **描述**：把上传的 `index.json` 解析为结构化条目，完成最小结构校验、前缀映射、条目级跳过报告与资源护栏。
  - **涉及文件**：`src/workbench/knowledge/index_parser.py`、`tests/test_kb_index_parser.py`
  - **具体操作**：`parse_index(raw: bytes, *, settings: KbSettings) -> ParsedIndex`。校验 UTF-8；`json.loads(..., parse_constant=raise)` 拒绝 `NaN/Infinity`；捕获 `RecursionError`；解析后深度 ≤ `max_json_depth`。顶层必须为非空字符串 `schema` + 非空数组 `entries`，否则 `IndexJsonError`。编号必填、≤128、匹配 `^[\w一-鿿][\w一-鿿.\-]{0,127}$`；`fields` 必须对象、`tables` / `code_paths` 必须字符串数组；`code_key = casefold(code)`，重复保留首条。合法条目按前缀映射类型，记录标题（`zh_name` → `name` → 编号兜底）、摘要（`zh_definition` → `description` → `content`）、`fields`、`tables`、`code_paths`、`neighbors`（≤200，超出截断并记报告）、`extras`（规范 JSON >64KB 丢弃并记报告）、`source_doc`、`anchor`、`freshness_at`。生成时间取 `meta.source.exported_at` 或顶层 `generated_at`，非 ISO 8601 即 `None`。跳过项写 `skippedEntries[{index, line?, code?, reason}]`，行号尽力定位 `"id": "<code>"`，最多 `report_max_items` 条并标 `truncated`。全部条目被跳过 → `IndexJsonError`。异常消息不含原文。用例 `test_tc101_rejects_index_without_schema_or_entries`、`test_tc102_maps_prefix_to_entry_type`、`test_tc103_skips_invalid_entries_with_line_and_reason`、`test_tc104_fails_when_no_entry_importable`（纯函数部分）、`test_tc105_enforces_parser_guards`、`test_tc106_truncates_neighbors_and_drops_large_extras`、`test_tc107_rejects_invalid_json_syntax`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-001
  - **对应 AC**：AC-012-3、AC-012-4、AC-012-5、AC-REQ-18、AC-REQ-19
  - **TC**：TC-101 ~ TC-107
  - **估算**：12h [逻辑]，不确定性中（护栏边界与行号定位）
  - **状态**：pending

- [ ] TASK-KB-003：实现正文匹配与名称推导
  - **描述**：按文件名优先、`### CODE` 切块兜底的顺序把 `.md` 正文匹配到编号；按六级顺序推导知识库名并生成 `name_key`。
  - **涉及文件**：`src/workbench/knowledge/body_matcher.py`、`src/workbench/knowledge/naming.py`、`tests/test_kb_body_matcher.py`、`tests/test_kb_naming.py`
  - **具体操作**：`match_bodies(codes, files) -> BodyMatchResult`：文件名去扩展名 `casefold` 等于 `code_key` → 整文件为正文；否则逐行扫描 `^### (\S+)\s*$`，区块到下一条 `## ` / `### ` 或文件尾；同一编号多处命中取「文件名升序 + 偏移最小」，其余记 `duplicateBodies`；未命中任何编号的文件记 `unmatchedFiles`；正文去首尾空白后为空视为缺失。`derive_name(explicit, index_meta, index_sha256)` 顺序：表单名 → 顶层 `name` → `meta.name` → `meta.source.files[0].path` 父目录 → `知识库 <graph_fingerprint[:8]>` → `知识库 <sha256[:8]>`；trim 后 ≤200。`name_key(name) = casefold(trim(name))`。用例 `test_tc108_derives_name_in_fixed_order`、`test_tc109_matches_body_by_filename_then_heading`、`test_tc110_marks_missing_body_as_blank`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-KB-001
  - **对应 AC**：AC-012-1、AC-013-5、AC-REQ-19、AC-REQ-20
  - **TC**：TC-108、TC-109、TC-110
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-004：实现注入模板渲染与 Unicode 字符预算
  - **描述**：用固定模板把条目组装为注入块，返回分段字符数与最终文本；前端镜像同一模板，但服务端为唯一权威实现。
  - **涉及文件**：`src/workbench/knowledge/rendering.py`、`tests/test_kb_rendering.py`
  - **具体操作**：模板逐行固定：`【知识库上下文】` → 每库一行 `知识库：<name> v<version>（生成时间：<ISO8601|未知>）` → 每条 `### <code> <title>` + 正文；正文缺失时用摘要并追加 `（正文缺失）`。字符口径 `len()`（Unicode 码点，换行与空格计入）；`injected_chars` 含编号、标题与分隔符；`text == injection_block + user_prompt`；`total_chars == len(text)`。纯函数，无 DB、无文件系统、不渲染 HTML/Markdown。用例 `test_tc127_renders_injection_template_and_chars`、`test_tc128_uses_summary_and_marks_missing_body`、`test_tc150_injection_block_carries_kb_name_and_generated_at`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-KB-001
  - **对应 AC**：AC-014-2、AC-015-3、AC-REQ-21、AC-REQ-22
  - **TC**：TC-127、TC-128、TC-150
  - **估算**：6h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-005：实现两张表 ORM 与知识库仓储
  - **描述**：按 `database-schema.md` 建 `knowledge_base` / `knowledge_entry` 模型，并提供版本取号、当前版本查询、条目批量写入、检索分页、冲突批量查询与删除所需仓储能力。
  - **涉及文件**：`src/workbench/db/models/knowledge_base.py`、`src/workbench/db/models/knowledge_entry.py`、`src/workbench/db/models/__init__.py`、`src/workbench/db/repositories/knowledge.py`
  - **具体操作**：`kb_id` / `entry_id` 用 `CHAR(32)` + `uuid4().hex`；`project_id` 用 `pk_type()` 变体并建 `ON DELETE RESTRICT` 外键；`knowledge_entry.kb_id` 建 `ON DELETE CASCADE`；`summary` / `body` 用 `medium_text()`；JSON 列用 `sa.JSON` 且不建索引；`current_flag` 用 `'1'` / `NULL`；枚举列 `status` / `type` / `current_flag` 全部 `CheckConstraint`；索引与唯一键按 schema（`uq_knowledge_base_project_name_current`、`uq_knowledge_base_project_name_version`、`uq_knowledge_entry_kb_code`、`ix_*`）；`__table_args__` 写 InnoDB/utf8mb4 参数。在 `models/__init__.py` 追加导入与 `__all__`。仓储方法：按 `project_id + name_key` 锁定当前行取 `version`（MySQL `SELECT ... FOR UPDATE`，SQLite 串行写）、批量插入条目（按累计 ≤8MB 分块 `executemany`）、按项目/库/类型/关键词分页、`countsByType` 聚合、按 `code_key IN (...)` 批量查冲突、删除逻辑库全部版本。不逐行 N+1。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-001
  - **对应 AC**：AC-012-4、AC-013-1、AC-013-2、AC-015-2、AC-016-1
  - **TC**：无直接 TC（由 TASK-KB-006 / 008 / 010 的 TC-144 / TC-113 / TC-118 ~ TC-126 间接验证）
  - **估算**：14h [逻辑]，不确定性中（双方言类型与分块写入）
  - **状态**：pending

- [ ] TASK-KB-006：实现迁移 `0007_knowledge_base` 与双方言迁移用例
  - **描述**：新增本 spec 唯一迁移，创建两张表并验证 SQLite / MySQL 双方言升级、降级与约束生效。
  - **涉及文件**：`migrations/versions/0007_knowledge_base.py`、`tests/test_kb_migrations.py`
  - **具体操作**：`revision = "0007"`、`down_revision = "0006"`；先建 `knowledge_base` 再建 `knowledge_entry`；显式声明主键、外键（`project` RESTRICT、`kb` CASCADE）、CHECK、唯一键与索引；不用 `batch_alter_table`（新表无需）；不用方言专属 DDL；`downgrade()` 先删子表再删父表。用例在 SQLite 临时文件库执行 `upgrade head → downgrade 0006 → upgrade head`，断言两表、索引、CHECK 与级联存在；设置 `AW_TEST_DATABASE_URL` 时在 MySQL 8.4 复跑同一用例（CI job）。断言迁移不创建/不修改 core 表。用例 `test_tc144_migration_0007_on_both_dialects`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-KB-005
  - **对应 AC**：AC-012-4、AC-013-2、AC-016-1
  - **TC**：TC-144
  - **估算**：6h [集成]，不确定性中（本地无 MySQL 时跳过并标注）
  - **状态**：pending

- [ ] TASK-KB-007：实现知识库文件存储适配器
  - **描述**：提供 staging 流式写入、服务端命名、包含校验、原子 rename、trash 与孤儿目录扫描；客户端文件名绝不参与路径。
  - **涉及文件**：`src/workbench/adapters/fs/knowledge_storage.py`、`tests/test_kb_import_service.py`（存储用例）
  - **具体操作**：根目录 `settings.data_path / "knowledge-bases"`；暂存 `.staging/<importToken>/`（与目标同文件系统）；流式写入并边写边校验单文件/单次/合计字节与文件数；落盘名 `sha256(内容)[:16] + "__" + slug(原名)`，slug 去路径分隔符、控制字符与首尾点，≤80；每次写入前 `Path.resolve()` 并校验仍在 `knowledge-bases/` 根内；写 `manifest.json`（文件清单 + sha256 + 版本元数据）；`rename` 到 `knowledge-bases/<kbId>`；`move_to_trash` 移入 `AW_DATA_DIR/.trash/<kbId>-<ts>/`；`scan_orphans(max_age=1h)` 只删「有目录无 DB 行」且 mtime 早于 1 小时的目录，只记数量。用例 `test_tc116_client_filename_never_used_as_path`、`test_tc117_startup_scan_removes_orphan_dirs`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-001、TASK-KB-005
  - **对应 AC**：AC-012-7、AC-016-1、AC-REQ-18
  - **TC**：TC-116、TC-117
  - **估算**：10h [逻辑]，不确定性中（路径与并发清理）
  - **状态**：pending

- [ ] TASK-KB-008：实现导入编排服务与整体回滚
  - **描述**：串起限额校验、暂存、解析、正文匹配、名称推导、版本取号、原子 rename 与单事务落库；任一步失败清理全部产物。
  - **涉及文件**：`src/workbench/services/knowledge/__init__.py`、`src/workbench/services/knowledge/import_service.py`、`tests/test_kb_import_service.py`
  - **具体操作**：`KnowledgeImportService.import_files(*, project_id, name, files) -> ImportResult`。先逐文件校验扩展名（`.json` / `.md` / `.markdown`）、必须含一个 `index.json`、单文件上限（index 20MB / 其他 10MB）、文件数 ≤50、合计 ≤100MB，收集全部命中项一次性拒绝，不落盘。合规后流式写 staging → 解析 → 匹配正文 → 推导名称 → 行锁取版本 → `rename` → 单事务写 KB 行与条目（分块）。同名重导把旧行置 `status='superseded'`、`current_flag=NULL`、`superseded_by_kb_id=<新行>`，返回 `versionBumped=true` / `previousVersion`。唯一约束冲突重试 1 次，仍冲突抛 `kb_name_conflict`。失败路径回滚事务并删除 staging 与目标目录；日志与错误只含 id/文件名/行号/计数/原因码。用例 `test_tc104_fails_when_no_entry_importable`（API 部分）、`test_tc113_rolls_back_all_on_failure`、`test_tc115_concurrent_import_conflict_returns_409`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-002、TASK-KB-003、TASK-KB-005、TASK-KB-007
  - **对应 AC**：AC-012-1、AC-012-5、AC-012-7、AC-013-4、AC-REQ-19、AC-REQ-24
  - **TC**：TC-104、TC-113、TC-115
  - **估算**：14h [逻辑]，不确定性中（失败注入与版本并发）
  - **状态**：pending

- [ ] TASK-KB-009：实现导入 API、请求 schema 与路由/启动接线
  - **描述**：暴露 `POST /api/v1/knowledge-bases`（multipart），挂载知识库路由，并在启动生命周期加入孤儿目录扫描。
  - **涉及文件**：`src/workbench/api/schemas/knowledge.py`、`src/workbench/api/v1/knowledge_bases.py`、`src/workbench/api/v1/router.py`、`src/workbench/main.py`、`tests/test_kb_import_api.py`
  - **具体操作**：`multipart/form-data` 字段 `projectId`（number，必填）、`name`（可选 ≤200）、`files[]`（1..50）；校验项目存在（404 `project_not_found`）。响应 201 `{kb, importReport}`，字段 camelCase，`kbId` 为 string（受 OQ-TD-04 影响，落地时按结论）；错误映射 `unsupported_file_type` / `too_many_files` / `file_too_large` / `index_json_missing` / `index_json_invalid` / `kb_name_conflict` / `kb_import_too_large` / `kb_write_failed` / `validation_error`，`details` 逐项且不含正文。`router.py` 注册 `knowledge_bases` / `knowledge_entries` / `knowledge_injection` 三个 router（统一依赖 `require_session`）。`main.py` lifespan 启动后调用孤儿扫描（mtime >1h，失败只记日志）。用例 `test_tc111_imports_knowledge_base_and_lists_it`、`test_tc112_rejects_upload_limit_violations_per_file`、`test_tc114_reimport_creates_new_version_and_supersedes_old`、`test_tc117_startup_scan_removes_orphan_dirs`（接线部分）、`test_tc145_large_body_roundtrip_not_truncated`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-008
  - **对应 AC**：AC-012-1、AC-012-2、AC-012-6、AC-012-7、AC-013-4、AC-REQ-18、AC-REQ-24
  - **TC**：TC-111、TC-112、TC-114、TC-117、TC-145
  - **估算**：10h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-010：实现查询服务（列表、版本、检索、详情、徽标）
  - **描述**：组装知识库列表/详情/版本、条目浏览与检索、类型计数、游标分页、新鲜度与冲突徽标，供浏览 API 与注入候选共用。
  - **涉及文件**：`src/workbench/services/knowledge/query_service.py`、`tests/test_kb_query_api.py`（服务级断言）
  - **具体操作**：`list_bases`（`projectId` / `includeSuperseded` / `limit` / `cursor`，排序 `updated_at DESC, kb_id`）；`get_base`（项目、全部版本、计数、导入报告、`latestKbId`、`supersededBy`）；`list_versions`；`search_entries`（`projectId` / `kbId` / `type` / `q` / `includeSuperseded`；默认只搜当前版本；`q` 转义 `% _ \` 并 `ESCAPE '\'`；排序 rank：`code` 精确 > `code` 前缀 > `title` > `summary` > `body`，同档 `code_key ASC, entry_id`；游标 base64url `{rank, code, entryId}`）；`countsByType` 忽略 `type`、共用其他条件一次聚合；`get_entry` 返回摘要/正文/字段/表/代码路径/邻居（同项目当前版本解析，不存在 `exists=false`）/来源文件/新鲜度/冲突；`injection_candidates` 只返回当前版本。新鲜度 `unknown` / `fresh` / `stale`（`AW_KB_STALE_DAYS`）；冲突按 `code_key IN (...)` 批量查、来源 ≤ `AW_KB_CONFLICT_SOURCES`。用例 `test_tc119_searches_by_code_prefix_exact_and_keyword`、`test_tc120_paginates_with_stable_cursor_and_counts_by_type`、`test_tc124_computes_freshness_states`、`test_tc125_detects_conflict_by_summary_digest`、`test_tc126_conflict_query_is_batched`、`test_tc143_project_summary_returns_zero_to_n_bases`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-005、TASK-KB-006
  - **对应 AC**：AC-012-6、AC-013-1、AC-013-3、AC-015-1、AC-015-2、AC-015-3、AC-REQ-20、AC-REQ-22、AC-REQ-24
  - **TC**：TC-119、TC-120、TC-124、TC-125、TC-126、TC-143
  - **估算**：12h [逻辑]，不确定性中（排序与游标稳定性）
  - **状态**：pending

- [ ] TASK-KB-011：实现知识库与条目浏览 API
  - **描述**：暴露知识库列表/详情/版本、全局条目检索、库内条目、条目详情共 6 个读端点，完成参数校验与错误映射。
  - **涉及文件**：`src/workbench/api/v1/knowledge_bases.py`、`src/workbench/api/v1/knowledge_entries.py`、`src/workbench/api/schemas/knowledge.py`、`tests/test_kb_query_api.py`
  - **具体操作**：`GET /knowledge-bases`、`GET /knowledge-bases/{kbId}`、`GET /knowledge-bases/{kbId}/versions`、`GET /knowledge-entries`、`GET /knowledge-bases/{kbId}/entries`、`GET /knowledge-entries/{entryId}`；`type` 枚举、`q` 1..100、`limit` 1..200、`cursor` 损坏 → 400 `validation_error`；404 `project_not_found` / `kb_not_found` / `entry_not_found`；响应 camelCase、RFC 3339 UTC；正文/摘要只按纯文本输出，不渲染 HTML。用例 `test_tc118_lists_entries_by_project_kb_and_type`、`test_tc121_entry_detail_contains_all_fields_and_neighbors`、`test_tc122_superseded_entry_points_to_latest`、`test_tc123_detail_shows_summary_when_body_missing`。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-KB-010
  - **对应 AC**：AC-013-1、AC-013-2、AC-013-4、AC-013-5、AC-REQ-20
  - **TC**：TC-118、TC-121、TC-122、TC-123
  - **估算**：8h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-012：实现注入服务、候选/预览端点与失效确认
  - **描述**：实现唯一的注入组装入口：preview 只读估算，prepare 重校验失效集并要求精确确认，超预算拒绝且不截断；同时提供候选与预览两个只读端点。
  - **涉及文件**：`src/workbench/services/knowledge/injection_service.py`、`src/workbench/api/v1/knowledge_injection.py`、`src/workbench/api/schemas/knowledge.py`、`tests/test_kb_injection_service.py`、`tests/test_kb_injection_api.py`
  - **具体操作**：`preview(*, project_id, refs, user_prompt)` 复用同一组装实现，返回 `items / invalidItems / promptChars / injectedChars / totalChars / limit / overLimit / warnings`，失效与超限不是错误；响应不回注入文本。`prepare_for_call(*, session_id, project_id, prompt, refs, confirm_invalid_codes)`：重算失效集（`kb_deleted` / `entry_not_found` / `superseded`），按 `(kb_id, code)` 确定性排序；失效集非空且确认集不完全相等 → `KnowledgeInvalidEntriesError`；确认后有效集为空 → `KnowledgeInjectionEmptyError`；`total_chars > get_settings().prompt_max_chars` → `PromptBudgetExceededError`（带分段字数与上限，不截断）；通过后调用 `render_injection` 并构造 `core.ports.InjectionSnapshot`（按库分组 `entry_codes`、`injected_chars` 求和、`excluded_codes`）。`GET /sessions/{sessionId}/knowledge-injection/candidates` 只返回当前版本 + 徽标，支持 `q` / `type` / `limit` / `cursor`；`POST /sessions/{sessionId}/knowledge-injection/preview` 校验 `refs[].kbId` / `refs[].code` / `userPrompt`。两类端点都不落库、不调模型；日志与错误只含 id/编号/计数/字符数。用例 `test_tc129_preview_reports_segments_and_over_limit`、`test_tc130_rejects_over_budget_without_truncation`、`test_tc131_invalid_entries_block_call_without_record`、`test_tc132_confirmation_requires_exact_invalid_set`、`test_tc133_cancel_does_not_initiate_call`、`test_tc134_confirmation_with_empty_valid_set_is_rejected`、`test_tc135_classifies_invalid_reasons`、`test_tc138_candidates_only_current_versions_with_badges`、`test_tc149_freshness_and_conflict_warnings_do_not_block`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-004、TASK-KB-010
  - **对应 AC**：AC-014-1、AC-014-2、AC-014-3、AC-014-4、AC-015-3、AC-015-4、AC-REQ-21、AC-REQ-22
  - **TC**：TC-129、TC-130、TC-131、TC-132、TC-133、TC-134、TC-135、TC-138、TC-149
  - **估算**：16h [逻辑]，不确定性中（确认竞态与预算边界）
  - **状态**：pending

- [ ] TASK-KB-013：把注入服务注册进 core 并锁定进程内契约
  - **描述**：在 `create_app()` 中注册真实的 `InjectionPreparer`，使 core 的 `POST /ai/complete` 在带 `knowledgeRefs` 时完成失效重校验、组装与留痕；验证 409/400 路径不写 `AiCallRecord`。
  - **涉及文件**：`src/workbench/services/knowledge/registration.py`、`src/workbench/main.py`、`tests/test_kb_injection_api.py`（或 `tests/test_kb_injection_service.py` 的桥接用例）
  - **具体操作**：`install_injection_preparer(app)` 构造 `KnowledgeInjectionService`（会话工厂、设置、仓储）并调用 core 的 `register_injection_preparer(impl)`；测试结束时注销，避免跨用例污染（core `tests/conftest.py` 已有 `injection_preparer` fixture，可参照）。把本 spec 的服务结果转换为 `core.ports.PreparedInjection(prepared=text, snapshot=snapshot)`；`total_chars == len(text)`，否则 core 返回 400 `injection_snapshot_mismatch`。确认 core 的 `/ai/complete` 映射：未确认 → 409 `knowledge_invalid_entries`、空集 → 409 `knowledge_injection_empty`、超预算 → 400 `prompt_budget_exceeded`，三者都不调 `AiGateway`、不写记录。**`kbId` 类型按 OQ-TD-04 结论落地**；在结论明确前不把该任务标记完成。用例 `test_tc136_records_injection_snapshot_without_body`、`test_tc137_logs_and_errors_never_contain_body`（注入路径部分）。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-KB-012
  - **对应 AC**：AC-014-2、AC-014-4、AC-014-5、AC-REQ-21
  - **TC**：TC-136、TC-137
  - **估算**：6h [集成]，不确定性中（跨 spec 契约，见 OQ-TD-04 / RISK-108）
  - **状态**：pending

- [ ] TASK-KB-014：实现删除生命周期、DELETE 端点与横切 API 用例
  - **描述**：删除逻辑知识库的全部版本、条目与文件，保留历史会话/事件/调用记录；补齐 10 个端点的鉴权与错误体横切断言。
  - **涉及文件**：`src/workbench/services/knowledge/lifecycle_service.py`、`src/workbench/api/v1/knowledge_bases.py`、`src/workbench/db/repositories/knowledge.py`、`tests/test_kb_lifecycle_api.py`、`tests/test_kb_security_logs.py`
  - **具体操作**：`delete_logical(*, project_id, kb_id)`：由 `kb_id` 解析 `(project_id, name_key)`，单事务删除该逻辑库全部版本（条目 FK 级联）；提交后把各版本目录 `rename` 进 `.trash/<kbId>-<ts>/` 并尽力删除，失败只记日志仍返回 204；不存在 → 404 `kb_not_found`。`DELETE /knowledge-bases/{kbId}` 为高风险操作，前端二次确认。历史记录不改；读取时 `kbDeleted` 由 core 左连接判定。横切：TC-147 断言 10 个端点无 Cookie → 401 且不泄露资源存在性；TC-148 断言错误体 `{code,message,details[],requestId}`、`details` 恒为数组、时间为 RFC 3339 UTC；TC-137 断言导入/解析/注入路径日志与响应体无哨兵正文。用例 `test_tc139_delete_removes_all_versions_entries_and_files`、`test_tc140_history_survives_delete_and_is_flagged`、`test_tc141_delete_is_scoped_to_one_logical_kb`、`test_tc142_file_cleanup_failure_still_returns_204`、`test_tc147_all_endpoints_require_session`、`test_tc148_error_body_and_time_format`、`test_tc137_logs_and_errors_never_contain_body`。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-007、TASK-KB-010、TASK-KB-012
  - **对应 AC**：AC-014-5、AC-016-1、AC-016-2、AC-016-3、AC-REQ-23
  - **TC**：TC-137、TC-139、TC-140、TC-141、TC-142、TC-147、TC-148
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-015：实现前端知识库数据层
  - **描述**：建立与 `api-spec.md` 对齐的 TS 类型、端点封装、Query key 工厂与 7 个 hooks；把选择器状态转换为 core `/ai/complete` 的请求形状。
  - **涉及文件**：`web/src/features/knowledge/api/types.ts`、`web/src/features/knowledge/api/client.ts`、`web/src/features/knowledge/api/keys.ts`、`web/src/features/knowledge/hooks/{useKnowledgeBases,useKnowledgeEntries,useEntryDetail,useImportKnowledge,useDeleteKnowledge,useInjectionCandidates,useInjectionPreview}.ts`、`web/src/features/knowledge/index.ts`
  - **具体操作**：`kbId` / `entryId` 为 `string`，`projectId` 为 `number`；复用 `web/src/lib/api/client.ts` 的 `apiFetch` / `queryString`；`preview` 请求体 `{refs, userPrompt}`；`toKnowledgeRefs(refs)` 按 `kbId` 分组为 `{kbId, entryCodes[]}`；`confirmInvalidCodes` 保持扁平 `{kbId, code}`。Query key：`["kb","list",{projectId,cursor}]`、`["kb",kbId,"detail"]`、`["kb",kbId,"versions"]`、`["kb","entries",{projectId,kbId,type,q,cursor}]`、`["kb",entryId]`、`["kb",sessionId,"candidates",{q,type,cursor}]`、`["kb",sessionId,"preview",{refsKey,prompt}]`；导入/删除成功失效 `["kb"]`；preview 防抖 250ms，勾选变化不重取候选。所有 hook 走 TanStack Query，不在组件内自建缓存。
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **依赖**：TASK-KB-009、TASK-KB-011、TASK-KB-012、TASK-KB-014
  - **对应 AC**：AC-012-1、AC-013-1、AC-014-1、AC-016-1
  - **TC**：无（前端 P1 可选，不计入后端 TC 结果）
  - **估算**：8h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-016：实现知识库列表页与导入页
  - **描述**：落地 `/knowledge-bases` 与 `/knowledge-bases/import`，包含项目筛选、列表、删除确认、多文件校验与导入报告。
  - **涉及文件**：`web/src/features/knowledge/pages/KnowledgeBaseListPage.tsx`、`web/src/features/knowledge/pages/KnowledgeImportPage.tsx`、`web/src/features/knowledge/components/{KnowledgeBaseTable,KbProjectFilter,KbDeleteDialog,KbImportPanel,KbFileValidationList,KbImportReport}.tsx`、同名 `*.module.css`
  - **具体操作**：列表展示名称、项目、最新版本、生成时间（缺失「未知」）、条目数、状态与操作；旧版本行内「另有 N 个旧版本（只读）」；页脚固定说明「只读导入、同名生成新版本、旧版只读」。导入页 `accept=".json,.md,.markdown"`，前端只做扩展名/单文件/数量/合计的即时提示并在不合规时禁用提交，**不前端解析 `index.json` 结构**；成功后展示已导入 N 条、跳过 M 条（行号 + 原因）、未匹配文件、新版本提示；报告只展示标识、行号、原因码，不展示正文。删除复用 `ConfirmDialog`，列明级联范围与「历史记录不变、无撤销」。样式只引用 core token，不新增变量。
  - **优先级**：P1
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-015
  - **对应 AC**：AC-012-1、AC-012-2、AC-012-5、AC-012-6、AC-016-1、AC-016-3
  - **TC**：无（前端 P1 可选；服务端结论见 TC-111 / TC-112 / TC-139）
  - **估算**：12h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-017：实现浏览页与条目详情页
  - **描述**：落地 `/knowledge-bases/:kbId` 与 `/knowledge-bases/:kbId/entries/:code`，提供筛选、类型分栏、检索、版本选择、详情与徽标。
  - **涉及文件**：`web/src/features/knowledge/pages/KnowledgeBrowsePage.tsx`、`web/src/features/knowledge/pages/KnowledgeEntryPage.tsx`、`web/src/features/knowledge/components/{KbBrowseLayout,KbTypeTabs,KbSearchBox,KbEntryList,KbEntryDetail,KbFreshnessBadge,KbConflictNotice,KbVersionSelector,KbDeletedBadge}.tsx`、同名 `*.module.css`
  - **具体操作**：筛选与检索状态由 URL query 驱动，`KbSearchBox` 300ms 防抖、`q` ≤100；默认展示最新版本，旧版本顶部提示「已被新版本取代」并提供「查看最新版」；`KbEntryDetail` 始终展示摘要，正文存在时展示正文，缺失时展示摘要并标「正文缺失」；字段/表/代码路径缺失显示「—」；一跳邻居存在时可跳转同项目条目，不存在时禁用；编号与代码路径用 `--font-family-mono`；正文/标题按纯文本渲染，不使用 `dangerouslySetInnerHTML`，不提供源文件下载；冲突提示注明「只提示，不阻止注入」。
  - **优先级**：P1
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-015
  - **对应 AC**：AC-013-1、AC-013-2、AC-013-3、AC-013-4、AC-013-5、AC-015-1、AC-015-2、AC-015-3、AC-015-4
  - **TC**：无（前端 P1 可选；服务端结论见 TC-118 ~ TC-125、TC-149）
  - **估算**：14h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-KB-018：接入 core 嵌入组件、路由导航与备份核对 [no-test]
  - **描述**：把注入选择器、字符预算、失效确认对话框嵌入 core 的会话调用面板；把项目摘要挂到既有挂载位；补齐路由、侧边栏入口与备份核对说明；完成手工端到端验收。
  - **涉及文件**：`web/src/features/knowledge/components/{KbInjectPicker,KbCharBudget,KbInvalidEntryDialog,ProjectKnowledgeSummary}.tsx`、`web/src/features/knowledge/routes.tsx`、`web/src/features/knowledge/index.ts`、`web/src/features/calls/CallPanel.tsx`、`web/src/features/projects/ProjectKnowledgeSummary.tsx`、`web/src/features/projects/ProjectsPage.tsx`、`web/src/router.tsx`、`web/src/app/AppShell.tsx`、`scripts/backup.sh`（核对）
  - **具体操作**：`KbInjectPicker` 读取当前会话项目的当前版本条目，按编号勾选，只展示徽标与标题，不渲染正文；`KbCharBudget` 展示「已选 N 条 · 注入 X 字符 · 提示 Y 字符 · 合计 Z / 200,000」，>90% warning，超限禁用「发起调用」并注明「不会截断」；`CallPanel` 提交时附带 `knowledgeRefs`，收到 409 `knowledge_invalid_entries` 打开 `KbInvalidEntryDialog`，确认后把 `details.invalidItems` 原样作为 `confirmInvalidCodes` 重试，取消则关闭且不发请求；409 后保留其余勾选，失效项取消勾选并标「不可用」。`ProjectKnowledgeSummary` 替换 `web/src/features/projects/ProjectKnowledgeSummary.tsx` 的空占位实现（保留 `data-mount="knowledge-summary"`），展示 0..n 个关联知识库并可跳转。`router.tsx` 在 `AuthGate` 内追加 4 条路由；`AppShell.tsx` 在「基座管理」分组追加「知识库」。`scripts/backup.sh` 核对：现有脚本已整体打包 `AW_DATA_DIR`，确认 `knowledge-bases/` 被包含、`.trash/` 被排除，并在恢复说明中补充按 `manifest.json` 核对 sha256。
  - **优先级**：P1
  - **复杂度**：M（2–3d）
  - **依赖**：TASK-KB-013、TASK-KB-016、TASK-KB-017
  - **对应 AC**：AC-012-6、AC-014-1、AC-014-2、AC-014-3、AC-014-4、AC-015-3、AC-REQ-21、AC-REQ-24
  - **TC**：无（前端 P1 可选；手工 E2E 作为验收证据）
  - **估算**：14h [样板]，不确定性中（跨 core 页面接入与 409 流程）
  - **状态**：pending
  - 免测理由：前端组件与页面按 `test-strategy.md` §1 为 P1 可选、不进入后端 TC 结果；其服务端结论已由 TC-129 ~ TC-138、TC-136 覆盖。本任务的验收证据为 `npm run build`、可选 Vitest 与手工端到端记录，不作为 pytest TC 来源。

## 5. 测试与门禁

- **TC 编号范围**：TC-101 ~ TC-150（50 条），全部由 pytest 用例给出结果，用例名统一 `test_tcNNN_<行为>`；后续新增从 TC-151 顺延。
- **默认套件**：SQLite 临时文件库（WAL + `busy_timeout`）+ 临时 `AW_DATA_DIR`；每个用例独立数据库，不读写本机真实数据。
- **MySQL**：CI service 容器复跑全部 API 用例与 `test_kb_migrations.py`；双方言只在一种通过视为缺陷（RISK-105）。
- **前端**：Vitest + Testing Library 为 P1 可选，不进入后端 TC 结果；后端门禁只证明 50 个 pytest TC 有结果。
- **不发起真实外部请求**：注入类用例使用 core 的假适配器或替换 `AiGateway` 的测试实现；限额用环境变量覆盖为小值。
- **安全断言**：用随机哨兵正文（如 `SENTINEL-<uuid>`）扫描 `caplog` 与响应体，断言日志、错误体、`import_report` 不含正文、摘要与字段值（TC-137）。
- **执行入口**：`uv run pytest -q`；测试报告需逐条出现 TC 编号，且新增 TC 必须同提交登记到 `test-verification/tc-map.json`（由 `tests/test_spec_tc_sync.py` 断言）。

## 6. AC → TC → 测试文件/用例名落点表

> 覆盖 24 条 AC + 7 条 EARS（AC-REQ-18 ~ AC-REQ-24）。文件路径相对仓库根 `tests/`。

| AC | TC | 测试文件 | 用例名（简） |
|----|----|---------|-------------|
| AC-012-1 | TC-108、TC-111 | `tests/test_kb_naming.py`、`tests/test_kb_import_api.py` | `test_tc108_derives_name_in_fixed_order`、`test_tc111_imports_knowledge_base_and_lists_it` |
| AC-012-2 | TC-112、TC-146 | `tests/test_kb_import_api.py`、`tests/test_kb_config.py` | `test_tc112_rejects_upload_limit_violations_per_file`、`test_tc146_kb_settings_defaults_and_overrides` |
| AC-012-3 | TC-101、TC-107 | `tests/test_kb_index_parser.py` | `test_tc101_rejects_index_without_schema_or_entries`、`test_tc107_rejects_invalid_json_syntax` |
| AC-012-4 | TC-102、TC-106 | `tests/test_kb_index_parser.py` | `test_tc102_maps_prefix_to_entry_type`、`test_tc106_truncates_neighbors_and_drops_large_extras` |
| AC-012-5 | TC-103、TC-104 | `tests/test_kb_index_parser.py`、`tests/test_kb_import_api.py` | `test_tc103_skips_invalid_entries_with_line_and_reason`、`test_tc104_fails_when_no_entry_importable` |
| AC-012-6 | TC-111、TC-143 | `tests/test_kb_import_api.py`、`tests/test_kb_query_api.py` | `test_tc111_imports_knowledge_base_and_lists_it`、`test_tc143_project_summary_returns_zero_to_n_bases` |
| AC-012-7 | TC-113 | `tests/test_kb_import_service.py` | `test_tc113_rolls_back_all_on_failure` |
| AC-013-1 | TC-118、TC-120 | `tests/test_kb_query_api.py` | `test_tc118_lists_entries_by_project_kb_and_type`、`test_tc120_paginates_with_stable_cursor_and_counts_by_type` |
| AC-013-2 | TC-121 | `tests/test_kb_query_api.py` | `test_tc121_entry_detail_contains_all_fields_and_neighbors` |
| AC-013-3 | TC-119、TC-120 | `tests/test_kb_query_api.py` | `test_tc119_searches_by_code_prefix_exact_and_keyword`、`test_tc120_paginates_with_stable_cursor_and_counts_by_type` |
| AC-013-4 | TC-114、TC-122 | `tests/test_kb_import_api.py`、`tests/test_kb_query_api.py` | `test_tc114_reimport_creates_new_version_and_supersedes_old`、`test_tc122_superseded_entry_points_to_latest` |
| AC-013-5 | TC-109、TC-110、TC-123、TC-128 | `tests/test_kb_body_matcher.py`、`tests/test_kb_query_api.py`、`tests/test_kb_rendering.py` | `test_tc109_matches_body_by_filename_then_heading`、`test_tc110_marks_missing_body_as_blank`、`test_tc123_detail_shows_summary_when_body_missing`、`test_tc128_uses_summary_and_marks_missing_body` |
| AC-014-1 | TC-129、TC-138 | `tests/test_kb_injection_service.py`、`tests/test_kb_injection_api.py` | `test_tc129_preview_reports_segments_and_over_limit`、`test_tc138_candidates_only_current_versions_with_badges` |
| AC-014-2 | TC-127、TC-128、TC-136 | `tests/test_kb_rendering.py`、`tests/test_kb_injection_api.py` | `test_tc127_renders_injection_template_and_chars`、`test_tc128_uses_summary_and_marks_missing_body`、`test_tc136_records_injection_snapshot_without_body` |
| AC-014-3 | TC-129、TC-130 | `tests/test_kb_injection_service.py` | `test_tc129_preview_reports_segments_and_over_limit`、`test_tc130_rejects_over_budget_without_truncation` |
| AC-014-4 | TC-131、TC-132、TC-133、TC-134、TC-135 | `tests/test_kb_injection_service.py`、`tests/test_kb_injection_api.py` | `test_tc131_invalid_entries_block_call_without_record`、`test_tc132_confirmation_requires_exact_invalid_set`、`test_tc133_cancel_does_not_initiate_call`、`test_tc134_confirmation_with_empty_valid_set_is_rejected`、`test_tc135_classifies_invalid_reasons` |
| AC-014-5 | TC-136、TC-137 | `tests/test_kb_injection_api.py`、`tests/test_kb_security_logs.py` | `test_tc136_records_injection_snapshot_without_body`、`test_tc137_logs_and_errors_never_contain_body` |
| AC-015-1 | TC-124 | `tests/test_kb_query_api.py` | `test_tc124_computes_freshness_states` |
| AC-015-2 | TC-125、TC-126 | `tests/test_kb_query_api.py` | `test_tc125_detects_conflict_by_summary_digest`、`test_tc126_conflict_query_is_batched` |
| AC-015-3 | TC-124、TC-138、TC-150 | `tests/test_kb_query_api.py`、`tests/test_kb_injection_api.py`、`tests/test_kb_rendering.py` | `test_tc124_computes_freshness_states`、`test_tc138_candidates_only_current_versions_with_badges`、`test_tc150_injection_block_carries_kb_name_and_generated_at` |
| AC-015-4 | TC-149 | `tests/test_kb_injection_service.py` | `test_tc149_freshness_and_conflict_warnings_do_not_block` |
| AC-016-1 | TC-139 | `tests/test_kb_lifecycle_api.py` | `test_tc139_delete_removes_all_versions_entries_and_files` |
| AC-016-2 | TC-140 | `tests/test_kb_lifecycle_api.py` | `test_tc140_history_survives_delete_and_is_flagged` |
| AC-016-3 | TC-141、TC-142 | `tests/test_kb_lifecycle_api.py` | `test_tc141_delete_is_scoped_to_one_logical_kb`、`test_tc142_file_cleanup_failure_still_returns_204` |
| AC-REQ-18 | TC-105、TC-112 | `tests/test_kb_index_parser.py`、`tests/test_kb_import_api.py` | `test_tc105_enforces_parser_guards`、`test_tc112_rejects_upload_limit_violations_per_file` |
| AC-REQ-19 | TC-101、TC-103、TC-104、TC-105 | `tests/test_kb_index_parser.py`、`tests/test_kb_import_api.py` | `test_tc101_rejects_index_without_schema_or_entries`、`test_tc103_skips_invalid_entries_with_line_and_reason`、`test_tc104_fails_when_no_entry_importable`、`test_tc105_enforces_parser_guards` |
| AC-REQ-20 | TC-118、TC-119、TC-121、TC-123 | `tests/test_kb_query_api.py` | `test_tc118_lists_entries_by_project_kb_and_type`、`test_tc119_searches_by_code_prefix_exact_and_keyword`、`test_tc121_entry_detail_contains_all_fields_and_neighbors`、`test_tc123_detail_shows_summary_when_body_missing` |
| AC-REQ-21 | TC-127、TC-130、TC-136、TC-137 | `tests/test_kb_rendering.py`、`tests/test_kb_injection_service.py`、`tests/test_kb_injection_api.py`、`tests/test_kb_security_logs.py` | `test_tc127_renders_injection_template_and_chars`、`test_tc130_rejects_over_budget_without_truncation`、`test_tc136_records_injection_snapshot_without_body`、`test_tc137_logs_and_errors_never_contain_body` |
| AC-REQ-22 | TC-124、TC-125、TC-149、TC-150 | `tests/test_kb_query_api.py`、`tests/test_kb_injection_service.py`、`tests/test_kb_rendering.py` | `test_tc124_computes_freshness_states`、`test_tc125_detects_conflict_by_summary_digest`、`test_tc149_freshness_and_conflict_warnings_do_not_block`、`test_tc150_injection_block_carries_kb_name_and_generated_at` |
| AC-REQ-23 | TC-139、TC-140 | `tests/test_kb_lifecycle_api.py` | `test_tc139_delete_removes_all_versions_entries_and_files`、`test_tc140_history_survives_delete_and_is_flagged` |
| AC-REQ-24 | TC-114、TC-143 | `tests/test_kb_import_api.py`、`tests/test_kb_query_api.py` | `test_tc114_reimport_creates_new_version_and_supersedes_old`、`test_tc143_project_summary_returns_zero_to_n_bases` |

## 7. 关键路径与风险

### 关键路径

```text
KB-001 → KB-002 → KB-003 → KB-005 → KB-006 → KB-007 → KB-008 → KB-009
       → KB-010 → KB-012 → KB-013 → KB-018
```

- 关键路径工时（单线程）：5 + 12 + 8 + 14 + 6 + 10 + 14 + 10 + 12 + 16 + 6 + 14 = **127h**，按每日 4.8h 有效开发约 **26.5 人日**。
- 全部任务合计 **185h**（约 38.5 人日）；004 / 011 / 014 / 015 ~ 017 可并行，理论最短约 27 ~ 29 人日（2 人并行时约 15 ~ 17 天）。
- 主要阻塞点：KB-013 依赖 OQ-TD-04 的 `kbId` 类型结论；KB-018 依赖前端 015 ~ 017 与 core 接入。

### 风险对照

| 风险 | 对应用例 / 任务 | 缓解落点 |
|------|----------------|---------|
| RISK-101 正文/摘要泄露 | TC-137、TC-148；KB-012 / 013 / 014 | 错误与日志字段白名单；解析器异常不透传；哨兵正文扫描 |
| RISK-102 路径穿越与资源耗尽 | TC-105、TC-112、TC-116；KB-002 / 007 / 008 | 服务端命名 + `resolve()` 包含校验 + 深度/条目/字节护栏 + 失败整包回滚 |
| RISK-105 双方言漂移 | TC-144、TC-145；KB-005 / 006 / 009 | `MEDIUMTEXT` 变体、JSON 不建索引、可空唯一索引、CI MySQL job |
| RISK-108 跨 spec 契约漂移（含 `kbId` 类型） | TC-136；KB-013；OQ-TD-04 | 先定类型再联调；快照断言只含标识/字符数；不实现静默降级 |
| RISK-109 阻塞确认被绕过或过期 | TC-131 ~ TC-134；KB-012 | `prepare_for_call` 每次重算失效集；确认集排序后完全相等；确认后空集 409 |
| RISK-113 前后端字符预算漂移 | TC-127、TC-129、TC-150；KB-004 / 012 / 015 | 模板与计数只在服务端定义；前端即时估算仅作提示，发起前以 preview/prepare 为准 |

## 8. 估点摘要

- 任务总数：**18**（S 7 / M 11；无 XS / L / XL）。
- 批次工时：A 51h、B 34h、C 20h、D 32h、E 48h，合计 **185h**。
- TC：TC-101 ~ TC-150 共 **50** 条，覆盖 **24 条 AC + 7 条 EARS**；全部由 pytest 给出结果。
- 前置：core `0006` 已落地（本仓库已确认）；OQ-TD-04 需在批次 D 联调前拍板；MySQL 用例依赖 CI service 容器。
- 批次验收：A（TC-101 ~ TC-110、127、128、150 + 迁移）；B（TC-111 ~ TC-117、145）；C（TC-118 ~ TC-126、143）；D（TC-129 ~ TC-142、149、136、137、147、148）；E（前端 build / 可选 Vitest / 手工 E2E / 备份核对）。
