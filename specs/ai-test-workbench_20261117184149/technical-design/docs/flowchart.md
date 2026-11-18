# Flowchart — workbench-core

> 阶段：tech-design。图与 `docs/database-schema.md` / `docs/api-spec.md` / `change-spec.md` 一致。

## 1. 分层架构

```mermaid
graph TB
  subgraph Browser["浏览器（SPA）"]
    UI["React 19 + Radix + Design Tokens"]
    Q["TanStack Query"]
    UI --> Q
  end

  subgraph API["FastAPI /api/v1"]
    AUTHMW["require_session + Origin 校验"]
    ROUTES["auth / entrances / projects / providers / models / sessions / artifacts / calls"]
    ERR["统一错误体 {code,message,details,requestId}"]
    AUTHMW --> ROUTES
    ROUTES --> ERR
  end

  subgraph Services["应用服务层（进程内契约冻结）"]
    SA["services.auth"]
    SP["services.projects / providers / models"]
    SS["services.sessions<br/>create / append_event"]
    SAR["services.artifacts<br/>save"]
    AG["services.ai_gateway<br/>AiGateway.complete（唯一模型出口）"]
    SC["services.calls（查询）"]
  end

  subgraph Adapters["适配层"]
    AIO["adapters.ai.openai_compatible"]
    AIA["adapters.ai.anthropic"]
    FS["adapters.fs.storage<br/>临时文件 / 原子移动 / trash / 包含校验"]
    CR["core.crypto AES-256-GCM"]
    PW["core.password Argon2id"]
    RD["core.redaction 日志脱敏"]
  end

  subgraph Data["持久化与文件"]
    DB[("MySQL 8.4 生产<br/>SQLite 开发/测试")]
    DISK[("AW_DATA_DIR<br/>sessions/ · .trash/ · 开发库")]
  end

  subgraph External["外部"]
    OAI["OpenAI 兼容 API"]
    ANT["Anthropic API"]
  end

  UI --> AUTHMW
  Q --> ROUTES
  ROUTES --> SA
  ROUTES --> SP
  ROUTES --> SS
  ROUTES --> SAR
  ROUTES --> AG
  ROUTES --> SC
  SA --> PW
  SP --> CR
  SS --> DB
  SAR --> FS
  SAR --> DB
  AG --> CR
  AG --> AIO
  AG --> AIA
  AG --> DB
  SC --> DB
  AIO --> OAI
  AIA --> ANT
  FS --> DISK
  ROUTES -. 日志 .-> RD
```

## 2. 登录与来源锁定

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser
  participant A as API /auth
  participant DB as DB
  B->>A: POST /auth/login {password} + Origin
  A->>A: Origin 校验（失败 403 forbidden_origin）
  A->>DB: SELECT login_attempt (source_ip_hash) FOR UPDATE
  alt locked_until > now
    A-->>B: 429 login_locked + Retry-After（不校验口令）
  else 未锁定
    A->>DB: 取 admin_credential
    A->>A: Argon2id verify(password)
    alt 校验失败
      A->>DB: failed_count+1；达 5 → locked_until=now+5min
      A-->>B: 401 login_failed（不区分原因）
    else 校验成功
      A->>DB: DELETE login_attempt（清零）
      A->>A: token=token_urlsafe(32)
      A->>DB: INSERT login_session(token_hash, SHA-256)
      A-->>B: 200 {authenticated} + Set-Cookie aw_session
    end
  end
  Note over B,A: 后续请求：查 token_hash → 校验 revoked_at/8h 空闲 → UPDATE last_seen_at
