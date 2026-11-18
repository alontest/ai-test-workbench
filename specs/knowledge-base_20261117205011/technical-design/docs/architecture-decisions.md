# Architecture Decisions Record (ADR) — knowledge-base

## 锁定时间

2026-11-18 11:15

> 编号从 ADR-101 起，避免与 workbench-core 的 ADR-001 ~ ADR-041 冲突。来源 spec 的 ADR-029 ~ ADR-040 已随 2026-11-17 的 spec 拆分迁出并保留编号；本文件的每条 ADR 都在 `_handoff/from-tech-arch.md` 的基础上**按当前需求重新论证**，不是原文照抄。跨 spec 扩展已按 `technical-design/answers.md`（2026-11-18 11:23:18，用户原话「A101 A、A102 A、A103 B」）拍板：101 = core 落库扩展、102 = `complete` 追加可选 `injection`、103 = 复用 core 的 `/ai/complete` 入口、不新增 calls 端点。

## 项目扫描摘要

| 层次 | 检测结果 | 置信度 |
|------|---------|--------|
| 仓库现状 | 占位骨架：`pyproject.toml`（无运行依赖）、`src/workbench/__init__.py`、`tests/conftest.py`；无后端/前端代码 | 高 |
| 后端 | 继承 core 的 architecture-locked 选型：Python 3.12+ / FastAPI / Pydantic 2 / SQLAlchemy 2.1 / Alembic / 单进程 Uvicorn | 高（来自 `specs/ai-test-workbench_20261117184149`） |
| 前端 | 继承 core：React 19 + TypeScript + Vite + React Router + TanStack Query + CSS 变量/CSS Modules + Radix Primitives；`dist` 由后端同源托管 | 高（同上） |
| 数据库 | MySQL 8.4 LTS（生产）+ SQLite（开发/测试），同一套 ORM 模型与迁移，双方言纪律 | 高（同上） |
| 部署 | docker-compose（app + mysql:8.4），支持外接 MySQL；默认 `127.0.0.1:8000` | 高（同上） |
| 知识库模块 | 尚无任何代码与迁移；本 spec 新建 `knowledge-base` 垂直模块、2 张表、1 组端点与 5 个页面/嵌入组件 | — |
| AlonWorkflow packs | `.aw/install.json` 的 `packs` 为空，未安装任何 pack，未套用 pack 专属约定 | 高 |

## 已确认决策

### ADR-101：技术栈完整继承 workbench-core，不重新选型

- **决策**：后端 Python 3.12+ / FastAPI / Pydantic 2 / SQLAlchemy 2.1 / Alembic / 单进程 Uvicorn；前端 React 19 + TS + Vite + React Router + TanStack Query + CSS 变量/CSS Modules + Radix Primitives；MySQL 8.4 生产 + SQLite 开发/测试。知识库作为同一进程内的垂直模块落地，不引入新的运行时、数据库或前端框架。
- **来源**：继承 core（core ADR-001 / 002 / 003 / 015 / 016 / 017 / 027）
- **状态**：✅ 已锁定
- **理由**：上游任务已锁定技术栈且与 core 一致；核心约束 `BG-05` 要求知识库复用 core 的会话、调用记录与登录态，混用第二套栈只会增加进程内与部署成本。`python-multipart` 已在 core（制品上传），导入上传直接复用。
- **影响**：依赖版本以 core 的 `pyproject.toml` / `uv.lock` 为唯一真源，本 spec 只在其中追加模块代码与迁移；本 spec 不新增任何第三方解析/检索/前端依赖。
- **取代**：无

### ADR-102：模块边界——进程内垂直模块，只经冻结接口与 core 交互

- **决策**：知识库后端落在 `src/workbench/knowledge/`（纯解析层）与 `src/workbench/services/knowledge/`（导入、查询、注入、生命周期服务），API 落在 `src/workbench/api/v1/knowledge*`；对 core 的依赖只允许三类：①调用 `AiGateway.complete(...)`；②调用 `sessions.append_event(...)`；③只读 `project_context`。反向由 core 调用本 spec 的进程内服务 `KnowledgeInjectionService.prepare_for_call(...)`（失效重校验 + 组装 + 字符预算，供 core 的 `POST /ai/complete` 使用，见 ADR-110 / ADR-112）。不新建 HTTP 客户端、不复制 AI 适配层与凭据读取、不直接写 `session_event` / `ai_call_record` 表（其扩展列与写入归 core，见 ADR-111）。全部对外端点挂 core 的 `require_session`，不新增匿名端点。
- **来源**：新增（依据 core ADR-041、`requirements-analysis/docs/context.md` 系统集成点）
- **状态**：✅ 已锁定
- **理由**：单用户、单进程部署，进程内调用是零成本且不存在网络失败面；`AiGateway` 是唯一模型出口与唯一预算收口，知识库若自建模型调用会绕过并发上限、超时/重试与 AiCallRecord 生命周期。
- **影响**：知识库与 core 必须同一发布单元交付；跨模块测试用同一个 `create_app()` fixture；跨 spec 扩展按 `technical-design/answers.md`（2026-11-18 11:23:18）执行，不在知识库模块里私改 core 表语义。
- **取代**：无

