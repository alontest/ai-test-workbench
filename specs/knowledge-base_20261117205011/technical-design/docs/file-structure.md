# File Structure — knowledge-base

> 阶段：tech-design（补充产出：目录结构与文件职责）。依据 `technical-design/change-spec.md` §1、`docs/component-tree.md`、`docs/api-spec.md`、`docs/database-schema.md`。
> 仓库基线：core spec 已建立 `src/workbench/` 与 `web/` 骨架；本 spec 只追加知识库模块文件，并改动 8 个接入点（见 §4）。测试目录沿用 `tests/`（pytest `pythonpath=["src"]`）。

## 1. 后端目录

```text
migrations/
  versions/
    0006_knowledge_injection.py      # core 交付（前置，本 spec 不改）
    0007_knowledge_base.py           # 本 spec：2 张表，down_revision="0006"

src/workbench/
  knowledge/                         # 纯解析层：无 DB、无 IO、可直接单测
    __init__.py
    config.py                        # KbSettings（AW_KB_*）、get_kb_settings()
    types.py                         # EntryType、PREFIX_TO_TYPE、ParsedEntry/ParsedIndex/ImportReport
    index_parser.py                  # parse_index()
    body_matcher.py                  # match_bodies()
    naming.py                        # derive_name()、name_key()
    rendering.py                     # render_injection()、注入模板常量
    errors.py                        # KbDomainError 族（只带码/计数/编号，不带正文）
  db/
    models/
      knowledge_base.py              # KnowledgeBase ORM
      knowledge_entry.py             # KnowledgeEntry ORM
    repositories/
      knowledge.py                   # KnowledgeRepository（版本行锁、检索、分页、冲突、删除）
  adapters/fs/
    knowledge_storage.py             # KbStorage：staging / 服务端命名 / 原子 rename / trash / 孤儿扫描
  services/knowledge/
    __init__.py
    import_service.py                # KnowledgeImportService.import_files()
    query_service.py                 # KnowledgeQueryService（列表/详情/版本/检索/候选）
    injection_service.py             # KnowledgeInjectionService.preview/prepare_for_call
    lifecycle_service.py             # KnowledgeLifecycleService.delete_logical()
    registration.py                  # install_injection_preparer(app)
  api/
    schemas/
      knowledge.py                   # 请求/响应 Pydantic 模型（camelCase、ID 字符串）
    v1/
      knowledge_bases.py             # 端点 1~5
      knowledge_entries.py           # 端点 6~8
      knowledge_injection.py         # 端点 9~10

tests/
  test_kb_config.py                  # TC-146
  test_kb_index_parser.py            # TC-101 ~ TC-107
  test_kb_body_matcher.py            # TC-109 / TC-110
  test_kb_naming.py                  # TC-108
  test_kb_rendering.py               # TC-127 / TC-128 / TC-150
  test_kb_import_service.py          # TC-111 / TC-113 / TC-114 / TC-115 / TC-116 / TC-117
  test_kb_import_api.py              # TC-112 / TC-114 / TC-145
  test_kb_query_api.py               # TC-118 ~ TC-126 / TC-143
  test_kb_injection_service.py       # TC-129 ~ TC-135 / TC-149
  test_kb_injection_api.py           # TC-136 ~ TC-138 / TC-147
  test_kb_lifecycle_api.py           # TC-139 ~ TC-142
  test_kb_migrations.py              # TC-144
  test_kb_security_logs.py           # TC-137 / TC-148
```

### 文件职责要点

| 文件 | 职责 | 不做什么 |
|------|------|---------|
| `knowledge/index_parser.py` | 最小结构、前缀映射、条目校验、护栏、报告 | 不读磁盘、不写 DB、不记录原文 |
| `knowledge/body_matcher.py` | `.md` 文件名优先 + `###` 切块 + 去重 | 不解析 Markdown 渲染、不做 HTML 清洗（输出按纯文本） |
| `knowledge/rendering.py` | 固定模板、Unicode 码点计数 | 不查 DB；入参是已解析的条目 |
| `services/knowledge/injection_service.py` | 失效重校验、阻塞确认比对、组装、预算 | 不直接调网关、不写 `ai_call_record`（归 core） |
| `adapters/fs/knowledge_storage.py` | 流式写 staging、`sha256[:16]__slug`、`resolve()` 包含校验、rename、trash | 不拼接客户端文件名、不跨 `knowledge-bases/` 根 |
| `services/knowledge/import_service.py` | 限额 → 暂存 → 解析 → 取号 → rename → 单事务落库 | 不在事务内做长 IO；失败必须清理 staging 与目录 |
| `services/knowledge/query_service.py` | 只读查询、徽标、冲突批量查询、游标 | 不做写操作；不逐行 N+1 |
| `services/knowledge/lifecycle_service.py` | 单事务删全部版本；提交后移文件 | 不改历史事件/调用记录 |
| `api/v1/knowledge_*.py` | 参数校验、错误映射、依赖 `require_session` | 不承载业务规则（规则在服务层） |

