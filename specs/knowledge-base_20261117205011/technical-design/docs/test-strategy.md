# Test Strategy — knowledge-base

> 阶段：tech-design（补充产出：测试策略与 TC 编号）。依据 ADR-118、`docs/architecture-decisions.md` 约束、`docs/api-spec.md`、`docs/database-schema.md`。
> **编号规则**：core 占 TC-001 ~ TC-070，repo-integration 计划 TC-201 起；本 spec 使用 **TC-101 ~ TC-150**（50 条），用例名统一 `test_tcNNN_<行为>`（如 `test_tc101_rejects_index_without_entries`）。后续新增用例从 TC-151 顺延，不复用编号。

## 1. 测试分层与基础设施

| 层 | 范围 | 设施 |
|----|------|------|
| 纯函数单测 | `knowledge/` 解析层（parser / body matcher / naming / rendering） | 直接调用，无 DB、无 IO；fixture 为内存 bytes |
| 服务级测试 | 导入、查询、注入、删除 | 测试 `Session`（SQLite 临时文件库，WAL + `busy_timeout`）+ 临时 `AW_DATA_DIR`（`tmp_path`） |
| API 级测试 | 10 个知识库端点 + 通过 core `/ai/complete` 的三条注入路径 | `httpx.ASGITransport` + 同一个 `create_app()` fixture；`require_session` 用 core 的登录 fixture 或测试覆盖 |
| 迁移测试 | `0007` 在 SQLite 与 MySQL 各跑一次 | 默认套件 SQLite；CI 追加 MySQL 8.4 service 容器 |
| 安全断言 | 日志与错误体不含正文片段 | `caplog` + 响应体字符串扫描；正文片段用随机哨兵串（如 `SENTINEL-<uuid>`） |
| 前端（P1 可选，不进门禁） | 组件行为与字符预算显示 | Vitest + Testing Library（core 已有配置） |

通用纪律：

- 所有 AI 调用使用 core 的假适配器或替换 `AiGateway` 的测试实现；**不发起真实外部请求**。
- 限额通过环境变量覆盖为小值（如 `AW_KB_MAX_FILES=2`、`AW_KB_MAX_FILE_BYTES=1024`、`AW_KB_MAX_TOTAL_BYTES=4096`、`AW_KB_MAX_ENTRIES=5`），避免生成大文件。
- 每个测试独立 `tmp_path` 与独立数据库文件；不读写本机真实 `$AW_DATA_DIR`。
- 时间相关断言注入固定 `now`（新鲜度阈值用显式时间，不用 sleep）。

## 2. 用例清单（TC-101 ~ TC-150）

