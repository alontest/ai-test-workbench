# Handoff：知识库技术架构（原 workbench-core ADR-029 ~ ADR-040）

- 来源 spec：`specs/ai-test-workbench_20261117184149`（module `ai-test-workbench`，域 `workbench-core`）
- 迁出依据：用户 2026-11-17 20:50:31 决策「拆 3 个」（workbench-core / knowledge-base / repo-integration）。
- 迁出时间：2026-11-17（tech-arch 阶段收窄）。来源 spec 的 ADR 清单**保留 ADR-029 ~ ADR-040 编号**并标注「已迁出至 knowledge-base spec」，正文以本文件为准。
- 本文件是迁出时的**技术方案原文抽取**：表结构、索引、接口签名、解析护栏、检索方案、限额、风险均可直接照此扩写本 spec 的 tech-arch / tech-design，不需回看来源 spec。
- 状态：知识库相关决策在来源 spec 中为「已确认」，但因 spec 拆分与仓库集成返工，来源 spec 整体退回 draft；本文件内容作为本 spec 的技术输入，仍须由本 spec 用户重新确认。

---

## 1. 数据模型

### 1.1 `knowledge_base`（一行 = 一个版本快照）

| 字段 | 类型（统一写法） | 约束 / 说明 |
|------|------------------|-------------|
| `kb_id` | `CHAR(32)` | PK，服务端 uuid4 hex |
| `project_id` | `CHAR(32)` | FK → `project_context` `ON DELETE RESTRICT`；知识库归属项目 |
| `name` | `VARCHAR(200)` | 展示名，导入时按第 4 节推导（界面无名称输入框） |
| `name_key` | `VARCHAR(200)` collate `utf8mb4_bin` | `casefold(trim(name))`，项目内唯一性依据 |
| `version` | `INTEGER` | 从 1 起，同名逻辑库 `max+1` |
| `current_flag` | `CHAR(1) NULL` | 当前版本 `'1'`，历史版本 `NULL` |
| `status` | `VARCHAR(20)` | `ready` / `superseded`；导入失败不落库 |
| `index_generated_at` | `DATETIME(6) NULL` | 来自 `index.json`，缺失为「未知」 |
| `entry_count` / `file_count` | `INTEGER` | 成功入库条目数 / 本次上传文件数（删除确认框展示） |
| `total_byte_size` | `BIGINT` | 本次上传文件实际字节合计（≤100MB） |
| `source_index_sha256` | `CHAR(64)` | `index.json` 原文摘要 |
| `storage_dir` | `VARCHAR(191)` | 相对 `AW_DATA_DIR`，如 `knowledge-bases/<kbId>` |
| `superseded_by_kb_id` | `CHAR(32) NULL` | 自引用新版本，供「查看最新版本」跳转 |
| `import_report` | `JSON NULL` | 跳过条目/未匹配文件/重复正文（结构原因码，不含正文） |
| `created_at` / `updated_at` | `DATETIME(6)` | 应用层写 UTC |

### 1.2 `knowledge_entry`（一行 = 一个编号）

| 字段 | 类型（统一写法） | 约束 / 说明 |
|------|------------------|-------------|
| `entry_id` | `CHAR(32)` | PK |
| `kb_id` | `CHAR(32)` | FK → `knowledge_base` `ON DELETE CASCADE` |
| `code` / `code_key` | `VARCHAR(128)` / `VARCHAR(128)` collate `utf8mb4_bin` | 原名 / `casefold` 归一，库内唯一 |
| `type` | `VARCHAR(20)` | 由编号前缀映射，见第 4 节 |
| `title` | `VARCHAR(500)` | `zh_name` 优先，否则 `name` |
| `summary` | `MEDIUMTEXT`（MySQL 变体） | `zh_definition` → `description` → `content`，不截断 |
| `body` / `body_missing` | `MEDIUMTEXT NULL` / `BOOLEAN` | 正文；缺失时 `NULL` + `true` |
| `body_source_file` | `VARCHAR(255) NULL` | 命中的 `.md` 原始文件名 |
| `fields` / `tables` / `code_paths` / `neighbors` / `extras` | `JSON NULL` | 结构化字段、表、代码路径、一跳邻居、未建模键 |
| `source_doc` / `anchor` | `VARCHAR(100)` / `VARCHAR(200)` | 上游溯源信息 |
| `freshness_at` | `DATETIME(6) NULL` | 条目新鲜度，缺失 = 未知 |
| `content_digest` | `CHAR(64)` | 冲突判定用：摘要归一化后的 sha256 |
| `created_at` | `DATETIME(6)` | 入库顺序依据 |

