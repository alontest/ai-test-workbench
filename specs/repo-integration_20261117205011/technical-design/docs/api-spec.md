# API Specification — repo-integration

> 阶段：tech-design（步骤 6，`api=yes`）。依据 `technical-design/docs/architecture-decisions.md`（ADR-205 / ADR-206 / ADR-208 / ADR-209 / ADR-211 / ADR-212 / ADR-213 / ADR-215）与 `design.md`。
> 基址 `/api/v1`，JSON；与 core 同源部署。**全部 15 个端点受 core 的 `require_session` 中间件保护**，无匿名端点；`POST` / `PATCH` 另走 core 的 `require_same_origin`（Origin/Referer 命中 `AW_PUBLIC_ORIGIN`，否则 403 `forbidden_origin`）。
> 跨域只读契约只有 `GET /repo-bindings/{bindingId}/baseline` 与 `GET /repo-bindings/{bindingId}/file`；其他端点不承诺跨域兼容。

## 1. 通用约定

- 资源端点直接返回资源 JSON，不套 `data`；创建 201，删除/解绑返回资源表示，列表 `{"items": [...], "nextCursor": "<opaque>" | null}`。
- 字段命名 camelCase；`projectId` 为 number（core `project_context` 主键），`bindingId` / `syncId` 为 string（`CHAR(32)` hex）。
- 时间 RFC 3339 UTC（`2026-11-20T02:30:00Z`）；未知值用 `null`，不用空串冒充。
- 错误体沿用 core：

```json
{
  "code": "repo_binding_duplicate",
  "message": "同一项目下已存在该仓库绑定。",
  "details": [{"field": "repoIdentifier", "message": "同一提供商与仓库已绑定，原绑定与令牌不变。"}],
  "requestId": "b7c1e0d2f3a4"
}
```

- `details` 恒为数组（映射型 `details` 仅用于 `retryAfterAt` 等固定结构，键名固定）；字段级错误带 `field`。
- **令牌零出口**：任何响应、`details`、日志、同步/读取记录都不出现完整令牌或密文；只回显 `tokenMasked`（如 `ghp_****abcd`）。
- **供应商原文零回显**：502 错误只返回固定码与映射后的可读文案，`details` 只允许 `{provider, statusCode, category, retryAfterAt}`。

### 1.1 分页与游标

| 端点组 | `limit` 默认 | 范围 | 游标 |
|--------|-------------|------|------|
| 绑定列表 / 仓库 / 分支 / 提交 | 30 | 1–100 | `cursor` 可选 |
| 目录树 | 100 | 1–100 | `cursor` 可选 |
| 同步记录 | 20 | 1–100 | `cursor` 可选 |

- `cursor` 为 base64url(JSON) + HMAC-SHA256（16 字节）的不透明串；内含 `bindingId`、`provider`、`repoKey`、`ref`、`path`、检索词指纹、供应商页码。
- 跨查询复用、跨绑定使用、篡改或签名不符 → `400 invalid_cursor`（不泄露游标内容）。
- 供应商分页在适配器内翻译：GitHub 用 `page`/`per_page` + `Link rel="next"` 取下一页页码；云效用 `page`/`perPage` + `x-next-page` / `x-total-pages`。服务层只看到 `nextCursor`。

### 1.2 `truncated` 与 `hasMore` 语义

- `hasMore=true`：还有下一页，`nextCursor` 非空；前端显示「加载下一页」。
- `truncated=true`：供应商明确标记或达到供应商单页上限，**结果不完整**；前端显示「目录树不完整，请逐级浏览」。
- 两者可同时为 `false`；不允许「不完整却报告完成」。GitHub `contents` 目录列表无分页，达到 1,000 条上限即 `truncated=true`、`hasMore=false`；云效 `ListFiles` 官方无分页，`hasMore=false`、`truncated=false`（若上游截断，按返回条数在上限处置 `truncated=true`）。
- 仓库 / 分支 / 提交列表只有 `nextCursor` / `total`，没有 `truncated`。

### 1.3 状态与守卫

| 条件 | 行为 |
|------|------|
| `bindingId` 不存在 | 404 `binding_not_found`（不区分「无权查看」与「不存在」） |
| `projectId` 不存在 | 404 `project_not_found` |
| `status='revoked'` | 除 `GET /baseline` 外，所有需要供应商请求或写操作的端点 → 409 `binding_revoked`；不发起任何外呼 |
| 从未成功同步 | 浏览类端点（repositories / branches / commits / tree）→ 200 `{metadataSynced:false, items:[], nextCursor:null, total:null, guide:"sync_first"}`，不发外呼、不返回错误页 |
| 并发同步 | 409 `sync_in_progress`，不产生第二条同步记录 |