## 2. 前端目录（`web/src/features/knowledge/`）

```text
web/src/features/knowledge/
  index.ts                      # 导出 4 页面 + 3 嵌入组件 + routes
  routes.tsx                    # 4 条路由（在 AuthGate 内）
  api/
    types.ts                    # 与 api-spec 对齐的 TS 类型
    client.ts                   # 端点封装 + toKnowledgeRefs()
    keys.ts                     # TanStack Query key 工厂
  hooks/
    useKnowledgeBases.ts
    useKnowledgeEntries.ts
    useEntryDetail.ts
    useImportKnowledge.ts
    useDeleteKnowledge.ts
    useInjectionCandidates.ts
    useInjectionPreview.ts
  pages/
    KnowledgeBaseListPage.tsx
    KnowledgeImportPage.tsx
    KnowledgeBrowsePage.tsx
    KnowledgeEntryPage.tsx
  components/
    KnowledgeBaseTable.tsx
    KbProjectFilter.tsx
    KbImportPanel.tsx
    KbFileValidationList.tsx
    KbImportReport.tsx
    KbBrowseLayout.tsx
    KbTypeTabs.tsx
    KbSearchBox.tsx
    KbEntryList.tsx
    KbEntryDetail.tsx
    KbFreshnessBadge.tsx
    KbConflictNotice.tsx
    KbVersionSelector.tsx
    KbDeletedBadge.tsx
    KbDeleteDialog.tsx
    KbInjectPicker.tsx
    KbCharBudget.tsx
    KbInvalidEntryDialog.tsx
    ProjectKnowledgeSummary.tsx
```

样式：每个组件配同名 `*.module.css`（CSS Modules，复用 core token 变量），仅在需要布局时新增，不定义新变量。

## 3. 数据与文件落盘布局

```text
$AW_DATA_DIR/
  sessions/<sessionId>/...            # core 制品（不改）
  knowledge-bases/
    <kbId>/
      index.json                      # 原文，原样保存
      docs/<sha256前16>__<slug>.md    # 原文，服务端命名
      manifest.json                   # 文件清单 + sha256 + 版本元数据
    .staging/<importToken>/...        # 导入暂存（同文件系统，可原子 rename）
  .trash/<kbId>-<ts>/                 # 删除中转，尽力清理
```

## 4. 对既有文件的改动点

| 文件 | 改动 |
|------|------|
| `src/workbench/api/v1/router.py` | 注册 3 个知识库 router（统一挂 `require_session` 依赖） |
| `src/workbench/main.py` | `create_app()` 调 `install_injection_preparer(app)`；生命周期追加孤儿目录扫描 |
| `web/src/router.tsx` | 追加 `/knowledge-bases/*` 4 条路由 |
| `web/src/app/AppShell.tsx` | 「基座管理」分组追加「知识库」入口 |
| `web/src/features/projects/ProjectContextPage.tsx` | 在 `data-mount="knowledge-summary"` 处渲染 `ProjectKnowledgeSummary` |
| `web/src/features/calls/CallPanel.tsx` | 嵌入选择器、字符预算与失效确认对话框；`/ai/complete` 附带 `knowledgeRefs` / `confirmInvalidCodes` |
| `scripts/backup.sh` | 备份范围追加 `knowledge-bases/` |
| `pyproject.toml` / `uv.lock` / `package.json` | **不改**（不新增依赖；`python-multipart` 已由 core 引入） |

## 5. 创建顺序（供 tech-tasks 拆分）

1. `knowledge/config.py`、`knowledge/types.py`、`knowledge/errors.py`（无依赖）
2. `knowledge/index_parser.py`、`body_matcher.py`、`naming.py`、`rendering.py`（依赖 1，可并行）
3. `db/models/knowledge_base.py`、`knowledge_entry.py`、`migrations/versions/0007_knowledge_base.py`（依赖 1）
4. `db/repositories/knowledge.py`、`adapters/fs/knowledge_storage.py`（依赖 3）
5. `services/knowledge/*`（依赖 2 + 4）
6. `api/schemas/knowledge.py`、`api/v1/knowledge_*.py`、`router.py` 接线（依赖 5）
7. `main.py` 注册 + 启动扫描；`CallPanel` / 项目页挂载
8. 前端 `api/` → `hooks/` → `components/` → `pages/` → `routes.tsx` / `AppShell`
9. 测试按 TC 分批补齐（见 `docs/test-strategy.md`）