### 1.3 关系与完整性

- `ProjectContext 1 ─ n KnowledgeBase 1 ─ n KnowledgeEntry`；
- `knowledge_base.superseded_by_kb_id → knowledge_base.kb_id`（可空）；
- 条目无反向引用；AiCallRecord / SessionEvent **不建外键**指向知识库，删除知识库不触碰历史。

### 1.4 唯一性与索引

- `UNIQUE(project_id, name_key, current_flag)`：保证「同项目同时只有一个当前版本」；
- `UNIQUE(project_id, name_key, version)`：防版本重号；
- `UNIQUE(kb_id, code_key)`：防库内编号重复；
- `knowledge_base(project_id, current_flag)`、`(project_id, name_key)`；
- `knowledge_entry(code_key)`、`(kb_id, type)`；
- 所有被索引的 `VARCHAR` 长度 ×4 字节 < 3072 字节上限。

`current_flag` 用 `'1'`/`NULL` 而非 `'1'`/`'0'`，因为 MySQL 与 SQLite 的唯一索引都允许多个 NULL。不使用 partial index / 生成列（方言专属，破坏双库同构）。

### 1.5 双方言写法差异

| 关注点 | MySQL 8.4 | SQLite | 统一写法与纪律 |
|--------|-----------|--------|----------------|
| 大文本 | `TEXT` 仅 64KB，非严格模式静默截断 | `TEXT` 无长度限制 | `Text().with_variant(MEDIUMTEXT(), "mysql")`（2^24 字节 > 单文件 10MB）；应用层仍校验长度 |
| 结构化字段 | 原生 `JSON`，不能直接建索引 | `TEXT` 存 JSON | `sa.JSON`，不按 JSON 内字段过滤/建索引 |
| 唯一 + 可空 | 唯一索引允许多个 NULL | 同 | `current_flag` 可空标志位 |
| 大小写唯一 | 列 collation `utf8mb4_bin` | 默认 `BINARY` | 存 `casefold` 后的 `name_key`/`code_key`，不依赖列 collation |
| 外键级联 | InnoDB 支持 | 需 `PRAGMA foreign_keys=ON` | 连接建立事件统一开启 |
| 模糊检索 | `LIKE` 受列 collation（`ai_ci`，ASCII 不敏感） | `LIKE` 仅 ASCII 不敏感 | 查询串转义 `% _ \` + `ESCAPE '\'`；大小写差异写入验收说明 |
| 时间 / ID | `DATETIME(6)` / `CHAR(32)` | ISO 文本 / `TEXT` | 应用层写 UTC；ID 服务端生成；禁 `NOW()` |

---

## 2. 文件布局与导入流程

```text
$AW_DATA_DIR/
  sessions/<sessionId>/...                 # 制品（core 既有，ADR-006）
  knowledge-bases/
    <kbId>/
      index.json                           # 原文，原样保存
      docs/<sha256前16>__<slug>.md         # 原文，服务端命名
      manifest.json                        # 文件清单 + sha256 + 版本元数据
    .staging/<importToken>/...             # 导入暂存（同文件系统，可原子 rename）
  .trash/                                  # 制品/知识库删除中转（既有）
  workbench.db                             # 仅开发/测试
```

- **隔离**：知识库根与 `sessions/` 平级，路径不得跨根引用；客户端文件名只用于展示、正文匹配与清单，**绝不拼进路径**。
- **命名**：`sha256(内容)[:16] + "__" + slug(原名)`；slug 去路径分隔符、控制字符与首尾点，长度 ≤80；同名上传靠内容摘要自然去重。
- **清洗规则**：去首尾空白、长度 ≤255、禁止 `/ \ NUL`、禁止 `.`/`..`、禁止以 `~` 开头，不满足即逐项拒绝。
- **路径校验**：所有落盘写入前用 `Path.resolve()` 校验仍在 `knowledge-bases/` 根内。
- **导入顺序**：
  1. 流式写 `.staging/`（边写边校验扩展名、单文件/单次/合计字节、文件数，超限立即中止并返回逐项原因）；
  2. 解析 `index.json` 与 `.md`；
  3. 取版本号（同名取行锁：MySQL `SELECT ... FOR UPDATE`，SQLite 串行写）；
  4. `rename` 到 `knowledge-bases/<kbId>`；
  5. 单事务写 KB 行 + 条目（按累计 ≤8MB 分块 `executemany`）；
  6. 提交。