### ADR-103：数据模型与双方言映射

- **决策**：新增两张表（一行 = 一个版本快照 / 一个编号）：
  - `knowledge_base`：`kb_id CHAR(32)` PK、`project_id` FK → `project_context` `ON DELETE RESTRICT`、`name`、`name_key`（`casefold(trim(name))`）、`version`、`current_flag CHAR(1) NULL`、`status`（`ready` / `superseded`）、`index_generated_at`、`entry_count`、`file_count`、`total_byte_size`、`source_index_sha256`、`storage_dir`、`superseded_by_kb_id`、`import_report JSON NULL`、`created_at` / `updated_at`。
  - `knowledge_entry`：`entry_id CHAR(32)` PK、`kb_id` FK → `knowledge_base` `ON DELETE CASCADE`、`code` / `code_key`、`type`（`term` / `entity` / `state` / `rule` / `process` / `api` / `domain_event` / `other`）、`title`、`summary`、`body` / `body_missing`、`body_source_file`、`fields` / `tables` / `code_paths` / `neighbors` / `extras`（`sa.JSON`）、`source_doc` / `anchor`、`freshness_at`、`content_digest`、`created_at`。
  - 索引：`UNIQUE(project_id, name_key, current_flag)`、`UNIQUE(project_id, name_key, version)`、`UNIQUE(kb_id, code_key)`；`(project_id, current_flag)`、`(project_id, name_key)`、`(code_key)`、`(kb_id, type)`。
  - 可移植写法：大文本用 `Text().with_variant(MEDIUMTEXT(), "mysql")`；JSON 用 `sa.JSON` 且不建索引/不做 `JSON_EXTRACT`；大小写唯一性靠应用层写入 `casefold` 后的 `*_key`，不依赖列 collation；`current_flag` 用 `'1'` / `NULL`，让两方言的可空唯一索引都成立；SQLite 连接建立时统一 `PRAGMA foreign_keys=ON`。
- **来源**：重构自来源 ADR-030（`_handoff/from-tech-arch.md` 第 1 节），按当前需求复核
- **状态**：✅ 已锁定
- **理由**：AC-012-1 / AC-012-4 / AC-013-2 / AC-015-2 要求条目可单条检索、详情可展示字段/表/代码路径/邻居；`AMB-017` 要求版本快照只读保留。双方言纪律来自 core ADR-015 ~ ADR-017 与 `RISK-021`：`TEXT` 在 MySQL 仅 64KB 会静默截断，必须用 `MEDIUMTEXT` 变体。
- **影响**：单条正文上限由单文件 10MB 隐含约束（< 16MB `MEDIUMTEXT`）；迁移编号顺延 core 链——core 的 `0006` 用于 OQ-ARCH-101 的 `ai_call_record` 扩展，本 spec 首个迁移为 `0007`（`down_revision = 0006`），保持单一线性历史。
- **取代**：无

### ADR-104：版本化、命名推导与唯一性

- **决策**：一个 `knowledge_base` 行 = 一个版本快照。名称按序推导（表单 `name` → 顶层 `name` → `meta.name` → `meta.source.files[0].path` 的父目录名 → `知识库 <graph_fingerprint 前 8 位>` → `知识库 <index.json sha256 前 8 位>`）；`name_key` 相同即进入版本链。同项目同名重导时对同名逻辑库取行锁（MySQL `SELECT ... FOR UPDATE`；SQLite 串行写）后 `version = max + 1`，旧行置 `status='superseded'`、`current_flag=NULL`、`superseded_by_kb_id=<新行>`，不询问覆盖。当前版本一律按 `project_id + current_flag='1'` 查询；旧版本只读，提供「查看最新版本」跳转。
- **来源**：重构自来源 ADR-029 / ADR-037，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-012-1` / `AC-012-6` / `AC-013-4` / `AC-REQ-24` 与 `AMB-017` 要求同项目名称唯一、同名重导生成新版本、浏览默认最新版；行锁避免两个并发导入拿到同一个 `version`。
- **影响**：两个导入并发撞上唯一约束时重试 1 次，仍冲突返回 409 `kb_name_conflict`（不是用户可见的业务分支，只是并发保护）；删除按逻辑库（`project_id + name_key`）整体删除，不支持单独删某个历史版本。
- **取代**：无

### ADR-105：文件落盘根、服务端命名与导入原子性

- **决策**：
  - 根目录 `$AW_DATA_DIR/knowledge-bases/`，与 core 的 `sessions/` 平级且互不跨根引用；每个知识库 `<kbId>/{index.json, docs/, manifest.json}`；导入暂存 `knowledge-bases/.staging/<importToken>/`（与目标同文件系统，支持原子 rename）。
  - 客户端文件名只用于展示、正文匹配与清单，**绝不拼进路径**；落盘名 = `sha256(内容)[:16] + "__" + slug(原名)`，slug 去路径分隔符/控制字符/首尾点、长度 ≤80；所有写入前用 `Path.resolve()` 校验仍在 `knowledge-bases/` 根内。
  - 导入顺序固定：流式写 `.staging/`（边写边校验扩展名、单文件/单次/合计字节、文件数，超限立即中止）→ 解析 `index.json` 与 `.md` → 取版本号 → `rename` 到 `knowledge-bases/<kbId>` → 单事务写 KB 行 + 条目（按累计 ≤8MB 分块 `executemany`）→ 提交。
  - 失败清理：②~⑥ 任一步失败 → 回滚 + 删除目录，不留半成品；进程崩溃留下的「有目录无 DB 行」由启动扫描清理（目录 mtime 早于 1 小时才删，只记数量日志）。
- **来源**：重构自来源 ADR-031，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-012-7` / `AC-REQ-18` / `AC-REQ-19` 要求失败整体回滚、0 残留；`AC-016-1` 要求删除时文件一并删除；`RISK-018` 要求阻断路径穿越。
- **影响**：`scripts/backup.sh` 需覆盖 `knowledge-bases/`（core ADR-019 的扩展）；恢复顺序为 DB 快照 → 文件目录，恢复后用 `manifest.json` 核对 sha256；磁盘余量不足时导入提前失败并返回 `kb_import_too_large` / `kb_write_failed`。
- **取代**：无

