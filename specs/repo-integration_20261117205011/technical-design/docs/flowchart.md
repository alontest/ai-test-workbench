# Flowchart — repo-integration

> 阶段：tech-design（附加产出）。含系统分层架构图、核心流程时序图、状态机与数据库 ER；ER 与 `docs/database-schema.md` 一致。

## 1. 系统分层架构

```mermaid
graph TB
  subgraph Browser["浏览器（core AppShell 内）"]
    Panel["RepoBindingPanel<br/>data-mount=repo-binding-panel"]
    Browse["RepoBrowsePage<br/>/projects/:projectId/repos/:bindingId"]
    Drawer["FileViewerDrawer（480px）"]
  end

  subgraph API["FastAPI /api/v1（core 同源）"]
    BindAPI["repo_bindings（端点 1~9）"]
    BrowseAPI["repo_browse（端点 10~15）"]
    CoreAPI["core：require_session / 错误体 / 分页"]
  end

  subgraph Service["服务层"]
    BindSvc["RepoBindingService"]
    TestSvc["RepoConnectivityService"]
    SyncSvc["RepoSyncService"]
    BrowseSvc["RepoBrowseService"]
    FileSvc["RepoFileService"]
  end

  subgraph Provider["供应商适配层"]
    Factory["build_provider()"]
    GH["GitHubProvider"]
    YX["YunxiaoProvider"]
    Base["BaseProvider<br/>httpx.AsyncClient<br/>follow_redirects=False<br/>max_retries=0"]
  end

  subgraph Pure["安全与纯逻辑"]
    Val["validation"]
    Crypto["crypto（AW_REPO_TOKEN_KEY）"]
    Cursor["cursor（HMAC）"]
    SSRF["ssrf"]
    Redact["redaction"]
  end

  subgraph Storage["存储"]
    Repo["RepoRepository"]
    DB[("MySQL 8.4 / SQLite<br/>repo_binding / repo_sync_record<br/>repo_metadata_snapshot / repo_file_read_record")]
  end

  HTTP["GitHub REST / 云效 Codeup"]

  Panel --> BindAPI
  Browse --> BrowseAPI
  Drawer --> BrowseAPI
  BindAPI --> BindSvc
  BindAPI --> TestSvc
  BindAPI --> SyncSvc
  BrowseAPI --> BrowseSvc
  BrowseAPI --> FileSvc
  BindSvc --> Crypto
  BindSvc --> Val
  TestSvc --> Factory
  SyncSvc --> Factory
  BrowseSvc --> Factory
  FileSvc --> Factory
  BrowseSvc --> Cursor
  BrowseSvc --> Val
  FileSvc --> Val
  Factory --> GH
  Factory --> YX
  GH --> Base
  YX --> Base
  Base --> SSRF
  Base --> Redact
  Base --> HTTP
  BindSvc --> Repo
  TestSvc --> Repo
  SyncSvc --> Repo
  BrowseSvc --> Repo
  FileSvc --> Repo
  Repo --> DB
```

**依赖方向**：`api` → `services` → `repos`（纯逻辑 + 适配器）+ `db/repositories`。适配器不写 DB；服务层不拼 URL；前端只消费归一化 DTO。

## 2. 绑定与测试连接（US-017 / US-018）

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant UI as RepoBindingForm
  participant API as /repo-bindings
  participant S as RepoBindingService / ConnectivityService
  participant Cry as crypto
  participant V as validation + ssrf
  participant P as Provider
  participant DB as RepoRepository

  alt 保存前测试（AMB-028）
    U->>UI: 填提供商 / 仓库标识 / 域名 / 令牌
    UI->>API: POST /repo-bindings/test-connection
    API->>V: 校验标识、域名、令牌非空
    alt 非法
      V-->>API: 400 invalid_*（逐字段）
      API-->>UI: 字段级错误，不落库
    else 合法
      API->>P: get_repository(repo)，10s 预算
      P-->>API: RepositorySummary 或 ProviderError
      API-->>UI: 200 result（四类之一）+ 时间 / 默认分支 / retryAfterAt
      Note over API,DB: 不写库、不写日志正文、不写会话/制品/AiCallRecord
    end
  else 保存绑定
    U->>UI: 点击保存
    UI->>API: POST /projects/{projectId}/repo-bindings
    API->>V: provider / repoIdentifier / apiBaseUrl / token
    API->>DB: 唯一性 (project_id, provider, repo_key, active_flag='1')
    alt 重复
      DB-->>API: 409 repo_binding_duplicate
      API-->>UI: 提示重复，原绑定与令牌不变
    else 不重复
      API->>Cry: encrypt_token(token) + mask_token(token)
      API->>DB: 写 binding(status='unverified', active_flag='1')
      API-->>UI: 201 RepoBindingSummary（只回掩码）
    end
  else 已保存测试
    U->>UI: 点击「测试连接」
    UI->>API: POST /repo-bindings/{id}/test-connection
    API->>DB: 取 binding；revoked → 409
    API->>Cry: decrypt_token()
    API->>P: get_repository(repo)，10s
    alt 成功
      API->>DB: status='connected'，lastVerified*
    else auth / permission / not_found
      API->>DB: status='token_invalid'
    else network / timeout / rate_limit / 5xx
      API->>DB: 状态不变
    end
    API-->>UI: 200 result + bindingStatus
  end