- **失败与清理**：②~⑥ 任一步失败 → 回滚 + 删除目录，接口返回错误，**不留半成品**（AC-012-7）；进程崩溃留下的「有目录无 DB 行」在启动扫描中清理（目录 mtime 早于 1 小时才删，只记数量日志）。
- **容量**：单库 ≤100MB（`total_byte_size` 落库前复核），磁盘余量不足时提前失败；`.trash` 由既有清理逻辑回收。
- **备份**：`scripts/backup.sh` 需覆盖 `knowledge-bases/`；恢复顺序为 DB 快照 → 文件目录，恢复后用 `manifest.json` 核对 sha256（扩展来源 spec ADR-019 范围）。

---

## 3. 解析契约与护栏

### 3.1 最小结构（缺任一 → 整包拒绝 `index_json_invalid`）

顶层对象 + 非空字符串 `schema`（版本标识，接受 `ontology-views/1` 等任意非空值）+ 非空数组 `entries`。

```json
{
  "schema": "ontology-views/1",
  "meta": {
    "tool": "ontology-consumption",
    "fingerprint": "<图谱文件 sha256>",
    "graph_fingerprint": "<图谱内容 sha256>",
    "source": {"exported_at": "2026-09-28T00:00:00Z"},
    "warnings": []
  },
  "entries": [
    {
      "id": "ENT-payment-order",
      "name": "PaymentOrder",
      "zh_name": "支付订单",
      "description": "…",
      "zh_definition": "…",
      "content": "…",
      "fields": {"order_id": "string"},
      "tables": ["payment_order"],
      "code_paths": ["src/pay/order.py"],
      "neighbors": [
        {"id": "ST-order-created", "relation": "has_state",
         "relation_name": "拥有状态", "dir": "out"}
      ],
      "freshness_at": "2026-09-01",
      "source_doc": "payment-domain.md",
      "anchor": "ent-payment-order",
      "extra": {}
    }
  ]
}
```

### 3.2 字段与报告规则

| 规则 | 处理 |
|------|------|
| 编号 `id` | 必填字符串，≤128，`^[\w一-鿿][\w一-鿿.\-]{0,127}$`（Unicode）；缺失/非法 → 跳过该条 |
| 类型 | **按前缀映射**，不信任条目自带 `type`：`TERM→term`、`ENT→entity`、`ST→state`、`BR→rule`、`BP→process`、`API→api`、`DE→domain_event`，其他前缀（`MOD/SYS/PRJ/SA/...`）→ `other` |
| 标题 / 摘要 | 标题 `zh_name` 优先否则 `name`；摘要 `zh_definition` → `description` → `content`（上游有 `content`），摘要列不截断 |
| `fields` / `tables` / `code_paths` | 必须分别为对象 / 字符串数组 / 字符串数组；类型不符 → 跳过该条并记原因 |
| `neighbors` | 保留 `{id, relation, relation_name, dir}`，最多 200 条（超出截断并记报告）；编号不存在不阻止导入，详情标「不可跳转」 |
| 未建模键 | `extra`、`aliases`、`module`、`main_path`、`zh_status` 与各类型快捷数组（`rules`/`states`/`processes`/`apis`/`evidence` 等）归入 `extras`；规范 JSON >64KB 则丢弃并记报告。`meta` 只取 `source.exported_at`，`fingerprint`/`graph_fingerprint`/`warnings` 计数写报告，`node_ids` 不入库 |
| 生成时间 | 取 `meta.source.exported_at`（上游真实字段），兼容顶层 `generated_at`；缺失或无法解析为 ISO 8601 时为 `NULL`（界面「未知」，不推断） |
| 条目新鲜度 | 上游目前不产出条目级新鲜度；`freshness_at` 是可选扩展字段（同时接受 `freshness_at` / `updated_at`），未提供即「未知」 |
| 重复编号 | `code_key` 归一后重复 → 保留首条，后续跳过 |
| 跳过报告 | `import_report.skippedEntries[{index, line, code?, reason}]`，原因用固定枚举码（`missing_id` / `invalid_id` / `duplicate_code` / `invalid_fields_type` …），最多 200 条 + `truncated`；行号为**尽力而为**（定位 `"id": "<code>"` 首次出现位置换算行号，找不到回退 `entries[<index>]`）；JSON 语法错误则整包拒绝并返回解析器给出的行列 |
| 整体失败 | JSON 语法错误 / 全部条目被跳过 / 缺最小结构 → 400，事务回滚，不做空库 |
| 内容摘要 | `content_digest = sha256(归一化摘要)`：去首尾空白 + 连续空白压成一个空格，缺失为空串；**只比摘要文本**，不含正文/标题/结构化字段（AC-015-2 口径） |