### ADR-106：`index.json` 解析契约与解析护栏

- **决策**：
  - 最小结构：顶层对象 + 非空字符串 `schema`（版本标识，接受任意非空值）+ 非空数组 `entries`；缺任一 → 整包拒绝 `index_json_invalid`，不建库。
  - 类型按编号前缀映射，**不信任条目自带的 `type`**：`TERM→term`、`ENT→entity`、`ST→state`、`BR→rule`、`BP→process`、`API→api`、`DE→domain_event`，其他前缀 → `other`。
  - 条目级校验：编号必填、≤128、`^[\w一-鿿][\w一-鿿.\-]{0,127}$`（Unicode）；`fields` / `tables` / `code_paths` 必须是对象 / 字符串数组 / 字符串数组；`code_key` 重复保留首条。不合法条目**跳过**并写 `import_report.skippedEntries[{index, line?, code?, reason}]`（固定枚举码，最多 200 条 + `truncated`），行号为尽力而为（定位 `"id": "<code>"` 首次出现位置；找不到回退 `entries[<index>]`）。
  - 解析护栏：`json.loads` 禁用 `NaN/Infinity`（`parse_constant` 抛错）、捕获 `RecursionError`、解析后校验深度 ≤32；文件必须真为 UTF-8；不做压缩包解包；条目上限 20,000；`neighbors` 最多 200 条（超出截断并记报告）；未建模键（`extra` / `aliases` / `module` / 各类型快捷数组等）合并进 `extras`，规范 JSON >64KB 则丢弃并记报告；生成时间取 `meta.source.exported_at`（兼容顶层 `generated_at`），缺失或非 ISO 8601 即 `NULL`（界面「未知」，不推断）；条目新鲜度接受可选 `freshness_at` / `updated_at`，未提供即「未知」。
  - 整体失败：JSON 语法错误 / 缺最小结构 / 全部条目被跳过 → 400 并事务回滚，不做空库。