### 1.4 错误码总表

| HTTP | code | 场景 |
|------|------|------|
| 400 | `invalid_provider` | `provider` 不是 `yunxiao` / `github` |
| 400 | `invalid_repo_identifier` | 仓库标识为空、格式不符或与 provider 不匹配 |
| 400 | `invalid_api_base_url` | 非 https、含路径/查询/片段、非 443、私网/回环地址，或 GitHub 传自定义域名 |
| 400 | `invalid_path` | 文件路径为空、含 `..`、绝对路径、控制字符、段/总长超限 |
| 400 | `invalid_ref` | ref 为空、含非法字符、`..`、`@{`、空白或超长 |
| 400 | `token_required` | 创建/更新令牌时令牌为空 |
| 400 | `invalid_cursor` | 游标签名不符、跨查询复用、篡改或损坏 |
| 400 | `validation_error` | `limit` 越界、`search` 超长等通用参数错误（`details` 逐字段） |
| 401 | `unauthorized` | 未登录或会话过期（core 统一返回） |
| 403 | `forbidden_origin` | `POST/PATCH` 的 Origin/Referer 不匹配（core 统一返回） |
| 404 | `project_not_found` | `projectId` 不存在 |
| 404 | `binding_not_found` | 绑定不存在（不区分无权查看） |
| 409 | `repo_binding_duplicate` | 同项目同 provider 同仓库已存在在绑行 |
| 409 | `sync_in_progress` | 同绑定已有未过期 claim；不产生第二条记录 |
| 409 | `binding_revoked` | 绑定已解绑，拒绝发起供应商请求 |
| 409 | `repo_not_synced` | **预留码**：本期端点不返回；未同步一律 200 空态（ADR-208 / OQ-RI-03） |
| 413 | `repo_file_too_large` | 文件 > 1,048,576 字节；`details` 含实际大小与上限，不截断 |
| 415 | `repo_file_binary` | base64 内容或含 NUL，判定为二进制 |
| 422 | `repo_file_not_utf8` | 文本解码失败，不是合法 UTF-8 |
| 502 | `provider_auth_failed` | 供应商 401 |
| 502 | `provider_permission_denied` | 供应商 403（非限流）或 404 |
| 502 | `provider_rate_limited` | 供应商 429、403+限流信号、`X-RateLimit-Remaining: 0` |
| 502 | `provider_unreachable` | DNS/连接/TLS 失败、5xx |
| 502 | `provider_timeout` | 连接或读取超时 |
| 502 | `provider_invalid_response` | 2xx 但 JSON 非法/结构不符/超过 5 MiB，或其他 4xx |
| 500 | `internal_error` | 未捕获异常（日志含 requestId，响应不含堆栈与正文） |

错误优先级：请求参数校验（400）→ 资源存在性（404）→ 绑定状态（409）→ 供应商调用（502）。同一请求只返回第一个命中的错误码；`details` 可列出全部字段级问题。

## 2. 错误分类单一映射表（ADR-206）

> 一行一个供应商信号；判定顺序为「网络异常 → 限流信号 → 状态码」。**403 先看限流信号**（`Retry-After`、`X-RateLimit-Remaining: 0`、响应体含 rate limit 文案），命中即 `rate_limited`，否则 `permission_denied`。