### 3.3 正文匹配与「正文缺失」降级

- 正文只来自上传的 `.md` / `.markdown`，匹配优先级：
  1. 文件名去扩展名后 `casefold` 等于某条目 `code_key` → 整文件为正文；
  2. 否则逐行扫描 `^### (\S+)\s*$` 标题，命中编号的区块（到下一条 `## ` / `### ` 或文件尾）为正文。
- 同一编号出现在多个文件 → 取「文件名升序 + 偏移最小」的一处，其余记 `import_report.duplicateBodies`。
- 正文去首尾空白后为空视为缺失：`body_missing=true`，详情/注入一律用摘要，界面标「正文缺失」并展示摘要（AC-013-5、AC-013-2）。
- 未匹配任何编号的 md 文件仍保存（溯源用），记 `import_report.unmatchedFiles`。
- 正文按纯文本存储与展示，**不渲染 HTML/Markdown**（沿用来源 spec ADR-013 的转义口径，防 XSS）；单条正文上限由单文件 10MB 隐含约束（< `MEDIUMTEXT` 16MB）。

### 3.4 安全护栏

- 知识库内容一律视为不可信输入。
- 解析层：`json.loads` 禁用 `NaN/Infinity`（`parse_constant` 抛错）、捕获 `RecursionError`、解析后校验深度 ≤32。
- 上传只接受 `.json` / `.md` / `.markdown` 扩展名且必须真为 UTF-8（解码失败即逐项拒绝）；不做压缩包解包。
- 展示层：正文/摘要/标题按纯文本转义渲染，不注入 HTML，不提供源文件下载接口。
- 日志与错误：只允许出现 `kbId / entryCode / 文件名 / 行号 / 字符数 / 错误码 / 数量`，**不得出现正文、摘要、字段值**；`import_report` 的 `reason` 只用固定枚举文案，不回显原值。
- AiCallRecord 不存正文。
- 解析器为独立模块（建议 `backend/app/knowledge/index_parser.py`），纯函数、无 DB 依赖，可直接单测；`entries` 顺序保留入库顺序。

---

## 4. 知识库名称推导

界面无名称输入框，按序推导（trim 后 ≤200）：

1. 表单 `name`（可选）
2. 顶层 `name`
3. `meta.name`
4. `meta.source.files[0].path` 的父目录名
5. `知识库 <graph_fingerprint 前 8 位>`
6. `知识库 <index.json sha256 前 8 位>`

推导结果 `name_key` 相同即进入版本链，因此同一图谱重复导出会稳定命中同一逻辑库。同项目同名 → 版本 +1，不询问覆盖。

---

## 5. 注入组装接口（供后续域复用）

```python
@dataclass(frozen=True)
class KbEntryRef:          # 用户勾选的条目（版本由 kbId 决定）
    kb_id: str
    code: str

@dataclass(frozen=True)
class InjectionItem:
    kb_id: str; kb_name: str; kb_version: int
    code: str; title: str
    chars: int
    source: Literal["body", "summary"]

@dataclass(frozen=True)
class InvalidItem:         # 失效选中项（被剔除，不阻断其余条目）
    kb_id: str; code: str; reason: str

@dataclass(frozen=True)
class PreparedPrompt:      # 交给 AiGateway 的唯一形态
    text: str              # 注入块 + 用户提示，已拼好
    prompt_chars: int
    injected_chars: int
    total_chars: int
    items: tuple[InjectionItem, ...]        # 实际注入
    invalid_items: tuple[InvalidItem, ...]  # 被剔除
    warnings: tuple[FreshnessWarning | ConflictWarning, ...]
    # 注：原 ADR-034 签名中 PreparedPrompt 未列 items，由 design.md 补全为上述形态

async def prepare(project_id: str, refs: Sequence[KbEntryRef],
                  user_prompt: str) -> PreparedPrompt
async def preview(project_id: str, refs: Sequence[KbEntryRef],
                  user_prompt: str) -> PreparedPrompt   # 同一实现，不落库
```