- **来源**：重构自来源 ADR-032，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-012-2` / `AC-012-3` / `AC-012-4` / `AC-012-5` / `AC-REQ-19` 要求按编号建索引、部分跳过可继续、无条目则整体失败；`RISK-018` 要求挡住巨型 JSON、深层嵌套与 `NaN` 造成的资源耗尽。阈值取「单库 `index.json` ≤20MB + 单文件 ≤10MB」的实测上限：20,000 条已覆盖本体导出规模，深度 32 远超正常导出结构。
- **影响**：解析器为独立纯函数模块（`src/workbench/knowledge/index_parser.py`），无 DB 依赖、可直接单测；`import_report` 只存原因码与数量，不回显原值。
- **取代**：无

### ADR-107：正文匹配与「正文缺失」降级

- **决策**：正文只来自上传的 `.md` / `.markdown`。匹配优先级：①文件名去扩展名后 `casefold` 等于某条 `code_key` → 整文件为正文；②否则逐行扫描 `^### (\S+)\s*$` 标题，命中编号的区块（到下一条 `## ` / `### ` 或文件尾）为正文。同一编号命中多处 → 取「文件名升序 + 偏移最小」的一处，其余记 `import_report.duplicateBodies`；未匹配任何编号的 md 仍保存并记 `unmatchedFiles`。正文去首尾空白后为空视为缺失：`body_missing=true`，详情与注入一律用摘要并标「正文缺失」。正文按纯文本存储与展示，不渲染 HTML/Markdown。
- **来源**：重构自来源 ADR-033，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-013-2` / `AC-013-5` / `AC-REQ-20` 要求正文缺失时展示摘要且不推测；`BR-C18` 与 `RISK-017` 要求内容按不可信输入处理、不渲染 HTML。
- **影响**：同一编号出现在不同 `.md` 中不做合并；正文缺失不是错误，不影响导入成功与注入（注入用摘要）。
- **取代**：无

### ADR-108：检索策略——可移植 `LIKE` + 明确性能边界

- **决策**：首期用可移植的 `LIKE '%q%'`：查询串转义 `%` / `_` / `\` 并显式 `ESCAPE '\'`；`q` 长度 1..100；默认只搜当前版本（`current_flag='1'`），旧版本经版本选择器单独浏览。排序：`code` 精确 > `code` 前缀 > `title` > `summary` > `body`；分页 `limit` 默认 50 / 上限 200，`cursor` 为 base64url 的 `{rank, code, entryId}`。分栏计数 `countsByType` 与主查询共用 `project` / `kbId` / `q` 条件、忽略 `type`，一次聚合返回。**不做** MySQL FULLTEXT（ngram）/ SQLite FTS5 / 向量检索。
- **来源**：重构自来源 ADR-036，按当前需求重新论证（已知未决项之一）
- **状态**：✅ 已锁定
- **理由**：`AC-013-1` / `AC-013-3` / `AC-REQ-20` 要求编号前缀、完整编号与关键词（标题/摘要/正文）检索。可接受性论证：单用户、单进程；单库 `index.json` ≤20MB、单库文件合计 ≤100MB、条目 ≤20,000，且默认只搜当前版本，扫描范围有天花板；编号前缀/完整编号查询先命中 `code_key` 索引，只有关键词检索才需要扫 `title` / `summary` / `body`。双方言行为差异（MySQL `ai_ci` 对 ASCII 不敏感、SQLite `LIKE` 只对 ASCII 不敏感）写入验收说明，不承诺非 ASCII 拉丁大小写一致。升级门禁：任一项目当前版本条目 >50,000，或检索 p95 >500ms，或单项目体感明显变慢 → 按扩展计划切 FULLTEXT / FTS5，接口与 `content_digest` 不变。
- **影响**：关键词检索在大库上可能是秒级；这是本期明确的取舍，不承诺全文索引级性能。若上线后触发门禁，只替换服务层实现，不改 HTTP 契约与表结构。
- **取代**：无

### ADR-109：注入组装与 200,000 字符预算收口