```

## 3. 同步基线（US-019）

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant API as POST /repo-bindings/{id}/sync
  participant S as RepoSyncService
  participant DB as RepoRepository
  participant P as Provider

  U->>API: 点击「同步」
  API->>DB: claim：UPDATE … sync_started_at=now<br/>WHERE status!='revoked' AND (NULL OR < now-900s)
  alt rowcount=0
    DB-->>API: 409 sync_in_progress
    API-->>U: 「同步进行中」，不产生第二条记录
  else claim 成功
    API->>DB: INSERT repo_sync_record(status='running')
    API->>P: get_repository + list_branches（分页拉全）+ list_commits(per_page=100, 1 页)
    alt 任一请求失败
      P-->>S: ProviderError（auth/network/rate_limit/permission/…）
      S->>DB: 更新 running 记录为 failed；更新 binding 的 last_sync_*；旧快照不动
      S->>DB: 释放 claim（sync_started_at=NULL）
      API-->>U: 200 record.status='failed' + 上次成功时间/基线保留
    else 全部成功
      S->>DB: 单事务：删旧 repo/branch/commit 快照 → 插新行 → 更新 binding 摘要 → 记录 success
      S->>DB: 释放 claim
      API-->>U: 200 record.status='success'（耗时 / 仓库 1 / 分支 N / 提交 ≤100）
    end
  end
```

不变量：

- 网络 IO 全部在写事务之外完成；写事务只做「删旧 + 插新 + 更新摘要 + 写记录」。
- 失败时 `last_sync_success_at` 与四类快照保持上次成功值（AC-019-3）。
- 崩溃遗留的 `running` 记录在下一次 claim 时归并为 `failed(interrupted)`；claim TTL 900s。
- 同步不拉目录树与文件内容（AMB-023 / AMB-026）；提交固定 `per_page=100`、最多 1 页。

## 4. 实时浏览与按需读文件（US-020 / US-021 / US-022）

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant UI as RepoBrowsePage
  participant API as repo_browse
  participant S as BrowseService / FileService
  participant DB as RepoRepository
  participant P as Provider

  U->>UI: 选择仓库 / 分支
  UI->>API: GET /repositories | /branches | /commits | /tree
  API->>DB: 取 binding；revoked → 409；从未同步 → 200 空态
  API->>S: 实时请求（游标 → 供应商页码）
  S->>P: 分页请求（GitHub Link / 云效 x-next-page）
  alt 200 正常
    P-->>S: 归一化条目 + nextCursor/total
    S-->>UI: items + nextCursor（+ truncated/hasMore）
  else 401 / 403 / 404
    P-->>S: ProviderError(auth/permission)
    S->>DB: binding.status='token_invalid'
    S-->>UI: 502 provider_auth_failed / provider_permission_denied
  else 429 / remaining=0
    P-->>S: ProviderError(rate_limited, retryAfterAt?)
    S-->>UI: 502 provider_rate_limited（不自动重试）
  else 网络 / 超时 / 5xx / 非法响应
    P-->>S: ProviderError(network/timeout/server_error/invalid_response)
    S-->>UI: 502 provider_unreachable / provider_timeout / provider_invalid_response
  end

  U->>UI: 点击文件
  UI->>API: GET /file?ref=&path=
  API->>S: validate_repo_path / validate_ref
  alt 非法
    S-->>UI: 400 invalid_path / invalid_ref（不写读取记录）
  else 合法
    S->>P: read_file（流式 ≤ 1 MiB + 1）
    alt 超限
      S->>DB: 写 refused(too_large)
      S-->>UI: 413 repo_file_too_large（实际大小 + 上限，不截断）
    else 二进制 / 非 UTF-8
      S->>DB: 写 refused(binary|not_utf8)
      S-->>UI: 415 repo_file_binary / 422 repo_file_not_utf8
    else 成功
      S->>DB: 写 success（只元数据）
      S-->>UI: 200 content + path/ref/size/fetchedAt
    end
  end