- **模板**（固定，改动需同步字数基线）：`【知识库上下文】` → 每库一行 `知识库：<name> v<version>（生成时间：<ISO8601|未知>）` → 每条 `### <code> <title>` + 正文（缺失则摘要 + 「（正文缺失）」）。
- **字符口径**：Unicode 码点（Python `len`；前端 `[...text].length`），换行/空格计入；`injected_chars` = 注入块全文（含标题/分隔符），`total_chars = injected_chars + prompt_chars`。
- **失效语义**：选中项「知识库已删除 / 版本已被取代 / 编号不存在」→ **只剔除该条目**并进 `invalid_items[{kbId, code, reason}]`，其余有效条目照常注入、调用照常发起（AC-014-4 阻止的是这些条目本身）；界面在调用前列出具体编号。
- **预算**：`injected_chars + prompt_chars ≤ 200,000`，超限**拒绝且不截断**，领域错误 `prompt_budget_exceeded`，`details` 返回 `promptChars / injectedChars / totalChars / limit`。
- **收口**：预算校验的唯一收口在 `AiGateway.complete(...)`（也校验无注入时 `len(user_prompt) ≤ 200,000`），通过后才写 AiCallRecord、才发起外部请求；超预算不写 AiCallRecord 与事件。
- **留痕**：`AiCallRecord` 增列 `knowledge_injection JSON NULL`（`[{kbId, kbName, kbVersion, entryCodes[], injectedChars}]` 快照）、`prompt_chars`、`injected_chars`、`total_chars`；同事务追加 `SessionEvent(type='knowledge_injection')`（payload 同构）。**只记标识、编号与字符数，不复制正文**。知识库/版本被删后历史记录不更新，读取时按 `kbId` 左连接判定 `kbDeleted=true`，界面用快照名展示并标「知识库已删除」。

---

## 6. API 契约（沿用来源 spec ADR-009 错误体与分页约定）

| 方法 | 路径 | 说明 | 主要错误码 |
|------|------|------|-----------|
| POST | `/api/v1/knowledge-bases` | multipart：`projectId`（必填）+ `name`（可选）+ `files[]`；201 返回 `{kb, importReport:{files[{name,size,accepted,reason?}], skippedEntries[], unmatchedFiles[], duplicateBodies[], counts{files,bytes,entries,skipped}, versionBumped, previousVersion, meta{fingerprint,graphFingerprint,warnings}}}`（部分条目跳过仍是 201） | `kb_name_conflict(409)`、`unsupported_file_type`、`too_many_files`、`index_json_missing`、`kb_import_too_large(413)`、`kb_import_invalid(400)` |
| GET | `/api/v1/knowledge-bases?projectId=&includeSuperseded=false` | **全局列表**（项目可空=全部，对齐列表页筛选）；行含 `kbId / name / project{id,name} / version / generatedAt / entryCount / fileCount / status / supersededCount / latestVersion` | — |
| GET | `/api/v1/knowledge-bases/{kbId}` | 详情 + `project` + `versions[]` + `entryCount/fileCount` + `importReport` + `supersededBy/latestKbId`（删除确认框所需数据一次取齐） | `kb_not_found(404)` |
| GET | `/api/v1/knowledge-bases/{kbId}/versions` | 版本列表 `{kbId,version,current,createdAt,generatedAt,entryCount,fileCount}` + `latestKbId` | `kb_not_found` |
| DELETE | `/api/v1/knowledge-bases/{kbId}` | 删除逻辑知识库全部版本，204 | `kb_not_found` |
| GET | `/api/v1/knowledge-entries?projectId=&kbId=&type=&q=&includeSuperseded=false&limit=&cursor=` | **全局检索/浏览**；返回 `items[{entryId,code,title,type,kbId,kbName,kbVersion,superseded,bodyMissing,freshness{at,state},conflict{hasConflict}}]` + `countsByType`（同一 q/项目/知识库、忽略 type 的分栏计数）+ `total` | 参数校验 400 |
| GET | `/api/v1/knowledge-bases/{kbId}/entries?type=&q=&limit=&cursor=` | 库内快捷路径（同一实现） | `kb_not_found` |
| GET | `/api/v1/knowledge-entries/{entryId}` | 详情：`kb{...latestKbId}`、`summary`、`body/bodyMissing/bodySourceFile`、`sourceDoc/anchor`、`fields/tables/codePaths`、`neighbors[{code,title,entryId?,kbId?,exists}]`、`freshness{at,state}`、`conflicts[{kbName,version,generatedAt}]` | `entry_not_found(404)` |
| GET | `/api/v1/sessions/{sessionId}/knowledge-injection/candidates?q=&type=` | 当前会话项目**当前版本**条目 + 徽标，供注入选择器（已删除/被取代不出现） | — |
| POST | `/api/v1/sessions/{sessionId}/knowledge-injection/preview` | `{refs:[{kbId,code}], userPrompt}`（传原文，服务端计字）→ 200 `{items, invalidItems, promptChars, injectedChars, totalChars, limit, warnings, overLimit}` | — |