- **决策**：唯一组装入口 `KnowledgeInjectionService.preview(...)` / `prepare(...)`（同一实现，`preview` 不落库）。模板固定为：`【知识库上下文】` → 每库一行 `知识库：<name> v<version>（生成时间：<ISO8601|未知>）` → 每条 `### <code> <title>` + 正文（缺失则摘要 + 「（正文缺失）」）。字符口径为 Unicode 码点（Python `len` / 前端 `[...text].length`，换行与空格计入）；`injected_chars` = 注入块全文（含编号、标题与分隔符），`total_chars = injected_chars + prompt_chars`。上限直接引用 core 的 `AW_PROMPT_MAX_CHARS`（200,000），**本 spec 不重复定义常量**。超限拒绝且不截断：领域错误 `prompt_budget_exceeded`，`details` 返回 `promptChars / injectedChars / totalChars / limit`。`AiGateway.complete` 仍是最终校验点；preview 只供界面实时反馈，发起调用时服务端必须重算。
- **来源**：重构自来源 ADR-034，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-014-1` / `AC-014-3` / `AC-REQ-21`、`AMB-015`、`UXAMB-001` 要求实时字数、分段展示与不截断；`RISK-020` 要求避免多域各自拼提示造成预算漂移。前端按同一模板镜像计数用于即时反馈，但最终值以服务端 preview/prepare 为准。
- **影响**：模板任何改动都同步影响前端计数与测试基线，必须写在同一处常量/函数并在测试中锁定；注入块大小随条目正文线性增长，单条 10MB 正文必然触发超限，这是预期行为。
- **取代**：无

### ADR-110：失效条目在发起前剔除，并做精确匹配的阻塞式确认

- **决策**：发起调用前统一重校验选中项：
  - 失效定义 = 所属知识库已删除 / 编号不存在 / 所选条目所属版本已被取代（`status='superseded'` 或 `current_flag IS NULL`）。
  - core 的 `POST /api/v1/sessions/{sessionId}/ai/complete` 收到 `knowledgeRefs` 后调用本 spec 的 `KnowledgeInjectionService.prepare_for_call(...)` 重算有效集与失效集。若失效集非空且请求未携带与失效集**完全相等**的 `confirmInvalidCodes`，服务抛出 `knowledge_invalid_entries`，由 core 映射为 409，`details` 列出全部 `{kbId, code, reason}`，**不发起外部请求、不写 AiCallRecord**。
  - 用户确认后，前端原样回传失效编号集合；core 再次调用同一服务并要求集合完全一致（防止 preview 与调用之间条目状态变化导致确认过期），通过后服务返回用其余有效条目组装好的注入文本与快照，core 再调用 `AiGateway`。
  - 若确认后有效集为空，服务抛出 `knowledge_injection_empty`，由 core 映射为 409，不发起调用（不产生无内容的「空确认」调用）。
  - 取消（前端不发起调用）→ 不产生 AiCallRecord；失效项取消勾选并标「不可用」，其余勾选保留（`UXAMB-002`）。
- **来源**：新增（`AC-014-4` 2026-11-18 按 `AMB-026` 改写；替代来源 ADR-034 中「剔除后照常调用」的旧语义）
- **状态**：✅ 已锁定
- **理由**：改写后的 `AC-014-4` 明确要求「剔除 + 阻塞式确认，确认后才调 `AiGateway` 并写 AiCallRecord；取消则不发起」。精确集合匹配比布尔 `confirm` 标志更难被绕过，也能覆盖「确认期间又发生版本取代」的竞态；`UXAMB-003` 要求不自动刷新选择器、发起前统一校验，此设计正好在发起时收口。
- **影响**：调用流程是两阶段（preview/首次 409 → 确认后重试），前端必须按 `details.invalidItems` 渲染阻塞对话框；core 的 `/ai/complete` 需新增 `knowledgeRefs` / `confirmInvalidCodes` 字段并在调用网关前调用本 spec 服务（OQ-ARCH-103 按 B）；服务端必须对失效集做确定性排序后比较，避免集合顺序造成误判。
- **取代**：无（改写来源 ADR-034 的失效语义；来源条目已随 spec 拆分迁出并在 core 中保留原文）

### ADR-111：注入留痕——扩展 core 的 AiCallRecord 与 SessionEvent

- **决策**：注入快照只记标识与字符数，不复制正文：
  - `ai_call_record` 追加可空列：`knowledge_injection JSON NULL`（`[{kbId, kbName, kbVersion, entryCodes[], injectedChars}]`）、`injected_chars`、`prompt_chars`、`total_chars`。
  - `session_event.type` 增加 `knowledge_injection`，`payload = {items:[{kbId, kbName, kbVersion, entryCodes[], injectedChars}], promptChars, injectedChars, totalChars, excludedCodes[]}`；与调用记录同事务写入。
  - 落库归属（OQ-ARCH-101 = A）：上述列与事件类型扩展由 **core 的迁移 `0006`** 落地，本 spec 只通过 `injection` 参数传快照、只读调用记录，不拥有 core 表迁移。
  - 写入时机（OQ-ARCH-102 = A）：`AiGateway.complete` 追加 keyword-only 可选参数 `injection: InjectionSnapshot | None = None`，在插入 `running` 记录时原子写入列与 `knowledge_injection` 事件；缺省 `None` 时行为与现状完全一致。
  - 读取：`ai_call_record` 不建指向知识库的外键；展示时按 `kbId` 左连接 `knowledge_base` 判定 `kbDeleted=true`，历史记录永不修改（core 的 calls / 时间线序列化暴露 `knowledgeInjection` 与 `kbDeleted`）。
- **来源**：重构自来源 ADR-035，按当前需求复核；落地方式见 `technical-design/answers.md` 2026-11-18 11:23:18（OQ-ARCH-101 A、OQ-ARCH-102 A）
- **状态**：✅ 已锁定
- **理由**：`AC-014-2` / `AC-014-5` / `AC-REQ-21` 要求 AiCallRecord 与 SessionEvent 都能回查知识库名、版本、编号列表与字符数，且正文不入库；`AC-016-2` / `AC-REQ-23` 要求删除知识库后历史记录保留并标「知识库已删除」，因此不能有外键级联。
- **影响**：core 的 `0006` 迁移负责加列与扩 `session_event.type` 的 CHECK（SQLite 需 Alembic batch 重建表），并同步 core 的 database-schema / api-spec / calls 序列化与契约测试；本 spec 的迁移从 `0007` 起，只建知识库两表。`prompt_preview` 仅 200 字符且属于内容字段，不能替代本列。合并前用 core 的契约测试验证列与事件类型存在，启动自检也校验列存在（RISK-108）。
- **取代**：无

### ADR-112：HTTP API 契约沿用 core 风格

- **决策**：基址 `/api/v1`，全部端点受 `require_session` 保护；错误体 `{code, message, details[], requestId}`；列表 `{"items":[...], "nextCursor": ...}`；时间 RFC 3339 UTC；写操作返回资源表示；删除 204。端点清单：

  | 方法 | 路径 | 说明 |
  |------|------|------|
  | POST | `/api/v1/knowledge-bases` | multipart：`projectId` + 可选 `name` + `files[]`；201 返回知识库摘要 + 导入报告 |
  | GET | `/api/v1/knowledge-bases` | 全局列表；`projectId` 可空；`includeSuperseded` 默认 false |
  | GET | `/api/v1/knowledge-bases/{kbId}` | 详情 + 项目 + 版本列表 + 计数 + 导入报告 + `latestKbId`（删除确认所需数据一次取齐） |
  | GET | `/api/v1/knowledge-bases/{kbId}/versions` | 版本列表 + `latestKbId` |
  | DELETE | `/api/v1/knowledge-bases/{kbId}` | 删除逻辑库全部版本（204） |
  | GET | `/api/v1/knowledge-entries` | 全局浏览/检索：`projectId` / `kbId` / `type` / `q` / `includeSuperseded` / `limit` / `cursor`；返回 `countsByType` 与 `total` |
  | GET | `/api/v1/knowledge-bases/{kbId}/entries` | 库内快捷路径（同一实现） |
  | GET | `/api/v1/knowledge-entries/{entryId}` | 详情：正文/摘要、字段、表、代码路径、一跳邻居、来源文件、新鲜度、冲突、版本信息 |
  | GET | `/api/v1/sessions/{sessionId}/knowledge-injection/candidates` | 当前会话项目**当前版本**条目 + 徽标（供注入选择器） |
  | POST | `/api/v1/sessions/{sessionId}/knowledge-injection/preview` | 只读预览：`{refs, userPrompt}` → 分段字符数、失效项、警告、`overLimit`；不落库、不调用模型 |

  **不新增注入调用端点**（OQ-ARCH-103 = B）：调用入口唯一为 core 的 `POST /api/v1/sessions/{sessionId}/ai/complete`。其请求体在 core 的 api-spec 中追加可选字段 `knowledgeRefs: [{kbId, code}]` 与 `confirmInvalidCodes: string[]`；core 在调用 `AiGateway` 前调用本 spec 的进程内服务 `KnowledgeInjectionService.prepare_for_call(project_id, refs, prompt, confirm_invalid_codes) -> PreparedInjection`（含 `text / injectedChars / promptChars / totalChars / items / excludedCodes`），域错误 `knowledge_invalid_entries` / `knowledge_injection_empty` / `prompt_budget_exceeded` 由 core 映射为对应 HTTP 状态与错误体。

  主要错误码：`validation_error(400)`、`kb_not_found(404)`、`entry_not_found(404)`、`project_not_found(404)`、`session_not_found(404)`、`kb_name_conflict(409)`、`knowledge_invalid_entries(409)`、`knowledge_injection_empty(409)`、`prompt_budget_exceeded(400)`、`unsupported_file_type(400)`、`too_many_files(400)`、`file_too_large(400)`、`index_json_missing(400)`、`index_json_invalid(400)`、`kb_import_too_large(413)`、`kb_write_failed(507)`、`session_closed(409)`、`ai_*`（沿用 core 上游错误码）。
- **来源**：重构自来源 ADR-036，按当前需求复核；调用入口见 `technical-design/answers.md` 2026-11-18 11:23:18（OQ-ARCH-103 B）
- **状态**：✅ 已锁定
- **理由**：`AC-012` ~ `AC-016` 需要按项目/知识库/类型筛选、全局检索、版本切换、删除确认数据一次取齐；core 的 `ADR-009` 与分页/错误约定是唯一对外风格，新增域不得自造外层结构。调用入口保持唯一（core 的 `/ai/complete`），知识库只提供进程内校验/组装/预算能力，避免会话页出现两条调用路径。
- **影响**：core 的 `/ai/complete` 请求 schema、错误码与前端调用路径需同步扩展（core api-spec / 前端）；本 spec 新增的对外端点只有知识库读/写与 preview，不新增模型调用端点；tech-design 展开逐字段 schema、`PreparedInjection` 类型与域错误映射；上传端点必须流式读取并在写盘前完成全部限额校验；`q` 与 `limit` 在依赖层统一校验，越界返回 `validation_error`。
- **取代**：无

### ADR-113：前端边界——复用 AppShell/Token，只新增知识库页面与嵌入组件

- **决策**：前端新增 `frontend/src/knowledge/`（routes / pages / components / api / hooks），路由 `/knowledge-bases`、`/knowledge-bases/import`、`/knowledge-bases/:kbId`、`/knowledge-bases/:kbId/entries/:code`；侧边栏「基座管理 → 知识库」入口。全部页面在 core 的 `AuthGate` + `AppShell` 内渲染，**不新增任何 design token**，颜色/字体/间距/圆角/阴影/布局变量一律引用 interaction-design 已定义的 token。会话页的 `KbInjectPicker` + `KbCharBudget` + `KbInvalidEntryDialog` 作为本 spec 组件嵌入 core 会话「发起调用」面板；项目上下文页的 `ProjectKnowledgeSummary` 通过 core 预留的 `data-mount="knowledge-summary"` 挂载，数据来自本 spec 的只读接口。正文/摘要/标题一律按纯文本渲染（`textContent` / React 默认转义），不注入 HTML，不提供源文件下载。
- **来源**：新增（依据 interaction-design `docs/context.md`、`UXAMB-004`、`AC-012-6`）
- **状态**：✅ 已锁定
- **理由**：`AC-012-6` 要求项目上下文页展示关联知识库；`UXAMB-004` 已确认组件由本 spec 提供、core 只留挂载位；`BG-05` 要求复用 core 外壳，避免两套视觉与登录态。`AMB-016` 要求只提示不阻断，徽标与提示由前端展示、判定在服务端。
- **影响**：需要 core 在会话页与项目上下文页各提供一个稳定的挂载点（项目页挂载位已在需求中锁定；会话页组件由 core 的调用面板直接引用本 spec 导出，或由 core 提供同形态挂载位，tech-design 细化）；前端不做正文 Markdown 渲染，代码路径与编号用 `--font-family-mono`。
- **取代**：无

### ADR-114：内容安全与日志边界

- **决策**：知识库内容一律视为不可信输入。①展示层纯文本转义，不渲染 HTML/Markdown、不提供源文件下载；②日志、错误响应、`import_report` 只允许出现 `kbId / entryCode / 文件名 / 行号 / 字符数 / 错误码 / 数量`，原因用固定枚举文案，不回显原文；③解析器异常不原样透传，统一映射为错误码；④`AiCallRecord` 不存正文/摘要/字段值；⑤上传文件名只用于展示与匹配，不参与路径；⑥所有落盘写入前 `resolve()` 包含校验。
- **来源**：重构自来源 ADR-039，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-014-5` / `AC-REQ-21` / `BR-C18` / `RISK-017` / `RISK-018` 要求正文与注入内容不出现在日志与错误响应；知识库来自本地工具导出，可能含内部实现细节。
- **影响**：新增日志脱敏测试（断言日志与错误体不含正文片段）；错误处理器统一构造，不接受解析器原始异常文本；前端错误展示只显示 `message` 与字段级 `details`。
- **取代**：无