```

## 3. AI 调用（成功 / 重试 / 超时 / 中断）

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser
  participant API as API /sessions/{id}/calls
  participant G as AiGateway
  participant AG as Provider Adapter
  participant P as 上游提供商
  participant DB as DB

  B->>API: POST calls {prompt, temperature?, maxTokens?}
  API->>G: complete(session_id, model_id, prepared, ...)
  G->>DB: 只读校验：会话进行中 / 模型与提供商启用
  alt 前置失败
    G-->>API: 错误（无 AiCallRecord）
    API-->>B: 404/409/400
  else 凭据解密失败
    G-->>API: provider_credential_unavailable（无 AiCallRecord）
    API-->>B: 502
  else 前置通过
    G->>G: acquire semaphore(4)
    G->>DB: INSERT ai_call_record(status=running)
    loop 最多 2 次尝试（仅网络错误 / 5xx 重试）
      G->>AG: request(prepared, params, timeout=120s)
      AG->>P: HTTPS
      alt 成功
        P-->>AG: 200 result
        AG-->>G: AIResult
      else 4xx 鉴权/限流/参数
        P-->>AG: 4xx
        AG-->>G: AIError（不重试）
      else 网络错误 / 5xx
        AG-->>G: AIError（可重试）
        G->>G: retry_count += 1（仅第一次）
      else 120s 无响应
        G-->>G: timeout（不重试）
      end
    end
    G->>DB: UPDATE call_record → success/ failed/ timeout（latency_ms, retry_count, error_code, result_text）
    G->>DB: INSERT session_event(type=call) + UPDATE session.updated_at（同一事务）
    alt 成功
      G-->>API: AIResult(call_id, text)
      API-->>B: 200
    else 失败/超时
      G-->>API: AIError(code, call_id, retry_count)
      API-->>B: 502/504（details 含 callId）
    end
  end
  Note over G,DB: 请求取消或进程异常：finally 终结 failed(interrupted)；硬崩溃由启动归并兜底
```

## 4. 启动自检与 running 回收

```mermaid
sequenceDiagram
  autonumber
  participant M as main/startup
  participant ENV as 环境变量
  participant DB as DB
  participant FS as AW_DATA_DIR
  M->>ENV: 校验 AW_ENCRYPTION_KEY / AW_ADMIN_PASSWORD
  alt 缺失或非法
    M-->>M: 非 0 退出（明确提示）
  end
  M->>DB: 连接（compose 场景退避最多 30s）
  M->>DB: 校验 alembic_version == head（否则提示 upgrade head 退出）
  M->>DB: 转存/轮换 admin_credential（Argon2id）
  M->>DB: SELECT status='running' 的调用记录
  loop 每条 running
    M->>DB: UPDATE → failed(interrupted), finished_at, latency_ms
    M->>DB: INSERT session_event(type=call, status=failed, errorCode=interrupted)
    M->>DB: UPDATE session.updated_at
  end
  M->>DB: 清理过期 login_session / login_attempt
  M->>FS: 扫描孤儿文件与过期 .trash
  M->>M: 启动 Uvicorn
```

## 5. 文件上传（校验、落盘、半成品清理）

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser
  participant API as API /sessions/{id}/artifacts
  participant S as artifacts.save
  participant T as .tmp
  participant D as sessions/<id>/
  participant DB as DB

  B->>API: multipart files[1..10]
  API->>S: save(session_id, file_name, source)
  S->>DB: 只读校验会话存在且进行中
  alt 会话终态 / 不存在
    S-->>B: 409 / 404（不落盘）
  end
  loop 每个文件
    S->>S: 扩展名白名单 + 流式读取 ≤10MB
    alt 不合规
      S->>T: 删除本批已写临时文件
      S-->>B: 400 details 列出每个不合格文件（整批不落盘）
    else 合规
      S->>T: 写入 .tmp/<uuid>
    end
  end
  S->>DB: 事务开始：INSERT artifact 行（同名自动改名）
  S->>D: os.replace 临时文件 → sessions/<id>/<uuid4>.<ext>
  alt 磁盘写失败
    S->>DB: ROLLBACK
    S->>D: 删除已移动文件
    S->>T: 清理临时文件
    S-->>B: 507 artifact_write_failed
  else 移动成功
    S->>DB: INSERT session_event(type=artifact) + UPDATE session.updated_at
    S->>DB: COMMIT
    S-->>B: 201 items + events
  end
  Note over S,D: 崩溃残留由启动孤儿扫描移入 .trash 并清理