| 供应商信号 | `ProviderError.category` | 测试连接四类结果 | API 响应 | 绑定状态副作用 | 同步记录 `errorCategory` |
|-----------|--------------------------|-----------------|---------|---------------|--------------------------|
| 401 | `auth` | `auth-error` | 502 `provider_auth_failed` | `token_invalid` | `auth` |
| 403 + 限流信号 | `rate_limited` | `unreachable` | 502 `provider_rate_limited` | 不变 | `rate_limit` |
| 403 其他 | `permission_denied` | `permission-denied` | 502 `provider_permission_denied` | `token_invalid` | `permission` |
| 404（仓库 / 分支 / 提交 / 目录 / 文件） | `not_found` | `permission-denied` | 502 `provider_permission_denied` | `token_invalid` | `permission` |
| 429 | `rate_limited` | `unreachable` | 502 `provider_rate_limited` | 不变 | `rate_limit` |
| 连接超时 / 读取超时 | `timeout` | `unreachable` | 502 `provider_timeout` | 不变 | `network` |
| DNS 失败 / 连接被拒 / TLS 失败 | `network` | `unreachable` | 502 `provider_unreachable` | 不变 | `network` |
| 5xx | `server_error` | `unreachable` | 502 `provider_unreachable` | 不变 | `other` |
| 2xx 但 JSON 非法 / 结构不符 / 超过 5 MiB | `invalid_response` | `unreachable` | 502 `provider_invalid_response` | 不变 | `other` |
| 200 且 `X-RateLimit-Remaining: 0` | `rate_limited` | `unreachable` | 502 `provider_rate_limited` | 不变 | `rate_limit` |
| 其他 4xx（非 401/403/404/429） | `invalid_response` | `unreachable` | 502 `provider_invalid_response` | 不变 | `other` |

映射规则：

- 权限不足不得归为网络失败；网络失败不得归为鉴权失败；限流不得归为鉴权失败；5xx / 非法响应不得伪装成功。
- 测试连接固定返回四类枚举；限流 / 5xx / 超时在四类中归「网络失败」，但 `message` 与 `retryAfterAt` 保留可读原因。
- `retryAfterAt` 取值：GitHub `retry-after`（秒）或 `x-ratelimit-reset`（epoch 秒）；云效无官方限流头 → `null`。无头不猜时间。
- 同步失败是「已完成的业务结果」，返回 **200 + `record.status='failed'`**，不抛 502；浏览 / 读文件 / 测试遇到上述失败 → 502 固定码。

## 3. 端点列表

### 3.1 绑定与生命周期（端点 1~9）

#### 1. GET /projects/{projectId}/repo-bindings

- **描述**：项目下全部绑定（含已解绑，按 `createdAt DESC`），用于项目上下文页列表。
- **关联 US**：US-017、US-019、US-023。
- **请求参数**：`limit`（默认 30，1–100）、`cursor`。
- **200 响应**：`{"items": [RepoBindingSummary], "nextCursor": null}`。
- **错误**：404 `project_not_found`；400 `invalid_cursor` / `validation_error`。

`RepoBindingSummary`：

```json
{
  "bindingId": "6f1c9a0e5b7d4c2a8e3f1b0d9c7a6e54",
  "projectId": 12,
  "provider": "github",
  "apiBaseUrl": "https://api.github.com",
  "orgId": null,
  "owner": "pay",
  "repoId": "pay/checkout",
  "repoName": "pay/checkout",
  "displayName": "pay/checkout",
  "defaultBranch": "main",
  "tokenMasked": "ghp_****abcd",
  "tokenExpiresAt": null,
  "status": "connected",
  "lastVerifiedAt": "2026-11-20T02:10:00Z",
  "lastVerifyResult": "success",
  "lastVerifyMessage": null,
  "lastSyncAttemptAt": "2026-11-20T02:20:00Z",
  "lastSyncStatus": "success",
  "lastSyncSuccessAt": "2026-11-20T02:20:06Z",
  "lastSyncDurationMs": 6200,
  "lastSyncErrorCategory": null,
  "lastSyncErrorMessage": null,
  "lastSyncRetryAfter": null,
  "baseline": {"ref": "main", "sha": "a1b2c3d", "fetchedAt": "2026-11-20T02:20:06Z"},
  "revokedAt": null,
  "createdAt": "2026-11-19T08:00:00Z",
  "updatedAt": "2026-11-20T02:20:06Z"
}
```

#### 2. POST /projects/{projectId}/repo-bindings

- **描述**：创建绑定：校验 → 加密令牌 → 唯一性检查 → 写 `status='unverified'`。
- **关联 US**：US-017（AC-017-1 ~ AC-017-6）、AC-REQ-25。
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider` | string | 是 | `yunxiao` / `github` |
| `repoIdentifier` | string | 是 | GitHub：`owner/repo`；云效：`group/repo` 全路径或数字 `repoId` |
| `orgId` | string | 云效必填 | 云效组织 ID；GitHub 忽略 |
| `apiBaseUrl` | string | 否 | 云效默认 `https://openapi-rdc.aliyuncs.com`；GitHub 固定 `https://api.github.com`，传入其他值 → 400 |
| `token` | string | 是 | 只读最小权限令牌；仅进请求体，不回显 |

