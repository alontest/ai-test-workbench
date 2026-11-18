# Flowchart — knowledge-base

> 阶段：tech-design（附加产出）。含系统分层架构图、核心流程时序图与数据库 ER 图；ER 与 `docs/database-schema.md` 一致。

## 1. 系统分层架构

```mermaid
graph TB
  subgraph Browser["浏览器（core AppShell 内）"]
    Pages["知识库页面<br/>列表 / 导入 / 浏览 / 详情"]
    Embed["嵌入组件<br/>KbInjectPicker / KbCharBudget / KbInvalidEntryDialog"]
    Summary["ProjectKnowledgeSummary<br/>data-mount=knowledge-summary"]
  end

  subgraph API["FastAPI /api/v1（core 同源）"]
    KBAPI["knowledge_bases / knowledge_entries<br/>knowledge_injection 端点（本 spec）"]
    CoreAPI["core: sessions / ai/complete<br/>calls / projects"]
  end

  subgraph Service["服务层"]
    ImportSvc["KnowledgeImportService"]
    QuerySvc["KnowledgeQueryService"]
    InjSvc["KnowledgeInjectionService<br/>preview / prepare_for_call"]
    LifeSvc["KnowledgeLifecycleService"]
    CoreSvc["core: AiGateway / sessions / projects"]
  end

  subgraph Pure["纯解析层（无 IO）"]
    Parser["index_parser"]
    Body["body_matcher"]
    Name["naming"]
    Render["rendering"]
  end

  subgraph Storage["存储"]
    Repo["KnowledgeRepository"]
    FS["KbStorage"]
    DB[("MySQL 8.4 / SQLite<br/>knowledge_base<br/>knowledge_entry")]
    Disk[("$AW_DATA_DIR/knowledge-bases/")]
  end

  Pages --> KBAPI
  Embed --> KBAPI
  Embed --> CoreAPI
  Summary --> KBAPI
  CoreAPI -->|"prepare_for_call + InjectionSnapshot"| InjSvc
  KBAPI --> ImportSvc
  KBAPI --> QuerySvc
  KBAPI --> InjSvc
  KBAPI --> LifeSvc
  ImportSvc --> Parser
  ImportSvc --> Body
  ImportSvc --> Name
  InjSvc --> Render
  ImportSvc --> Repo
  ImportSvc --> FS
  QuerySvc --> Repo
  InjSvc --> Repo
  LifeSvc --> Repo
  LifeSvc --> FS
  Repo --> DB
  FS --> Disk
  CoreSvc -.->|"注入后写入留痕（core 的 0006 列）"| DB
```

**依赖方向**：`api` → `services` → `knowledge`（纯函数）+ `db/repositories` + `adapters/fs`。纯解析层不依赖 FastAPI、SQLAlchemy 与文件系统；`services` 不直接访问 `AiGateway`（调用由 core 执行，本 spec 只返回 `PreparedInjection`）。

## 2. 导入流程（US-012）

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant API as POST /knowledge-bases
  participant S as KnowledgeImportService
  participant ST as KbStorage
  participant P as index_parser / body_matcher
  participant DB as Repository + DB

  U->>API: multipart(projectId, name?, files[])
  API->>S: import_files(...)
  S->>S: 类型/单文件/文件数/合计 校验（逐项收集原因）
  alt 任一不合规
    S-->>API: 400 unsupported_file_type / file_too_large / too_many_files / kb_import_too_large
    API-->>U: 逐项说明，不落盘、不建库
  else 合规
    S->>ST: 流式写 .staging/<token>/（边写边校验字节）
    S->>P: parse_index(index.json 原文)
    alt 缺最小结构 / JSON 非法 / 全部条目被跳过
      P-->>S: IndexJsonError
      S->>ST: 删除 staging
      S-->>API: 400 index_json_invalid / index_json_missing
    else 有可导入条目
      S->>P: match_bodies(codes, md 文件)
      S->>DB: 行锁取版本号（同名 current 行 FOR UPDATE）
      S->>ST: rename .staging/<token> → knowledge-bases/<kbId>
      S->>DB: 单事务写 knowledge_base + 分块 executemany 条目
      alt 写库失败
        DB-->>S: 异常
        S->>ST: 删除 knowledge-bases/<kbId>
        S-->>API: 507 kb_write_failed / 409 kb_name_conflict（重试 1 次后）
      else 提交成功
        S-->>API: 201 {kb, importReport}
        API-->>U: 列表出现，状态「已就绪」
      end
    end
  end