### ADR-115：限额与配置项

- **决策**：`AW_KB_MAX_INDEX_BYTES=20MB`、`AW_KB_MAX_FILE_BYTES=10MB`、`AW_KB_MAX_FILES=50`、`AW_KB_MAX_TOTAL_BYTES=100MB`、`AW_KB_MAX_ENTRIES=20000`、`AW_KB_MAX_JSON_DEPTH=32`、`AW_KB_MAX_NEIGHBORS=200`、`AW_KB_MAX_EXTRAS_BYTES=65536`、`AW_KB_STALE_DAYS=30`、`AW_KB_CONFLICT_SOURCES=20`、`AW_KB_REPORT_MAX_ITEMS=200`。`AW_PROMPT_MAX_CHARS=200000` **从 core 的 settings 读取，不在本 spec 重复声明**。超限一律拒绝并报实测值/上限，不截断；唯一例外是展示性字段 `neighbors` / `extras` 按上述规则截断/丢弃并记报告。测试通过环境变量覆盖为小值。
- **来源**：重构自来源 ADR-040，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-012-2` / `AMB-014` / `AMB-015` 已把用户可见上限定死；其余是解析护栏，取来源 spec 的实测默认值，既覆盖正常本体导出又挡住恶意输入。
- **影响**：所有阈值集中在 `config`（pydantic-settings），不得散落魔法数字；修改默认值只影响新导入，已有数据不重算。
- **取代**：无

### ADR-116：新鲜度与版本冲突只提示不阻断

- **决策**：`freshness_at` 缺失 → `unknown`（未知）；早于 `now - AW_KB_STALE_DAYS` → `stale`（可能过期）；否则 `fresh`。冲突判定：同项目内（含已被取代版本）存在相同 `code_key` 且 `content_digest` 不同 → 标「版本冲突」，列出 `{kbName, version, generatedAt}`（最多 20 条）。`content_digest = sha256(归一化摘要)`：去首尾空白 + 连续空白压成一个空格，缺失为空串；只比摘要文本，不含正文/标题/结构化字段。列表页只对当前版本结果标 `hasConflict`，详情页列冲突来源；按 `code_key IN (...)` 批量查询，不做逐行 N+1。新鲜度与冲突**只提示不阻断**；不克隆仓库、不解析代码校验新鲜度。
- **来源**：重构自来源 ADR-037，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-015-1` / `AC-015-2` / `AC-015-3` / `AC-015-4` / `AC-REQ-22` 与 `AMB-016`；`BR-C19` 明确只提示。冲突口径只比摘要，避免正文差异把同一业务结论误判为冲突。
- **影响**：冲突查询随项目规模增长，需要 `code_key` 索引与批量查询；`content_digest` 写入后不重算，摘要变更只可能来自新导入；已删除知识库的条目不再参与冲突（历史记录中的编号仍按快照展示）。
- **取代**：无