- **201 响应**：`RepoBindingSummary`（`tokenMasked` 必有，完整令牌/密文永不出现）。
- **错误**：400 `invalid_provider` / `invalid_repo_identifier` / `invalid_api_base_url` / `token_required` / `validation_error`；404 `project_not_found`；409 `repo_binding_duplicate`（原绑定与令牌不变）。

#### 3. GET /repo-bindings/{bindingId}

- **200 响应**：`RepoBindingSummary`。
- **错误**：404 `binding_not_found`。

#### 4. PATCH /repo-bindings/{bindingId}/token

- **描述**：只替换 `token_ciphertext` / `token_masked` / `updated_at`；`bindingId`、快照、同步记录不变。
- **关联 US**：US-017（AC-017-4）、US-023（AC-023-2）。
- **请求体**：`{"token": "..."}`（必填；空 → 400 `token_required`）。
- **200 响应**：`RepoBindingSummary`。
- **错误**：400 `token_required`；404 `binding_not_found`；409 `binding_revoked`。

#### 5. POST /repo-bindings/{bindingId}/test-connection

- **描述**：对已保存绑定发起一次只读请求（仓库详情），10s 预算；成功更新 `status` / `lastVerified*`。
- **关联 US**：US-018（AC-018-1 ~ AC-018-5）、AC-REQ-26。
- **请求体**：无。
- **200 响应**：

```json
{
  "result": "success",
  "testedAt": "2026-11-20T02:10:00Z",
  "message": "连接成功。",
  "defaultBranch": "main",
  "latestCommitAt": "2026-11-20T01:58:00Z",
  "retryAfterAt": null,
  "bindingStatus": "connected"
}
```

`result ∈ success | auth-error | unreachable | permission-denied`；`bindingStatus` 为更新后的绑定状态。
- **错误**：404 `binding_not_found`；409 `binding_revoked`；502 仅在内部无法分类时使用（正常失败也返回 200 + `result`）。

#### 6. POST /repo-bindings/test-connection

- **描述**：用表单当前值测试，**不落库、不写日志正文、不写会话/制品/AiCallRecord**；字段变更由前端置 `stale`，服务端不保存结果。
- **关联 US**：US-018（AC-018-1）、AMB-028。
- **请求体**：同端点 2 的 `provider` / `repoIdentifier` / `orgId?` / `apiBaseUrl?` / `token`。
- **200 响应**：同端点 5，`bindingStatus=null`。
- **错误**：400 `invalid_provider` / `invalid_repo_identifier` / `invalid_api_base_url` / `token_required`；不产生绑定行。

#### 7. POST /repo-bindings/{bindingId}/sync

- **描述**：手动同步基线：仓库详情 1 条 + 全部分支 + 最近 100 条提交；单事务覆盖快照；失败保留旧快照。
- **关联 US**：US-019（AC-019-1 ~ AC-019-6）、AC-REQ-27 / AC-REQ-28。
- **请求体**：无。
- **200 响应**：

```json
{
  "record": {
    "syncId": "9a0b…", "bindingId": "6f1c…",
    "startedAt": "2026-11-20T02:20:00Z", "finishedAt": "2026-11-20T02:20:06Z",
    "status": "success", "durationMs": 6200,
    "repoCount": 1, "branchCount": 18, "commitCount": 100,
    "errorCategory": null, "errorMessage": null, "retryAfterAt": null
  },
  "binding": {"bindingId": "6f1c…", "status": "connected", "lastSyncSuccessAt": "2026-11-20T02:20:06Z", "baseline": {"ref": "main", "sha": "a1b2c3d", "fetchedAt": "2026-11-20T02:20:06Z"}}
}
```

- 失败同样是 **200**：`record.status='failed'`、`errorCategory ∈ auth | network | rate_limit | permission | other | interrupted`、`retryAfterAt` 可空；`binding` 的 `lastSyncSuccessAt` 与 `baseline` 保持上次成功值。
- **错误**：404 `binding_not_found`；409 `sync_in_progress`（不产生第二条记录）/ `binding_revoked`。

#### 8. GET /repo-bindings/{bindingId}/sync-records

- **描述**：最近同步记录，按 `startedAt DESC`。
- **请求参数**：`limit`（默认 20，1–100）、`cursor`。
- **200 响应**：`{"items": [SyncRecord], "nextCursor": null}`；`SyncRecord` 字段同端点 7 的 `record`。
- **错误**：404 `binding_not_found`；400 `invalid_cursor`。