```

失败语义：任一步失败 → 事务回滚 + 删除目录，不留文件、知识库行与条目索引（AC-012-7）。进程崩溃留下的「有目录无 DB 行」由启动扫描清理（目录 mtime 早于 1 小时才删，只记数量）。

## 3. 注入与调用流程（US-014，AC-014-4 改写版）

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant UI as CallPanel + KbInjectPicker
  participant KB as knowledge-injection/preview
  participant Core as core POST /ai/complete
  participant S as KnowledgeInjectionService
  participant GW as AiGateway
  participant DB as ai_call_record / session_event

  U->>UI: 勾选条目 / 输入提示
  UI->>KB: {refs:[{kbId,code}], userPrompt}
  KB->>S: preview(project_id, refs, prompt)
  S-->>KB: items / invalidItems / 分段字符数 / overLimit / warnings
  KB-->>UI: 实时「已选 N 条 · 注入 X · 提示 Y · 合计 Z / 200000」
  alt overLimit
    UI-->>U: 显示分段与超出量，禁用「发起调用」，不截断
  else 未超限
    U->>Core: {prompt, knowledgeRefs:[{kbId,entryCodes[]}]}
    Core->>S: prepare_for_call(session, project, prompt, refs, confirm=())
    S->>S: 重校验失效集（已删除 / 不存在 / 已被取代）并按 (kbId,code) 排序
    alt 失效集非空且未精确确认
      S-->>Core: KnowledgeInvalidEntriesError(details.invalidItems)
      Core-->>UI: 409 knowledge_invalid_entries（不调网关、不写 AiCallRecord）
      UI-->>U: 阻塞式对话框列出被剔除编号（取消则不发起）
      U->>UI: 确认
      UI->>Core: 重试 + confirmInvalidCodes（原样回传失效集）
      Core->>S: prepare_for_call(..., confirm_invalid_codes=失效集)
      S->>S: 集合完全相等才继续；否则再次抛错（确认过期）
    end
    alt 有效集为空
      S-->>Core: KnowledgeInjectionEmptyError
      Core-->>UI: 409 knowledge_injection_empty（不发起）
    else 有效集非空
      S->>S: render_injection → text / 字符数 / snapshot
      alt totalChars > 200000
        S-->>Core: PromptBudgetExceededError
        Core-->>UI: 400 prompt_budget_exceeded（分段字数 + 上限）
      else 预算通过
        S-->>Core: PreparedInjection(text, snapshot, excludedCodes)
        Core->>GW: complete(..., prepared=text, injection=snapshot)
        GW->>DB: 同事务写 4 列 + knowledge_injection 事件（只记标识/编号/字符数）
        GW-->>Core: AIResult
        Core-->>UI: 200 调用结果
      end
    end
  end
```

不变量：

- 失效、空注入与超预算三类错误都发生在**调用外部请求之前**，均不写 `AiCallRecord`、不写事件。
- 预览与发起调用使用**同一组装实现**（`preview` 与 `prepare_for_call` 共用渲染与计数），最终以服务端重算为准。
- 字符口径为 Unicode 码点；`total_chars == len(text)`，注入块尾部含分隔符，避免拼接口径漂移。