### 6.1 分页与检索

- 分页：`limit` 默认 50 / 上限 200，`cursor` 为 base64url 的 `{rank, code, entryId}`，保证同排序下稳定翻页。
- 排序：`code` 精确 > `code` 前缀 > `title` > `summary` > `body`。
- 检索实现：可移植 `LIKE '%q%'`（转义 `% _ \`，`ESCAPE '\'`），默认只搜当前版本；`q` 长度 1..100。
- 不做 MySQL FULLTEXT（ngram）/ SQLite FTS5；MySQL 侧大小写不敏感依赖列 collation，SQLite 仅 ASCII —— 写进验收说明，不承诺非 ASCII 拉丁大小写一致。
- 升级路径：`LIKE` 升级为 MySQL FULLTEXT / SQLite FTS5 或向量检索；接口与 `content_digest` 不变。

---

## 7. 版本、新鲜度、冲突与删除

- **版本**：一个 `knowledge_base` 行 = 一个版本快照；同名重导 `version+1`，旧行 `status='superseded'`、`current_flag=NULL`、`superseded_by_kb_id=<新行>`，只读保留；默认只展示当前版本。查当前版本一律 `WHERE project_id=? AND current_flag='1'`。导入需对同名逻辑库取行锁后取版本号，唯一冲突重试 1 次再报 409。历史版本只读并有「查看最新版本」入口（AC-013-4）。
- **新鲜度**：`freshness_at` 缺失 → `unknown`（未知）；早于 `now-30d` → `stale`（可能过期）；否则 `fresh`。**只提示不阻止**（AC-015-4）。
- **冲突**：同项目内（含已被取代版本）存在相同 `code_key` 且 `content_digest` 不同 → 标冲突并列出 `{kbName, version, generatedAt}`（最多 20 条）；列表按 `code_key IN (...)` 批量一次查询，不做逐行 N+1。新鲜度与冲突**只提示不阻止**注入。
- **失效条目**：「所属版本已被取代」与「知识库已删除 / 编号不存在」同属 AC-014-4 的失效条目：发起调用前提示具体编号并阻止使用这些条目，浏览仍可读。
- **删除**：`DELETE /knowledge-bases/{kbId}` 删除**逻辑知识库**（`project_id + name_key` 命中的全部版本）：单事务删 `knowledge_base` 行（条目 FK 级联），提交后把各版本目录 `rename` 进 `.trash/` 并后台删除。历史会话、SessionEvent、AiCallRecord **不变**（无外键指向 KB），读取时左连接判定标「知识库已删除」。不支持单独删除某个历史版本。删除为高风险操作，需覆盖「删除后注入被阻断、历史记录可读」。
- **保留策略**：知识库默认**永久保留**，不做自动过期或自动清理（AC-016-3）。

---

## 8. 限额与配置（默认值即需求值，测试可覆盖小值）