| TC | 用例名（简） | 层级 | 覆盖 AC / 规则 | 关键断言 |
|----|-------------|------|---------------|---------|
| TC-101 | `test_tc101_rejects_index_without_schema_or_entries` | 纯函数 | AC-012-3 / AC-REQ-19 | 缺 `schema` / 缺 `entries` / `entries=[]` → `index_json_invalid`，不产生条目 |
| TC-102 | `test_tc102_maps_prefix_to_entry_type` | 纯函数 | AC-012-4 | `TERM/ENT/ST/BR/BP/API/DE` 映射各自类型；`MOD-1` → `other`；忽略条目自带 `type` |
| TC-103 | `test_tc103_skips_invalid_entries_with_line_and_reason` | 纯函数 | AC-012-5 / AC-REQ-19 | 缺编号 / 编号重复 / `fields` 非对象 → 跳过；`skippedEntries[{index,line,code,reason}]` 有行号或回退 index；其余保留 |
| TC-104 | `test_tc104_fails_when_no_entry_importable` | 纯函数 + API | AC-012-5 | 全部跳过 → 400 `index_json_invalid`，不建库、无目录 |
| TC-105 | `test_tc105_enforces_parser_guards` | 纯函数 | AC-REQ-18 / ADR-106 | 深度 33、`NaN`、`Infinity`、`RecursionError`、条目 20,001 → 拒绝并报实测/上限；不 OOM |
| TC-106 | `test_tc106_truncates_neighbors_and_drops_large_extras` | 纯函数 | AC-012-4 / ADR-106 | `neighbors` 保留 200 条并记报告；`extras` 规范 JSON >64KB 丢弃并记报告 |
| TC-107 | `test_tc107_rejects_invalid_json_syntax` | 纯函数 | AC-012-3 | 语法错误 → `index_json_invalid`，带行列（尽力而为），不建库 |
| TC-108 | `test_tc108_derives_name_in_fixed_order` | 纯函数 | AC-012-1 / ADR-104 | 表单名 > 顶层 `name` > `meta.name` > `meta.source.files[0].path` 父目录 > `graph_fingerprint[:8]` > sha256[:8]；`name_key` 大小写归一 |
| TC-109 | `test_tc109_matches_body_by_filename_then_heading` | 纯函数 | AC-013-5 / ADR-107 | 文件名等于 `code_key` → 整文件；否则 `### CODE` 切块；多处命中取文件名升序 + 偏移最小；其余记 `duplicateBodies` |
| TC-110 | `test_tc110_marks_missing_body_as_blank` | 纯函数 | AC-013-5 | 未匹配 / 空白正文 → `body_missing=true`，`body=NULL`，不使用空串冒充 |
| TC-111 | `test_tc111_imports_knowledge_base_and_lists_it` | API | AC-012-1 / AC-012-6 | 201；`kb` 含名称/生成时间（缺失为 null）/条目数/`status=ready`；`GET /knowledge-bases` 可见 |
| TC-112 | `test_tc112_rejects_upload_limit_violations_per_file` | API | AC-012-2 / AC-REQ-18 | 非白名单类型、超单文件、超文件数、超合计、缺 `index.json` → 对应 400/413，`details` 逐项，**无目录、无行** |
| TC-113 | `test_tc113_rolls_back_all_on_failure` | 服务 | AC-012-7 | 在解析后 / rename 后 / 写库时注入异常 → 知识库行 0、条目 0、`knowledge-bases/<kbId>` 不存在、无 staging 残留 |
| TC-114 | `test_tc114_reimport_creates_new_version_and_supersedes_old` | API | AC-013-4 / AC-REQ-24 / AMB-017 | 同名再导 → `version=2`；旧行 `status=superseded`、`current_flag=NULL`、`superseded_by_kb_id` 指向新行；同项目两个 `current_flag='1'` 不可能 |
| TC-115 | `test_tc115_concurrent_import_conflict_returns_409` | 服务 | ADR-104 | 模拟唯一约束冲突 → 重试 1 次；仍冲突 → 409 `kb_name_conflict`，无残留 |
| TC-116 | `test_tc116_client_filename_never_used_as_path` | 服务 | RISK-018 | `../../etc/passwd`、`a/b.md`、控制字符 → 落盘名仍为 `sha256[:16]__slug`；`resolve()` 越界即拒绝 |
| TC-117 | `test_tc117_startup_scan_removes_orphan_dirs` | 服务 | ADR-105 | 仅删除 mtime > 1h 的「有目录无行」；有 DB 行的目录保留；只记数量日志 |
| TC-118 | `test_tc118_lists_entries_by_project_kb_and_type` | API | AC-013-1 / AC-REQ-20 | 三种筛选组合正确；无匹配 → `items=[]`、`total=0`、非错误 |
| TC-119 | `test_tc119_searches_by_code_prefix_exact_and_keyword` | API | AC-013-3 / ADR-108 | 完整编号 rank 最高、前缀次之、标题/摘要/正文命中；`%`、`_`、`\` 被转义；`q` 101 字符 → 400 |
| TC-120 | `test_tc120_paginates_with_stable_cursor_and_counts_by_type` | API | AC-013-1 / AC-013-3 | 翻页不重不漏；`countsByType` 忽略 `type` 条件、共用 project/kbId/q；`limit` 上限 200 |
| TC-121 | `test_tc121_entry_detail_contains_all_fields_and_neighbors` | API | AC-013-2 | 摘要/正文/字段/表/代码路径/邻居/来源文件/新鲜度齐全；邻居存在时带 `entryId`，不存在时 `exists=false` |
| TC-122 | `test_tc122_superseded_entry_points_to_latest` | API | AC-013-4 | 旧版本详情 `kb.superseded=true`、`latestKbId` 非空；浏览默认当前版本 |
| TC-123 | `test_tc123_detail_shows_summary_when_body_missing` | API | AC-013-5 | `bodyMissing=true`、`body=null`、`summary` 非空 |
| TC-124 | `test_tc124_computes_freshness_states` | API | AC-015-1 / AC-015-3 | 缺失 → `unknown`；早于 30 天 → `stale`；30 天内 → `fresh`；不改写 `freshness_at` |
| TC-125 | `test_tc125_detects_conflict_by_summary_digest` | API | AC-015-2 / ADR-116 | 同 `code_key` 且 `content_digest` 不同 → `hasConflict=true`；来源 `{kbName,version,generatedAt}` ≤20；摘要相同不报冲突 |
| TC-126 | `test_tc126_conflict_query_is_batched` | 服务 | ADR-116 | 对 N 条结果统计 SQL 次数为常数（≤3），不做逐行查询 |
| TC-127 | `test_tc127_renders_injection_template_and_chars` | 纯函数 | AC-014-2 / ADR-109 | 模板逐行精确：`【知识库上下文】` / `知识库：<name> v<version>（生成时间：…）` / `### <code> <title>` + 正文；`total_chars == len(text)` |
| TC-128 | `test_tc128_uses_summary_and_marks_missing_body` | 纯函数 | AC-014-2 / AC-013-5 | 正文缺失时用摘要并追加「（正文缺失）」；`source="summary"`；不注入空串 |
| TC-129 | `test_tc129_preview_reports_segments_and_over_limit` | API | AC-014-1 / AC-014-3 | `promptChars/injectedChars/totalChars/limit` 正确；超限时 200 + `overLimit=true`；不落库 |
| TC-130 | `test_tc130_rejects_over_budget_without_truncation` | 服务 | AC-014-3 / AC-REQ-21 | 超 200,000 → `PromptBudgetExceededError`；错误只带分段字数与上限；条目未被截断或丢弃 |
| TC-131 | `test_tc131_invalid_entries_block_call_without_record` | 服务 + API | AC-014-4 | 失效集非空且未确认 → 409 `knowledge_invalid_entries`；`details.invalidItems` 完整；`ai_call_record` 与事件 0 条；网关未被调用 |
| TC-132 | `test_tc132_confirmation_requires_exact_invalid_set` | 服务 + API | AC-014-4 / ADR-110 | 集合完全相等 → 继续并写快照；少一条/多一条/顺序不同（排序后相等）→ 行为分别为 409 / 409 / 通过 |
| TC-133 | `test_tc133_cancel_does_not_initiate_call` | API | AC-014-4 | 409 后不再请求 → 无 `ai_call_record`、无 `knowledge_injection` 事件；勾选状态由前端保留（组件测试可选） |
| TC-134 | `test_tc134_confirmation_with_empty_valid_set_is_rejected` | 服务 | ADR-110 | 确认后有效集为空 → 409 `knowledge_injection_empty`，不发起调用 |
| TC-135 | `test_tc135_classifies_invalid_reasons` | 服务 | AC-014-4 | 已删除库 → `kb_deleted`；编号不存在 → `entry_not_found`；旧版本条目 → `superseded`；三类可同时出现 |
| TC-136 | `test_tc136_records_injection_snapshot_without_body` | API | AC-014-2 / AC-014-5 | `ai_call_record.knowledge_injection` 与四列正确；`session_event(type=knowledge_injection)` 同事务；快照与事件均不含正文片段 |
| TC-137 | `test_tc137_logs_and_errors_never_contain_body` | 安全 | AC-014-5 / AC-REQ-21 / BR-C18 | 导入、解析失败、注入失败三条路径的日志与响应体均不含哨兵正文；`import_report` 只有原因码 |
| TC-138 | `test_tc138_candidates_only_current_versions_with_badges` | API | AC-014-1 / AC-015-3 | 已删除/被取代不出现；徽标（freshness/conflict/bodyMissing）与详情一致 |
| TC-139 | `test_tc139_delete_removes_all_versions_entries_and_files` | API | AC-016-1 / AC-REQ-23 | 逻辑库全部版本行删除、条目级联 0、目录不存在、列表不再出现 |
| TC-140 | `test_tc140_history_survives_delete_and_is_flagged` | API | AC-016-2 | 历史 `session_event` / `ai_call_record` / 制品不变；读取 `knowledgeInjection.kbDeleted=true`；编号列表保留 |
| TC-141 | `test_tc141_delete_is_scoped_to_one_logical_kb` | API | AC-016-3 | 同项目其他知识库与条目不变；不自动过期 |
| TC-142 | `test_tc142_file_cleanup_failure_still_returns_204` | 服务 | ADR-117 | 模拟 rename/删除失败 → 204，DB 已删，`.trash` 残留且日志只记数量 |
| TC-143 | `test_tc143_project_summary_returns_zero_to_n_bases` | API | AC-012-6 / AC-REQ-24 | 0 个 → 空数组；多个 → 按 `updated_at` 倒序；含状态与 `latestKbId` |
| TC-144 | `test_tc144_migration_0007_on_both_dialects` | 迁移 | RISK-021 / ADR-118 | SQLite + MySQL 各跑 `upgrade head` → `downgrade 0006` → `upgrade head`；索引、CHECK、`ON DELETE CASCADE` 存在 |
| TC-145 | `test_tc145_large_body_roundtrip_not_truncated` | API | RISK-021 | >64KB（<10MB）正文写入后读回字节级一致（验证 `MEDIUMTEXT`） |
| TC-146 | `test_tc146_kb_settings_defaults_and_overrides` | 配置 | ADR-115 / AC-012-2 | 11 个 `AW_KB_*` 默认值正确；环境变量覆盖生效；`AW_PROMPT_MAX_CHARS` 取自 core，不重复定义 |
| TC-147 | `test_tc147_all_endpoints_require_session` | API | ADR-112 | 10 个端点无 Cookie → 401 `unauthorized`，不泄露资源存在性 |
| TC-148 | `test_tc148_error_body_and_time_format` | API | ADR-112 | 错误体 `{code,message,details[],requestId}`；`details` 恒为数组；时间为 RFC 3339 UTC |
| TC-149 | `test_tc149_freshness_and_conflict_warnings_do_not_block` | 服务 | AC-015-4 / AC-REQ-22 | 带 `stale` / `conflict` 条目仍可发起调用；`warnings` 出现在 preview；不触发仓库克隆或代码解析 |
| TC-150 | `test_tc150_injection_block_carries_kb_name_and_generated_at` | 纯函数 | AC-015-3 / AC-REQ-22 | 注入块每库一行包含知识库名与生成时间；缺失时写「未知」，不推断 |