### ADR-117：删除语义与保留策略

- **决策**：`DELETE /knowledge-bases/{kbId}` 删除**逻辑知识库**（`project_id + name_key` 命中的全部版本）：单事务删除 `knowledge_base` 行（条目 FK 级联）；提交后把各版本目录 `rename` 进 `AW_DATA_DIR/.trash/<kbId>-<ts>/` 并尽力删除，失败只记日志并保留 trash 供启动清理。历史 `session_event` / `ai_call_record` / 制品**不修改**（无外键指向知识库），读取时按 `kbId` 左连接标「知识库已删除」。不支持单独删除历史版本；知识库永久保留，不做自动过期或自动清理。删除为高风险操作，前端必须二次确认并列出级联范围。
- **来源**：重构自来源 ADR-038，按当前需求复核
- **状态**：✅ 已锁定
- **理由**：`AC-016-1` / `AC-016-2` / `AC-016-3` / `AC-REQ-23` 与 `AMB-018`、`BR-C20`：级联删除当前数据、历史记录不变、永久保留。先提交 DB 再清文件，保证「列表不再出现」不被文件系统失败阻塞；反向顺序则可能出现「文件已删但 DB 行还在」的可见损坏。
- **影响**：删除失败可能留下 `.trash` 目录（可由启动扫描清理）；删除后历史记录中的编号仍可读，仅标「知识库已删除」；备份恢复后已删除知识库可能「复活」，以 DB 快照为准（文档写明恢复语义）。
- **取代**：无