#### 9. POST /repo-bindings/{bindingId}/unbind

- **描述**：二次确认后的解绑：`status='revoked'`、`active_flag=NULL`、清空密文与掩码、写 `revoked_at`；快照与记录只读保留；幂等（重复解绑返回 200 当前行）。
- **关联 US**：US-023（AC-023-4 ~ AC-023-6）、AC-REQ-33。
- **请求体**：无。
- **200 响应**：`RepoBindingSummary`（`status="revoked"`、`tokenMasked=""`、`revokedAt` 非空）。
- **错误**：404 `binding_not_found`。

### 3.2 实时浏览（端点 10~14）

> 公开响应中的 `RepositorySummary` / `BranchSummary` / `CommitSummary`：

```json
{"repoId": "pay/checkout", "fullName": "pay/checkout", "displayName": "pay/checkout", "defaultBranch": "main", "webUrl": "https://github.com/pay/checkout"}
{"name": "main", "isDefault": true, "headSha": "a1b2c3d", "committedAt": "2026-11-20T02:00:00Z"}
{"sha": "a1b2c3d4e5f6...", "shortSha": "a1b2c3d", "title": "fix(pay): 回调签名校验顺序调整", "authorName": "lin.t", "committedAt": "2026-11-20T01:21:00Z"}
```

#### 10. GET /repo-bindings/{bindingId}/repositories

- **描述**：实时仓库列表（供应商分页 + `search`）。
- **关联 US**：US-020（AC-020-1 / AC-020-3 / AC-020-4）、AC-REQ-29。
- **请求参数**：`search`（≤100）、`limit`、`cursor`。
- **200 响应**：`{"metadataSynced": true, "live": true, "items": [RepositorySummary], "nextCursor": null, "total": 42, "guide": null}`。
- 未同步：`200 {"metadataSynced": false, "live": false, "items": [], "nextCursor": null, "total": null, "guide": "sync_first"}`，不发外呼。
- **错误**：404 `binding_not_found`；409 `binding_revoked`；502 见映射表。

#### 11. GET /repo-bindings/{bindingId}/branches

- **请求参数**：`repoId`（可选，默认绑定仓库）、`search`、`limit`、`cursor`。
- **200 响应**：同 10 的包装，`items: [BranchSummary]`；默认分支 `isDefault=true`。
- **关联 US**：US-020（AC-020-2 ~ AC-020-4）。
- **错误**：同上。

#### 12. GET /repo-bindings/{bindingId}/commits

- **请求参数**：`repoId`（可选）、`ref`（**必填**，分支 / tag / sha）、`limit`、`cursor`。
- **200 响应**：`{"metadataSynced": true, "live": true, "items": [CommitSummary], "nextCursor": null, "total": 120, "guide": null}`；按提交时间倒序；空数组不是错误。
- **关联 US**：US-021（AC-021-1）。
- **错误**：400 `invalid_ref`；404；409 `binding_revoked`；502。

#### 13. GET /repo-bindings/{bindingId}/tree

- **请求参数**：`repoId`（可选）、`ref`（**必填**）、`path`（默认空串 = 根）、`limit`（默认 100，1–100）、`cursor`。
- **200 响应**：

```json
{
  "metadataSynced": true, "live": true,
  "path": "src", "ref": "main",
  "items": [
    {"name": "main.py", "path": "src/main.py", "type": "file", "sizeBytes": 8806},
    {"name": "api", "path": "src/api", "type": "dir", "sizeBytes": null}
  ],
  "truncated": false,
  "hasMore": false,
  "nextCursor": null,
  "total": 2,
  "guide": null
}
```

- **关联 US**：US-021（AC-021-2 / AC-021-3 / AC-021-4）、AC-REQ-30。
- **错误**：400 `invalid_path` / `invalid_ref` / `invalid_cursor`；404；409 `binding_revoked`；502。
- `type ∈ file | dir`；大小未知时 `sizeBytes=null`，不写 0 冒充。

#### 14. GET /repo-bindings/{bindingId}/file

- **描述**：按 ref 读取单个文件；路径/ref 校验在**发起任何外部请求之前**完成；内容只在响应中存在。
- **请求参数**：`repoId`（可选）、`ref`（必填）、`path`（必填）。
- **关联 US**：US-022（AC-022-1 ~ AC-022-5）、AC-REQ-31 / AC-REQ-34。
- **200 响应**：