```

## 5. 绑定状态机

```mermaid
stateDiagram-v2
  [*] --> unverified: 创建绑定（active_flag='1'）
  unverified --> connected: 测试成功
  unverified --> token_invalid: 测试 401/403/404
  unverified --> revoked: 解绑（active_flag=NULL，清密文）
  connected --> token_invalid: 同步/浏览/读文件 401/403/404
  connected --> revoked: 解绑
  token_invalid --> connected: 更新令牌 + 测试成功
  token_invalid --> revoked: 解绑
  revoked --> [*]: 只读保留；重新绑定新建行
```

- 网络失败、超时、限流、5xx 不改变状态（AC-018-3 / ADR-206）。
- `revoked` 为终态；重新绑定同一仓库生成新 `binding_id` 与新令牌（AC-023-6）。

## 6. 分页与游标

```mermaid
flowchart LR
  C["cursor（base64url JSON + HMAC）"] --> Verify{"签名 & 指纹<br/>binding/repo/ref/path/search"}
  Verify -- 不匹配 --> E400["400 invalid_cursor"]
  Verify -- 匹配 --> Page["取供应商页码 page"]
  Page --> Req["GitHub: page&per_page<br/>云效: page&perPage"]
  Req --> Next["下一页：GitHub Link rel=next<br/>云效 x-next-page"]
  Next --> Out["nextCursor（重新签名）"]
  Next -- 无 --> End["nextCursor=null"]
```

## 7. 数据库 ER

```mermaid
erDiagram
  PROJECT_CONTEXT ||--o{ REPO_BINDING : "拥有 0..n / RESTRICT"
  REPO_BINDING ||--o{ REPO_SYNC_RECORD : "CASCADE"
  REPO_BINDING ||--o{ REPO_METADATA_SNAPSHOT : "CASCADE"
  REPO_BINDING ||--o{ REPO_FILE_READ_RECORD : "CASCADE"

  REPO_BINDING {
    char32 binding_id PK
    bigint project_id FK
    varchar20 provider
    varchar255 api_base_url
    varchar128 org_id
    varchar128 owner
    varchar191 repo_id
    varchar255 repo_name
    varchar255 repo_key
    varchar255 display_name
    varchar255 default_branch
    varchar2048 token_ciphertext
    varchar64 token_masked
    datetime token_expires_at
    varchar20 status
    char1 active_flag
    datetime last_verified_at
    varchar20 last_verify_result
    varchar500 last_verify_message
    datetime last_sync_attempt_at
    varchar20 last_sync_status
    datetime last_sync_success_at
    int last_sync_duration_ms
    varchar20 last_sync_error_category
    varchar500 last_sync_error_message
    datetime last_sync_retry_after
    datetime sync_started_at
    datetime revoked_at
    datetime created_at
    datetime updated_at
  }
  REPO_SYNC_RECORD {
    char32 sync_id PK
    char32 binding_id FK
    datetime started_at
    datetime finished_at
    varchar20 status
    int duration_ms
    int repo_count
    int branch_count
    int commit_count
    varchar20 error_category
    varchar500 error_message
    datetime retry_after_at
    datetime created_at
  }
  REPO_METADATA_SNAPSHOT {
    char32 snapshot_id PK
    char32 binding_id FK
    varchar191 repo_id
    varchar20 kind
    varchar255 ref
    json payload
    datetime fetched_at
    boolean truncated
  }
  REPO_FILE_READ_RECORD {
    char32 read_id PK
    char32 binding_id FK
    varchar191 repo_id
    varchar255 ref
    varchar1024 file_path
    bigint byte_size
    varchar20 encoding
    varchar20 status
    varchar20 reject_reason
    datetime fetched_at
  }
```

> 唯一键：`uq_repo_binding_project_provider_repo_active(project_id, provider, repo_key, active_flag)`；`repo_sync_record` / `repo_metadata_snapshot` / `repo_file_read_record` 与 core 表之间无外键。