| 配置 | 默认 | 用途 |
|------|------|------|
| `AW_KB_MAX_INDEX_BYTES` | 20MB | `index.json` 单文件 |
| `AW_KB_MAX_FILE_BYTES` | 10MB | 其他单文件 |
| `AW_KB_MAX_FILES` | 50 | 单次文件数 |
| `AW_KB_MAX_TOTAL_BYTES` | 100MB | 单库累计（不是项目累计） |
| `AW_KB_MAX_ENTRIES` | 20000 | 解析护栏 |
| `AW_KB_MAX_JSON_DEPTH` | 32 | 解析护栏 |
| `AW_KB_MAX_NEIGHBORS` | 200 | 一跳邻居截断 |
| `AW_KB_MAX_EXTRAS_BYTES` | 65536 | 未建模键上限 |
| `AW_KB_STALE_DAYS` | 30 | 新鲜度阈值 |
| `AW_KB_CONFLICT_SOURCES` | 20 | 冲突来源条数 |
| `AW_PROMPT_MAX_CHARS` | 200000 | 注入 + 提示合计（与 core 粘贴上限共口径） |
| `AW_KB_REPORT_MAX_ITEMS` | 200 | 导入报告条目上限 |

超限一律**拒绝并报出实测值/上限**，不截断（唯一例外：`neighbors` 与 `extras` 属展示性字段，超限截断/丢弃并记报告）。

---

## 9. 来源 spec 的风险条目（原文迁出）

| ID | 风险 | 类别 | 影响 | 概率 | 评分 | 缓解措施 |
|----|------|------|------|------|------|---------|
| RISK-017 | 知识库正文/摘要/字段值经日志、错误响应或导出泄露（内容含内部实现细节） | 安全 | 高 | 中 | 🔴 Critical | 知识库内容按不可信输入处理；日志与错误只允许 id/编号/文件名/行号/字符数/固定原因码；`import_report` 原因用枚举不回声原值；AiCallRecord 不存正文；用例断言日志与错误体无正文片段 |
| RISK-018 | 导入路径穿越、巨型 JSON/深层嵌套/`NaN` 导致越权写盘、内存或 CPU 耗尽 | 安全 | 高 | 中 | 🔴 Critical | 客户端文件名不参与路径 + 服务端 sha256 命名 + `resolve()` 包含校验；扩展名白名单 + UTF-8 校验；深度 32、条目数与单文件/合计字节上限；禁 `NaN/Infinity`、捕获 `RecursionError`；导入失败整包回滚 |
| RISK-019 | 导入半成品：文件已落盘但 DB 回滚，或 DB 提交但目录缺失 | 技术 | 中 | 中 | 🟡 Medium | 顺序固定为 staging → rename → 单事务写库；失败删目录；启动扫描清理「有目录无行」；`manifest.json` 支持备份核对；用例覆盖各阶段注入失败 |
| RISK-020 | 注入预算误算或绕过（各域自行拼提示、前端估算字数），导致超长请求被模型拒绝或费用失控 | 技术 | 中 | 中 | 🟡 Medium | 唯一组装入口 `KnowledgeInjectionService` + 唯一校验点 `AiGateway`；preview 与 prepare 同实现；字符口径统一为 Unicode 码点；超限错误分段报数；用例覆盖注入含标题/分隔符后的边界 |
| RISK-021 | 双方言差异：`TEXT` 静默截断、JSON 列不能建索引、可空唯一索引语义、`LIKE` 大小写与全表扫描性能 | 技术 | 高 | 中 | 🔴 Critical | 大文本强制 `MEDIUMTEXT` 变体；`sa.JSON` 不建索引；`current_flag` 可空唯一索引在两方言各跑迁移与用例；`LIKE` 转义并限制范围；MySQL `STRICT_TRANS_TABLES` 写进部署自检；性能退化触发 FTS 升级 |
| RISK-022 | 版本取代/删除语义混淆，用户把旧版本条目当作现行结论注入 | 范围 | 中 | 中 | 🟡 Medium | 注入时带知识库名 + 版本 + 生成时间；默认只展示当前版本；旧版本只读并标「已被 vN 取代」；按 AC-014-4 在调用前剔除已被取代的条目并提示具体编号；删除为逻辑库级并二次确认 |

应急预案（原文）：