```json
{
  "path": "src/main.py", "ref": "main",
  "sizeBytes": 8806, "encoding": "text",
  "content": "from api.client import CodeupClient\n...",
  "fetchedAt": "2026-11-20T02:30:00Z"
}
```

- **错误**：400 `invalid_path` / `invalid_ref`（**不写读取记录**）；404 `binding_not_found`；409 `binding_revoked`；413 `repo_file_too_large`（`details=[{field:"sizeBytes",message:"实际 3565158 字节，上限 1048576 字节"}]`，不截断）；415 `repo_file_binary`；422 `repo_file_not_utf8`；502 见映射表。
- 成功与「超限 / 二进制 / 非 UTF-8」写 `repo_file_read_record`（`status=success|refused`，`reject_reason=too_large|binary|not_utf8`）；**非法路径/ref 不写记录**（AC-022-5）。

### 3.3 跨域只读（端点 15）

#### 15. GET /repo-bindings/{bindingId}/baseline

- **描述**：只按 `bindingId` 读取同步基线（仓库 / 分支 / 提交快照），不发起供应商请求、不暴露令牌；令牌失效或已解绑时仍可读。
- **关联 US**：US-020（AC-020-4）、US-023（AC-023-4 / AC-023-5）、AC-REQ-29 / AC-REQ-33。
- **200 响应**：

```json
{
  "bindingId": "6f1c…", "provider": "github", "repoName": "pay/checkout",
  "status": "token_invalid", "revoked": false,
  "metadataSynced": true, "lastSyncSuccessAt": "2026-11-20T02:20:06Z",
  "repo": {"repoId": "pay/checkout", "fullName": "pay/checkout", "defaultBranch": "main"},
  "branches": [BranchSummary],
  "commits": [CommitSummary],
  "fetchedAt": "2026-11-20T02:20:06Z"
}
```

- 从未同步：`200 {"metadataSynced": false, "repo": null, "branches": [], "commits": [], "lastSyncSuccessAt": null, "guide": "sync_first"}`。
- **错误**：404 `binding_not_found`。

## 4. 端点总览

| # | 方法 | 路径 | 描述 | 认证 | 关联 US |
|---|------|------|------|------|---------|
| 1 | GET | `/api/v1/projects/{projectId}/repo-bindings` | 绑定列表 | Session | US-017 / 019 / 023 |
| 2 | POST | `/api/v1/projects/{projectId}/repo-bindings` | 创建绑定 | Session + Origin | US-017 |
| 3 | GET | `/api/v1/repo-bindings/{bindingId}` | 绑定详情 | Session | US-017 / 018 / 019 |
| 4 | PATCH | `/api/v1/repo-bindings/{bindingId}/token` | 更新令牌 | Session + Origin | US-017 / 023 |
| 5 | POST | `/api/v1/repo-bindings/{bindingId}/test-connection` | 已保存测试 | Session + Origin | US-018 |
| 6 | POST | `/api/v1/repo-bindings/test-connection` | 未保存测试（不落库） | Session + Origin | US-018 |
| 7 | POST | `/api/v1/repo-bindings/{bindingId}/sync` | 手动同步 | Session + Origin | US-019 |
| 8 | GET | `/api/v1/repo-bindings/{bindingId}/sync-records` | 同步记录 | Session | US-019 |
| 9 | POST | `/api/v1/repo-bindings/{bindingId}/unbind` | 解绑 | Session + Origin | US-023 |
| 10 | GET | `/api/v1/repo-bindings/{bindingId}/repositories` | 实时仓库列表 | Session | US-020 |
| 11 | GET | `/api/v1/repo-bindings/{bindingId}/branches` | 实时分支列表 | Session | US-020 |
| 12 | GET | `/api/v1/repo-bindings/{bindingId}/commits` | 实时提交列表 | Session | US-021 |
| 13 | GET | `/api/v1/repo-bindings/{bindingId}/tree` | 实时目录树 | Session | US-021 |
| 14 | GET | `/api/v1/repo-bindings/{bindingId}/file` | 按需读文件（跨域只读） | Session | US-022 |
| 15 | GET | `/api/v1/repo-bindings/{bindingId}/baseline` | 同步基线（跨域只读） | Session | US-020 / 023 |