## 4. 删除流程（US-016）

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant API as DELETE /knowledge-bases/{kbId}
  participant S as KnowledgeLifecycleService
  participant DB as Repository + DB
  participant FS as KbStorage
  participant H as 历史记录（只读）

  U->>U: 二次确认（列明级联范围，无撤销）
  U->>API: DELETE
  API->>S: delete_logical(project_id, kb_id)
  S->>DB: 解析 kb_id → (project_id, name_key)，查全部版本
  alt 不存在
    S-->>API: 404 kb_not_found
  else 存在
    S->>DB: 单事务删除 knowledge_base 全部版本（条目 ON DELETE CASCADE）
    DB-->>S: 提交成功
    S->>FS: 各版本目录 rename → .trash/<kbId>-<ts>/ 并尽力删除
    Note over S,FS: 文件清理失败只记日志，仍返回 204（ADR-117）
    S-->>API: 204
    API-->>U: 列表不再出现
    H->>DB: 读取时按 kbId 左连接判定 kbDeleted（行不存在或表不存在）
    H-->>U: 历史编号保留并标「知识库已删除」，事件/制品/调用记录未修改
  end
```

## 5. 版本与状态

```mermaid
stateDiagram-v2
  [*] --> ready: 导入成功（version = max+1）
  ready --> superseded: 同名逻辑库再次导入（current_flag → NULL, superseded_by_kb_id → 新行）
  superseded --> [*]: 删除逻辑库（连同全部版本）
  ready --> [*]: 删除逻辑库（连同全部版本）
```

导入失败不产生任何行（无 `failed` 状态）。

## 6. 数据库 ER

```mermaid
erDiagram
  PROJECT_CONTEXT ||--o{ KNOWLEDGE_BASE : "拥有 0..n"
  KNOWLEDGE_BASE ||--o{ KNOWLEDGE_ENTRY : "ON DELETE CASCADE"
  KNOWLEDGE_BASE |o--o| KNOWLEDGE_BASE : "superseded_by_kb_id（无 FK）"

  KNOWLEDGE_BASE {
    char32 kb_id PK
    bigint project_id FK
    varchar200 name
    varchar200 name_key
    int version
    char1 current_flag
    varchar20 status
    datetime index_generated_at
    int entry_count
    int file_count
    bigint total_byte_size
    char64 source_index_sha256
    varchar191 storage_dir
    char32 superseded_by_kb_id
    json import_report
    datetime created_at
    datetime updated_at
  }

  KNOWLEDGE_ENTRY {
    char32 entry_id PK
    char32 kb_id FK
    varchar128 code
    varchar128 code_key
    varchar20 type
    varchar500 title
    mediumtext summary
    mediumtext body
    boolean body_missing
    varchar255 body_source_file
    json fields
    json tables
    json code_paths
    json neighbors
    json extras
    varchar100 source_doc
    varchar200 anchor
    datetime freshness_at
    char64 content_digest
    datetime created_at
  }
```

> 唯一键：`uq_knowledge_base_project_name_current(project_id, name_key, current_flag)`、`uq_knowledge_base_project_name_version(project_id, name_key, version)`、`uq_knowledge_entry_kb_code(kb_id, code_key)`；`ai_call_record` / `session_event` 与知识库之间**无外键**。

## 7. 检索与排序

```mermaid
flowchart LR
  Q["q（1..100，转义 % _ \\）"] --> Exact["code_key 精确命中（rank 0）"]
  Q --> Prefix["code_key 前缀命中（rank 1）"]
  Q --> Title["title LIKE（rank 2）"]
  Q --> Summary["summary LIKE（rank 3）"]
  Q --> Body["body LIKE（rank 4）"]
  Exact --> Merge["合并 + 去重（同一条目取最小 rank）"]
  Prefix --> Merge
  Title --> Merge
  Summary --> Merge
  Body --> Merge
  Merge --> Page["order by rank, code_key, entry_id<br/>limit 50（≤200）+ cursor"]
  Page --> Counts["countsByType（忽略 type，共用 project/kbId/q）"]
```