## 3. TC ↔ AC 映射

| AC | 覆盖 TC |
|----|---------|
| AC-012-1 | TC-108, TC-111 |
| AC-012-2 | TC-112, TC-146 |
| AC-012-3 | TC-101, TC-107 |
| AC-012-4 | TC-102, TC-106 |
| AC-012-5 | TC-103, TC-104 |
| AC-012-6 | TC-111, TC-143 |
| AC-012-7 | TC-113 |
| AC-013-1 | TC-118, TC-120 |
| AC-013-2 | TC-121 |
| AC-013-3 | TC-119, TC-120 |
| AC-013-4 | TC-114, TC-122 |
| AC-013-5 | TC-109, TC-110, TC-123, TC-128 |
| AC-014-1 | TC-129, TC-138 |
| AC-014-2 | TC-127, TC-128, TC-136 |
| AC-014-3 | TC-129, TC-130 |
| AC-014-4 | TC-131, TC-132, TC-133, TC-134, TC-135 |
| AC-014-5 | TC-136, TC-137 |
| AC-015-1 | TC-124 |
| AC-015-2 | TC-125, TC-126 |
| AC-015-3 | TC-124, TC-138, TC-150 |
| AC-015-4 | TC-149 |
| AC-016-1 | TC-139 |
| AC-016-2 | TC-140 |
| AC-016-3 | TC-141, TC-142 |
| AC-REQ-18 | TC-105, TC-112 |
| AC-REQ-19 | TC-101, TC-103, TC-104, TC-105 |
| AC-REQ-20 | TC-118, TC-119, TC-121, TC-123 |
| AC-REQ-21 | TC-127, TC-130, TC-136, TC-137 |
| AC-REQ-22 | TC-124, TC-125, TC-149, TC-150 |
| AC-REQ-23 | TC-139, TC-140 |
| AC-REQ-24 | TC-114, TC-143 |

## 4. 门禁与执行

- `python3 .aw/aw.py verify` 跑 `.aw/config.json` 的测试命令；测试报告需逐条出现 TC 编号。
- 默认套件（SQLite）必须全绿；CI 额外启动 MySQL 8.4 容器跑同一套用例（至少 `test_kb_migrations.py` 与全部 API 用例）。
- 前端 Vitest 与 Playwright 为 P1 可选，不进入本阶段门禁；`KbCharBudget` 与 `KbInvalidEntryDialog` 的关键行为由服务端 TC-129 / TC-131 / TC-132 兜底。
- 失败处理：先修实现；确认用例本身写错才改用例，并在提交说明里写明原因。