```

## 6. 删除会话（DB + 文件一致性）

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser
  participant API as API DELETE /sessions/{id}
  participant S as sessions.delete_session
  participant FS as AW_DATA_DIR
  participant DB as DB

  B->>API: DELETE /sessions/42（ConfirmDialog 已确认）
  API->>S: delete_session(42)
  S->>FS: rename sessions/42 → .trash/42-<uuid>
  alt 重命名失败
    S-->>B: 500 session_delete_failed（DB 不动）
  else 重命名成功或目录不存在
    S->>DB: BEGIN; DELETE analysis_session WHERE id=42
    Note over DB: CASCADE：session_event / artifact / ai_call_record
    alt 提交成功
      S->>FS: 删除 .trash/42-<uuid>（失败仅记日志）
      S-->>B: 204
    else 提交失败
      S->>FS: 尽力 rename 回 sessions/42
      S-->>B: 500 internal_error（trash 由清理任务兜底）
    end
  end
```

## 7. 会话状态流转

```mermaid
stateDiagram-v2
  [*] --> in_progress: POST /sessions（项目 + 启用模型 + 入口）
  in_progress --> completed: 用户二次确认（POST /complete，actor=local-user）
  in_progress --> failed: 系统未捕获失败（actor=system）
  completed --> [*]
  failed --> [*]
  note right of completed
    终态：拒绝新增事件 / 制品 / 调用（409 session_closed）
    不提供重新打开
  end note
```

## 8. ER 图

```mermaid
erDiagram
  ADMIN_CREDENTIAL {
    smallint credential_id PK
    varchar algorithm
    varchar password_hash
    datetime updated_at
  }
  LOGIN_SESSION {
    bigint login_session_id PK
    char token_hash UK
    datetime created_at
    datetime last_seen_at
    datetime revoked_at
    char source_ip_hash
  }
  LOGIN_ATTEMPT {
    char source_ip_hash PK
    int failed_count
    datetime first_failed_at
    datetime last_failed_at
    datetime locked_until
  }
  PROJECT_CONTEXT {
    bigint project_id PK
    varchar name
    varchar name_key UK
    varchar repo_url
    varchar tech_stack
    text requirement_source
    text notes
    datetime created_at
    datetime updated_at
  }
  PROVIDER_CONFIG {
    bigint provider_id PK
    varchar name
    varchar protocol
    varchar base_url
    varchar api_key_ciphertext
    boolean enabled
    datetime created_at
    datetime updated_at
  }
  MODEL_BINDING {
    bigint model_id PK
    bigint provider_id FK
    varchar model_name
    varchar model_name_key
    varchar display_name
    numeric default_temperature
    int default_max_tokens
    boolean enabled
    datetime created_at
  }
  ANALYSIS_SESSION {
    bigint session_id PK
    bigint project_id FK
    varchar entrance_key
    varchar title
    varchar status
    bigint model_id FK
    datetime created_at
    datetime updated_at
    datetime closed_at
  }
  SESSION_EVENT {
    bigint event_id PK
    bigint session_id FK
    varchar type
    json payload
    datetime created_at
  }
  ARTIFACT {
    bigint artifact_id PK
    bigint session_id FK
    varchar kind
    varchar file_name
    varchar file_name_key
    varchar storage_name
    varchar relative_path
    varchar mime_type
    bigint byte_size
    datetime created_at
  }
  AI_CALL_RECORD {
    bigint call_id PK
    bigint session_id FK
    bigint model_id FK
    bigint provider_id FK
    varchar status
    char prompt_digest
    varchar prompt_preview
    int prompt_char_count
    text result_text
    int latency_ms
    int retry_count
    varchar error_code
    varchar error_message
    datetime created_at
    datetime finished_at
  }

  PROVIDER_CONFIG ||--o{ MODEL_BINDING : "提供"
  PROJECT_CONTEXT ||--o{ ANALYSIS_SESSION : "拥有"
  MODEL_BINDING ||--o{ ANALYSIS_SESSION : "被选定"
  ANALYSIS_SESSION ||--o{ SESSION_EVENT : "级联删除"
  ANALYSIS_SESSION ||--o{ ARTIFACT : "级联删除"
  ANALYSIS_SESSION ||--o{ AI_CALL_RECORD : "级联删除"
  MODEL_BINDING ||--o{ AI_CALL_RECORD : "调用快照"
  PROVIDER_CONFIG ||--o{ AI_CALL_RECORD : "调用快照"
```

> `ADMIN_CREDENTIAL`、`LOGIN_SESSION`、`LOGIN_ATTEMPT` 不与业务表建外键；登录会话独立于分析会话。