### ADR-118：测试与门禁

- **决策**：沿用 core 的 pytest preset 与 TC 命名规则（用例名带 TC 编号）；SQLite 用临时文件库（WAL + `busy_timeout`）跑默认套件，MySQL 由 CI service 容器跑同一套用例；解析器、正文匹配、字符预算为纯函数单测；导入/检索/注入/删除为 API 级测试；AI 调用用假适配器或替换 `AiGateway` 的测试实现，不发起真实外部请求；限额通过环境变量覆盖为小值；日志与错误体做「不含正文片段」断言；双方言迁移从空库到 head 各跑一次。
- **来源**：新增（依据 core ADR-041 测试门禁与 `RISK-021`）
- **状态**：✅ 已锁定
- **理由**：`AC-012` ~ `AC-016` 与 7 条 EARS 都需要可重复、无外部依赖的验证；双方言漂移是 core 已识别的 Critical 风险，知识库新增两张表与一次 CHECK 变更，必须两方言都验证。
- **影响**：CI 需要 MySQL 服务（与 core 相同）；测试不得依赖本机 `$AW_DATA_DIR` 真实数据；注入类测试要覆盖「确认后调用 / 取消不调用 / 确认过期再 409」三条路径。
- **取代**：无

## 约束条件

- 不得修改 core 的冻结签名：`AiGateway.complete(session_id, model_id, prepared, *, temperature, max_tokens)`、`sessions.create` / `sessions.append_event`、`artifacts.save`；需要扩展时走 `open-questions.md`，不得在代码里私自加参数。
- `AW_PROMPT_MAX_CHARS`（200,000）由 core 单点定义，本 spec 引用同值，不重复声明。
- 单用户、单进程部署；所有端点受 `require_session` 保护；不新增匿名端点、不新增 HTTP 客户端、不新增凭据读取。
- 错误体固定 `{code, message, details[], requestId}`；分页固定 `limit` + `cursor`；时间 RFC 3339 UTC；ID 与 core 保持各自表内类型（知识库侧为 `CHAR(32)` hex）。
- 双方言纪律：只用 SQLAlchemy 通用类型与差异清单内的写法；新增迁移必须同时通过 SQLite 与 MySQL；`session_event.type` 的 CHECK 变更在 SQLite 用 batch 模式重建。
- 知识库内容视为不可信输入；正文/摘要/字段值不得进入日志、错误响应与 AiCallRecord；正文按纯文本展示。
- 文件只写入 `$AW_DATA_DIR/knowledge-bases/` 与 `.trash/`，不跨根引用 `sessions/`；客户端文件名不参与路径。
- 知识库归属项目（0..n），同项目名称唯一；删除逻辑库不触碰历史会话、制品与调用记录。
- 迁移链顺延 core：core 的 `0006` 为 `ai_call_record` / `session_event` 的扩展迁移（OQ-ARCH-101 A），本 spec 的首个迁移为 `0007`，`down_revision = 0006`，保持线性历史。
- 未安装任何 AlonWorkflow pack（`packs` 为空），未套用 pack 专属约定；如需对应约定可 `alonwf pack add <pack>` 后重跑本阶段。

## 状态

architecture-locked

> 本状态在用户在对话中确认 tech-arch 阶段后生效；OQ-ARCH-101 ~ 103 已拍板并写入 ADR-111 / ADR-112，无阻塞项。