- **RISK-017**：若发现正文进入日志/错误体，立即在日志出口与错误构造处加白名单字段，禁止透传解析器异常原文；对已产生的日志做一次性扫描；受影响知识库可要求重导。
- **RISK-018**：若出现越界写盘或资源耗尽，立即下线导入入口，修正包含校验/护栏后重跑安全用例；已上传目录按 `manifest.json` 审计并隔离。
- **RISK-021**：若某方言出现截断或唯一索引不生效，立即停止发布并新增修正迁移；已截断的数据按原文重导（不修改历史迁移）。

---

## 10. 来源 spec 扩展计划中的知识库条目（原文）

| 阶段 | 用户规模 | 架构变化 |
|------|---------|---------|
| 知识库规模化 | 单项目多库、检索变慢 | `LIKE` 升级为 MySQL FULLTEXT（ngram）/ SQLite FTS5，或引入向量检索；接口与 `content_digest` 不变 |
| 知识库自动化 | 上游工具直连 | `ontology-builder` 通过内部接口推送 `index.json` + `.md`，替代手工上传；复用同一解析/版本/报告契约 |

---

## 11. 与 core 的依赖边界（本 spec 扩写时必须遵守）

本 spec 的知识库能力运行在 core 之上，以下 core 契约**不得改写**（来源 spec 已冻结名称与语义）：

- `AiGateway.complete(session_id, model_id, prepared: str, *, temperature=None, max_tokens=None)`：唯一模型出口；知识库注入在通过预算校验后由本 spec 组装成纯文本传入；core 负责超时 120s、网络错误与 5xx 重试 1 次、`retryCount` 入库、AiCallRecord 生命周期。
- `sessions.create` / `sessions.append_event`：会话创建与事件追加；知识库侧只调用，不直接写 `SessionEvent` 表。
- `artifacts.save`：制品保存；知识库上传**不复用**制品通道（独立 `knowledge-bases/` 根与独立限额）。
- 认证与访问控制：所有知识库接口默认受 `require_session` 保护，401 统一错误体；不新增匿名端点。
- 错误结构：`{code, message, details[], requestId}`；分页 `limit` + `cursor`；写操作返回资源表示。
- 凭证与加密：本 spec 本期不存第三方令牌（`ontology-builder` 直连为后续阶段）。
- 数据与备份：`AW_DATA_DIR` 增加 `knowledge-bases/` 子根；`scripts/backup.sh` 由本 spec 扩展覆盖。
- 测试门禁：沿用 `pytest` preset；TC 编号命名规则不变。

---

## 12. 迁出清单（供本 spec 对账）

- ADR：来源 spec ADR-029 ~ ADR-040（12 条）——知识库归属与版本化、实体与双方言映射、文件落盘与导入原子性、`index.json` 解析契约、正文匹配与降级、注入组装与预算、注入留痕、API 与检索、新鲜度与冲突、删除语义、安全与日志边界、导入护栏与限额。
- 设计决策：来源 spec `design.md` 决策 11 ~ 13（知识库存储形态与版本化、文件落盘与导入原子性、注入组装与预算收口）。
- 数据表：`knowledge_base`、`knowledge_entry` 及全部索引（本文第 1 节）。
- 接口：`POST/GET/DELETE /api/v1/knowledge-bases*`、`GET /api/v1/knowledge-entries*`、`GET /api/v1/sessions/{sessionId}/knowledge-injection/candidates`、`POST /api/v1/sessions/{sessionId}/knowledge-injection/preview`（本文第 6 节）。
- 组件：`frontend/knowledge`、`backend/services/knowledge`、`backend/knowledge`（解析层）、`KnowledgeInjectionService`。
- 依赖：`python-multipart` 已在 core（制品上传需要），知识库导入复用同一依赖，不新增解析库。
- 非新增依赖结论：`markdown-it-py` / `orjson` / `ijson` / `Pygments` 均未采用；如需 Markdown 渲染再按 classifiers 与仓库 LICENSE 单独评估许可证。
- 风险：RISK-017 ~ RISK-022（本文第 9 节）。
- 扩展计划：知识库规模化、知识库自动化两条（本文第 10 节）。
- 流程约束：导入事务边界、预算收口、留痕口径、内容不可信、方言纪律（本文第 2、3、5、7 节）。
