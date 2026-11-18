# API Specification（API Spec）— workbench-core

> **文档状态：draft — 2026-11-18 因跨 spec 知识库注入扩展（A101 / A102 / A103 B）变更，待用户重新确认。**

> 阶段：tech-design（步骤 6，`api=yes`）。依据 `technical-design/docs/architecture-decisions.md`（ADR-009 / ADR-013 / ADR-022 ~ ADR-026）与 `docs/database-schema.md`。
> 基址 `/api/v1`，JSON；前端由同源静态文件托管（ADR-008 / ADR-027）。
> 跨域说明：本 spec 的对外 HTTP 端点只服务浏览器界面；后续业务域通过 `change-spec.md` 冻结的**进程内接口**接入（`sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete`），因此本文件没有 `[cross-domain]` 端点。

## 响应与错误约定

### 成功响应

- 资源端点直接返回资源 JSON（不套 `data` 包装，ADR-009「写操作返回资源表示」）。
- 列表统一 `{"items": [...], "nextCursor": "<opaque>" | null}`；游标由服务端 base64url 编码，客户端原样回传，不解读。
- 删除成功 `204 No Content`；无响应体的操作（登出）同样 `204`。
- 时间字段为 RFC 3339 UTC：`2026-11-18T02:30:00Z`；ID 为 JSON number；布尔为 JSON boolean。
- 分页参数：`limit`（默认 20，1–100；事件列表默认 50，1–200）、`cursor`（可选）。排序语义由各端点写明，游标编码最后一条的排序键。

### 错误响应

```json
{
  "code": "session_closed",
  "message": "会话已结束，不能继续写入。",
  "details": [{"field": "sessionId", "message": "session 42 is completed"}],
  "requestId": "b7c1e0d2f3a4"
}
```

- `details` 恒为数组，元素至少含 `message`；字段级错误带 `field`。`requestId` 为每次请求生成的短随机串，用于日志关联（不含敏感信息）。
- `Content-Type: application/json; charset=utf-8`。鉴权失败的 401 只含 `code/message/details/requestId`，不含任何业务字段。
- 认证：除 `POST /api/v1/auth/login` 外的所有端点要求有效 `aw_session` Cookie；否则 401 `unauthorized`。
- CSRF：所有 `POST/PUT/PATCH/DELETE` 校验 `Origin`（缺失时退回 `Referer`）必须命中 `AW_PUBLIC_ORIGIN` 列表；不匹配 403 `forbidden_origin`；JSON 写接口必须 `Content-Type: application/json`（上传为 `multipart/form-data`）。
- 请求体校验失败：400 `validation_error`，`details` 逐字段列出；不写任何数据（AC-003-2）。

### 错误码表

| HTTP | code | 场景 |
|------|------|------|
| 400 | `validation_error` | 字段缺失/格式/范围错误（含空正文、超限字数） |
| 400 | `validation_error` | 数据库 CHECK 约束违反的统一出口（MySQL 3819 / SQLite CHECK），消息「请求参数违反数据约束。」 |
| 400 | `prompt_too_long` | 提示 >200,000 字符（`details` 含 `charCount` / `maxChars`） |
| 400 | `text_too_long` | 粘贴正文 >200,000 字符 |
| 400 | `text_empty` | 正文为空或仅空白 |
| 400 | `file_type_not_allowed` / `file_too_large` / `too_many_files` | 上传校验（批量整体拒绝） |
| 400 | `entrance_unknown` | 未知入口 key |
| 401 | `unauthorized` | 未登录、会话过期或已吊销 |
| 401 | `login_failed` | 口令错误（不区分原因） |
| 403 | `forbidden_origin` | Origin/Referer 不匹配 |
| 404 | `project_not_found` / `provider_not_found` / `model_not_found` / `session_not_found` / `artifact_not_found` / `call_not_found` | 目标不存在或不属于当前可见范围 |
| 409 | `project_name_duplicate` | 项目名重复（大小写不敏感） |
| 409 | `model_name_duplicate` | 同提供商下模型名重复（大小写不敏感） |
| 409 | `provider_disabled` / `model_disabled` | 目标不可用于新调用 |
| 409 | `session_closed` | 会话已结束，拒绝写入/调用 |
| 409 | `conflict` | 数据库重复键/外键约束兜底（MySQL 1062 / 1451 / 1452），消息「资源已存在或状态冲突。」；资源专属 409 code（如 `project_name_duplicate`）由服务层在各端点定义，`conflict` 仅是兜底 |
| 400 | `prompt_budget_exceeded` | 提示 + 注入块 >200,000 字符（`details` 含分段字数与上限） |
| 400 | `injection_snapshot_mismatch` | 注入快照字符数与实际组装正文不一致（内部契约错误） |
| 409 | `knowledge_invalid_entries` | 知识库条目失效且 `confirmInvalidCodes` 未精确匹配（`details.invalidItems`） |
| 409 | `knowledge_injection_empty` | 确认后有效条目为空，拒绝发起空注入调用 |
| 409 | `knowledge_unavailable` | 请求携带 `knowledgeRefs` 但未安装 knowledge-base 进程内服务 |
| 410 | `artifact_file_missing` | 制品行存在但文件缺失 |
| 429 | `login_locked` | 来源 IP 连续失败锁定；带 `Retry-After` 秒数 |
| 500 | `internal_error` | 未捕获异常（日志含 requestId，响应不含堆栈） |
| 500 | `session_delete_failed` | 会话目录重命名失败，删除未执行 |
| 502 | `provider_credential_unavailable` | 凭据解密失败（不产生 AiCallRecord） |
| 502 | `ai_auth` / `ai_rate_limit` / `ai_server_error` / `ai_unreachable` / `ai_invalid_request` | 上游调用最终失败（已写 AiCallRecord） |
| 504 | `ai_timeout` | 单次尝试 120s 无响应（已写 AiCallRecord，status=timeout） |
| 507 | `artifact_write_failed` | 磁盘写入失败（已清理半成品） |

数据库错误兜底：CHECK 约束 → 400 `validation_error`；重复键/外键 → 409 `conflict`；未识别错误（如连接中断 2006）→ 500 `internal_error`。约束名与驱动原文不进入响应消息。

## 端点总览

| # | 方法 | 路径 | 描述 | 认证 | 关联 US |
|---|------|------|------|------|---------|
| 1 | POST | `/auth/login` | 口令登录 | Public | US-011 |
| 2 | POST | `/auth/logout` | 登出并吊销令牌 | Session | US-011 |
| 3 | GET | `/auth/session` | 校验登录态并刷新空闲时间 | Session | US-011 |
| 4 | GET | `/entrances` | 6 入口配置 | Session | US-001 / US-002 |
| 5 | GET | `/projects` | 项目列表 | Session | US-008 |
| 6 | POST | `/projects` | 创建项目 | Session | US-008 |
| 7 | GET | `/projects/{projectId}` | 项目详情 | Session | US-008 |
| 8 | PATCH | `/projects/{projectId}` | 编辑项目 | Session | US-008 |
| 9 | GET | `/providers` | 提供商列表（掩码） | Session | US-003 |
| 10 | POST | `/providers` | 创建提供商 | Session | US-003 |
| 11 | PATCH | `/providers/{providerId}` | 编辑/启停提供商 | Session | US-003 |
| 12 | POST | `/providers/{providerId}/connection-test` | 测试已保存提供商 | Session | US-003 |
| 13 | POST | `/providers/connection-test` | 测试未保存表单 | Session | US-003 |
| 14 | GET | `/providers/{providerId}/models` | 提供商下模型列表 | Session | US-004 |
| 15 | GET | `/models` | 跨提供商模型列表 | Session | US-004 / US-009 |
| 16 | POST | `/providers/{providerId}/models` | 登记模型 | Session | US-004 |
| 17 | PATCH | `/models/{modelId}` | 编辑/启停模型 | Session | US-004 |
| 18 | GET | `/sessions` | 会话列表（含首页最近 10 条） | Session | US-001 / US-009 |
| 19 | POST | `/sessions` | 创建会话 | Session | US-009 |
| 20 | GET | `/sessions/{sessionId}` | 会话详情 | Session | US-009 |
| 21 | POST | `/sessions/{sessionId}/complete` | 标记完成 | Session | US-009 |
| 22 | DELETE | `/sessions/{sessionId}` | 删除会话并级联清理 | Session | US-009 |
| 23 | GET | `/sessions/{sessionId}/events` | 时间线事件（升序） | Session | US-009 |
| 24 | POST | `/sessions/{sessionId}/inputs/text` | 追加文本输入事件 | Session | US-006 |
| 25 | POST | `/sessions/{sessionId}/artifacts` | 上传会话制品 | Session | US-007 |
| 26 | GET | `/artifacts/{artifactId}` | 制品元数据 | Session | US-007 |
| 27 | GET | `/artifacts/{artifactId}/content` | 制品预览/下载 | Session | US-007 |
| 28 | POST | `/sessions/{sessionId}/ai/complete` | 发起 AI 调用（可选知识库注入） | Session | US-005 |
| 29 | GET | `/calls` | 调用记录查询 | Session | US-010 |
| 30 | GET | `/calls/{callId}` | 调用记录详情 | Session | US-010 |

## 认证与入口

##### POST /auth/login

- 描述：单用户口令登录；Argon2 校验，成功签发 `aw_session` Cookie。来源 IP 连续失败 5 次锁 5 分钟。
- 认证：无（唯一白名单端点）。关联 US-011。
- 请求：`{"password": "..."}`（1–256 字符，不记录日志）
- 200：`{"authenticated": true}` + `Set-Cookie: aw_session=<token>; HttpOnly; SameSite=Lax; Path=/[; Secure]`
- 401：`{"code":"login_failed","message":"口令错误，请重试。","details":[],"requestId":"..."}`
- 429：`{"code":"login_locked","message":"尝试次数过多，请稍后再试。","details":[{"retryAfterSeconds": 187}]}` + `Retry-After: 187`
- 400：`validation_error`（口令缺失/空）
- 约束：响应与日志不含口令原文、哈希；失败提示统一；锁定期不校验口令、不刷新计数。

##### POST /auth/logout

- 描述：立即吊销当前登录会话并清除 Cookie。
- 认证：需要。关联 US-011 / AC-011-6。
- 请求：无体。
- 204：`Set-Cookie: aw_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`
- 401：`unauthorized`（无有效会话时前端视为已登出）

##### GET /auth/session

- 描述：AuthGate 启动校验；命中即刷新 `last_seen_at`。
- 认证：需要。关联 US-011 / AC-011-5。
- 200：`{"authenticated": true, "lastSeenAt": "2026-11-18T02:20:00Z", "idleExpiresAt": "2026-11-18T10:20:00Z"}`
- 401：`unauthorized`

##### GET /entrances

- 描述：6 个入口配置（代码常量，单一来源驱动 planned/live，AC-002-3）。
- 认证：需要。关联 US-001 / US-002。
- 200：`{"items":[{"key":"case-library","name":"用例库","description":"…","domain":"test-case","status":"planned"}, …]}`
- 入口 key 固定：`case-library` / `bug-analysis` / `log-triage` / `sql-analysis` / `regression-list` / `test-report`；本期全部 `planned`。

## 项目上下文

##### GET /projects

- 认证：需要。关联 US-008。
- 查询：`limit`、`cursor`；排序 `updated_at DESC, project_id DESC`。
- 200：`{"items":[{"projectId":1,"name":"支付中心","repoUrl":"https://…","techStack":"Java 21 / MySQL","requirementSource":"…","notes":"…","createdAt":"…","updatedAt":"…"}],"nextCursor":null}`

##### POST /projects

- 认证：需要。关联 US-008 / AC-008-1。
- 请求：`{"name":"支付中心","repoUrl":"https://git.example.com/pay","techStack":"Java 21","requirementSource":"PRD v3","notes":""}`（`name` 必填 1–100；`repoUrl` 可选 http(s) 绝对地址；文本字段可空）
- 201：项目对象（同上，含 `projectId`）
- 409：`project_name_duplicate`（`details:[{"field":"name"}]`）
- 400：`validation_error`

##### GET /projects/{projectId}

- 认证：需要。关联 US-008 / AC-008-2。
- 200：项目对象；404：`project_not_found`

##### PATCH /projects/{projectId}

- 认证：需要。关联 US-008 / AC-008-2。
- 请求：部分字段，`{"techStack":"Java 21 / MySQL 8.4","requirementSource":"PRD v4"}`；显式 `null` 清空可空字段；`name` 参与唯一性校验。更新 `updatedAt`。
- 200：项目对象；404 / 409 / 400 同上。
- 说明：不提供项目删除（`DELETE` 未定义）；删除项目会使历史会话失去归属，超出本期需求。

## AI 提供商与模型

##### GET /providers

- 认证：需要。关联 US-003。
- 200：`{"items":[{"providerId":1,"name":"OpenAI","protocol":"openai_compatible","baseUrl":"https://api.openai.com/v1","apiKeyMasked":"sk-****abcd","enabled":true,"createdAt":"…","updatedAt":"…"}],"nextCursor":null}`
- 任何响应都不含 `apiKey` 或密文（AC-003-1 / AC-REQ-3）。

##### POST /providers

- 认证：需要。关联 US-003 / AC-003-1/2。
- 请求：`{"name":"OpenAI","protocol":"openai_compatible","baseUrl":"https://api.openai.com/v1","apiKey":"sk-…"}`
- 校验：`name` 1–100；`protocol` ∈ `openai_compatible|anthropic`；`baseUrl` http(s)、无 userinfo、≤500；`apiKey` 1–512。
- 201：提供商对象（掩码）；400：`validation_error`（逐字段）。
- 写入：`apiKey` 经 AES-256-GCM 加密为 `v1:<nonce_b64>:<ciphertext_b64>` 后落库；不回显。

##### PATCH /providers/{providerId}

- 认证：需要。关联 US-003 / AC-003-4。
- 请求：`{"enabled":false}` / `{"baseUrl":"…"}` / `{"apiKey":"…"}`；`apiKey` 缺省或空串表示不修改（UXAMB-006）。
- 200：提供商对象；400/404。
- 语义：停用提供商后其模型不再可选；历史 AiCallRecord 仍可查（含快照）。

##### POST /providers/{providerId}/connection-test

- 描述：用已保存配置发起最小请求，10s 独立超时；不写会话、制品或 AiCallRecord（AC-003-3）。
- 认证：需要。关联 US-003。
- 请求：`{"baseUrl":"https://…","apiKey":"sk-…"}`（两者均可选，用于「表单当前值、不落库」；缺省用已存储值）
- 200：`{"ok":true,"latencyMs":420,"modelCount":57,"errorCode":null}` 或 `{"ok":false,"latencyMs":10000,"modelCount":null,"errorCode":"timeout"}`
- `errorCode` ∈ `auth|rate_limit|server_error|timeout|unreachable|invalid_request|credential_unavailable`；上游失败仍返回 200（测试结果），不抛业务错误。
- 404：`provider_not_found`；400：`validation_error`。

##### POST /providers/connection-test

- 描述：未保存的新提供商表单测试（明文密钥只在内存中使用，不落库、不写日志）。
- 认证：需要。关联 US-003。
- 请求：`{"protocol":"anthropic","baseUrl":"https://api.anthropic.com/v1","apiKey":"sk-…"}`
- 200：同上。
- 说明：与上一条响应结构一致；前端在「新建」状态使用本端点。

##### GET /providers/{providerId}/models

- 认证：需要。关联 US-004。
- 查询：`limit`、`cursor`、`enabled`（可选）。
- 200：`{"items":[{"modelId":1,"providerId":1,"modelName":"gpt-4.1","displayName":"GPT-4.1","defaultTemperature":0.7,"defaultMaxTokens":4096,"enabled":true,"createdAt":"…"}],"nextCursor":null}`

##### GET /models

- 描述：跨提供商查询模型，供新建会话对话框选择「启用且提供商启用」的模型。
- 认证：需要。关联 US-004 / US-009 / AC-004-3。
- 查询：`providerId`、`enabled`（`true|false`）、`limit`、`cursor`。
- 200：`{"items":[{"modelId":3,"modelName":"gpt-4.1","displayName":"GPT-4.1","defaultTemperature":0.7,"defaultMaxTokens":4096,"enabled":true,"provider":{"providerId":1,"name":"OpenAI","enabled":true}}],"nextCursor":null}`
- 说明：`enabled=true` 时同时要求提供商启用；不返回密钥或密文。

##### POST /providers/{providerId}/models

- 认证：需要。关联 US-004 / AC-004-1/2。
- 请求：`{"modelName":"gpt-4.1","displayName":"GPT-4.1","defaultTemperature":0.7,"defaultMaxTokens":4096}`
- 校验：`modelName/displayName` 1–191；`defaultTemperature` 0–2（两位小数）；`defaultMaxTokens` 1–1,000,000。
- 201：模型对象；409：`model_name_duplicate`；404：`provider_not_found`；400。
- 说明：提供商停用时不阻止登记模型，但该模型不可选。

##### PATCH /models/{modelId}

- 认证：需要。关联 US-004。
- 请求：`{"displayName":"GPT-4.1","defaultTemperature":0.2,"defaultMaxTokens":8192,"enabled":false}`
- 200：模型对象；404：`model_not_found`；400。
- 说明：`modelName` 不可改（改名等于新模型）；默认参数只影响后续调用，不影响历史记录。

## 会话

##### GET /sessions

- 认证：需要。关联 US-009 / AC-001-3 / AC-009-2。
- 查询：`projectId`、`status`（`in_progress|completed|failed`）、`limit`、`cursor`；排序 `updated_at DESC, session_id DESC`。
- 200：

```json
{"items":[{"sessionId":42,"project":{"projectId":1,"name":"支付中心"},"entranceKey":"bug-analysis","title":"订单超时排查","status":"in_progress","model":{"modelId":3,"modelName":"gpt-4.1","displayName":"GPT-4.1","providerId":1,"providerName":"OpenAI"},"createdAt":"…","updatedAt":"…","closedAt":null}],"nextCursor":null}
```

- 首页最近 10 条：同端点 `limit=10&cursor=null`（不额外开端点）。

##### POST /sessions

- 认证：需要。关联 US-009 / AC-009-1 / AC-008-3 / AC-010。
- 请求：`{"projectId":1,"entranceKey":"bug-analysis","title":"订单超时排查","modelId":3}`
- 校验：项目存在；模型存在且 `model.enabled && provider.enabled`；入口 key 合法；标题 1–200。
- 201：会话对象；404 `project_not_found|model_not_found`；409 `model_disabled|provider_disabled`；400。

##### GET /sessions/{sessionId}

- 认证：需要。关联 US-009 / AC-009-3。
- 200：会话对象；404：`session_not_found`

##### POST /sessions/{sessionId}/complete

- 描述：用户二次确认后标记完成；写 `status_change` 事件（`local-user`），更新 `closed_at`。
- 认证：需要。关联 US-009 / AC-009-4。
- 请求：无体。
- 200：会话对象（`status=completed`）；409：`session_closed`（已结束，幂等重复调用也返回 409）；404。

##### DELETE /sessions/{sessionId}

- 描述：删除整个会话并级联事件、制品文件与调用记录（先文件进 trash，再删库）。
- 认证：需要。关联 US-009 / AC-009-5。
- 204；404：`session_not_found`；500：`session_delete_failed`（目录重命名失败，数据未删）。

##### GET /sessions/{sessionId}/events

- 认证：需要。关联 US-009 / AC-009-3。
- 查询：`limit`（默认 50，最大 200）、`cursor`；排序 `event_id ASC`（时间线发生顺序）。
- 200：

```json
{"items":[{"eventId":7,"sessionId":42,"type":"input_text","payload":{"title":"报错日志","text":"…","charCount":1280},"createdAt":"…"}],"nextCursor":null}
```

- 事件类型与 payload 见 `database-schema.md` §2.8；`knowledge_injection` 事件序列化时每个 item 附 `kbDeleted`（读取时按 `kbId` 左连接 `knowledge_base`）；404：`session_not_found`。

##### POST /sessions/{sessionId}/inputs/text

- 认证：需要。关联 US-006 / AC-006-1/2/3。
- 请求：`{"title":"报错日志","text":"…"}`
- 校验：标题 1–200；`text` 去空白后非空；`len(text) <= 200000`（按 Unicode 字符计）。
- 201：`{"eventId":7,"sessionId":42,"type":"input_text","payload":{…},"createdAt":"…"}`；同时刷新会话 `updated_at`。
- 400：`text_empty|text_too_long|validation_error`（`details` 含 `charCount`、`maxChars`）；409：`session_closed`；404。

##### POST /sessions/{sessionId}/artifacts

- 描述：上传 1–10 个白名单文本文件；批量全成功或全拒绝；同名自动改名。
- 认证：需要。关联 US-007 / AC-007-1/2/3。
- 请求：`multipart/form-data`，重复字段 `files`；单文件 ≤10MB；白名单 `.txt .md .markdown .log .json .yaml .yml .csv .sql`。
- 201：`{"items":[{"artifactId":9,"sessionId":42,"kind":"upload","fileName":"app-1.log","mimeType":"text/plain","byteSize":20480,"createdAt":"…"}],"events":[{"eventId":8,"type":"artifact","payload":{…}}]}`
- 400：`file_type_not_allowed|file_too_large|too_many_files`（`details` 列出每个不合格文件与原因，整批不落盘）；507：`artifact_write_failed`；409：`session_closed`；404。
- 约束：客户端文件名不参与路径拼接；流式写临时文件，校验通过后才移入 `sessions/<sessionId>/`。

## 制品

##### GET /artifacts/{artifactId}

- 认证：需要。关联 US-007 / AC-007-1。
- 200：`{"artifactId":9,"sessionId":42,"kind":"upload","fileName":"app-1.log","mimeType":"text/plain","byteSize":20480,"createdAt":"…"}`
- 404：`artifact_not_found`

##### GET /artifacts/{artifactId}/content

- 描述：预览或下载制品内容。
- 认证：需要。关联 US-007 / ADR-013。
- 查询：`mode=inline|download`（默认 `inline`）；`max_bytes` 仅 inline 有效，默认/上限 262144，超过返回 400。
- 200：原始字节。响应头：
  - `Content-Type` 由扩展名白名单映射（`.json` → `application/json`；`.csv` → `text/csv`；其余 → `text/plain; charset=utf-8`），不采信客户端声明；
  - `X-Content-Type-Options: nosniff`；
  - `Content-Disposition: inline; filename="app-1.log"; filename*=UTF-8''app-1.log`（download 时 `attachment`）；
  - `Content-Length`。
- 404：`artifact_not_found`；410：`artifact_file_missing`（行在文件不在）；400：`validation_error`（`max_bytes` 越界）；409？无。

## AI 调用

##### POST /sessions/{sessionId}/ai/complete

- 描述：基座验证面板发起调用，模型固定为会话模型；可覆盖 temperature / max_tokens（UXAMB-010）；可选携带知识库引用，由 core 在调用前调用 knowledge-base 的进程内服务做失效重校验、组装与字符预算（A103 B / ADR-042）。每次进入提供商（成功、失败、超时、中断）都写 AiCallRecord。
- 认证：需要。关联 US-005 / US-010。
- 请求：

```json
{
  "prompt": "请分析以下日志…",
  "temperature": 0.2,
  "maxTokens": 2048,
  "knowledgeRefs": [{"kbId": 5, "entryCodes": ["ENT-012", "BR-003"]}],
  "confirmInvalidCodes": [{"kbId": 5, "code": "ENT-009"}]
}
```

- 字段：`prompt` 1–200,000；`temperature` 0–2；`maxTokens` 1–1,000,000；`knowledgeRefs` 可选（缺省 = 不注入，行为与旧版完全一致）；`confirmInvalidCodes` 可选，只在用户已看到失效清单后回传，服务端要求与重算失效集**完全相等**。
- 200：

```json
{"callId":17,"sessionId":42,"status":"success","resultText":"…","latencyMs":2140,"retryCount":0,
 "model":{"modelId":3,"displayName":"GPT-4.1","modelName":"gpt-4.1","providerId":1,"providerName":"OpenAI"},
 "knowledgeInjection":[{"kbId":5,"kbName":"支付中心知识库","kbVersion":2,"entryCodes":["ENT-012","BR-003"],"injectedChars":1840,"kbDeleted":false}],
 "createdAt":"…","finishedAt":"…"}
```

- 无注入时 `knowledgeInjection = null`。
- 失败（均已写 AiCallRecord，`details` 含 `callId`、`retryCount`）：
  - 502 `ai_auth` / `ai_rate_limit` / `ai_server_error` / `ai_unreachable` / `ai_invalid_request`
  - 504 `ai_timeout`
  - 502 `provider_credential_unavailable`（未进入提供商，不写记录）
- 前置拒绝（不写 AiCallRecord，AC-005-3）：404 `session_not_found`；409 `session_closed|model_disabled|provider_disabled`；400 `validation_error|prompt_too_long|prompt_budget_exceeded|injection_snapshot_mismatch`。
- 知识库注入拒绝（不发起外部请求、不写 AiCallRecord）：
  - 409 `knowledge_invalid_entries`：`details.invalidItems = [{kbId, code, reason}]`，需用户确认后带 `confirmInvalidCodes` 重试；
  - 409 `knowledge_injection_empty`：确认后有效集为空；
  - 409 `knowledge_unavailable`：请求携带 `knowledgeRefs` 但本部署未安装 knowledge-base 的进程内服务；
  - 400 `prompt_budget_exceeded`：`details = {promptChars, injectedChars, totalChars, limit}`（上限 `AW_PROMPT_MAX_CHARS=200000`）。
- 并发：进程内信号量默认 4；排队等待不计入 `latencyMs`。
- 说明：本路径取代早期草案的 `POST /sessions/{sessionId}/calls`（未实现）；按 ADR-103 B 不新增 `/knowledge-injection/calls`。

##### GET /calls

- 认证：需要。关联 US-010 / AC-010-1/2/3。
- 查询：`sessionId`、`projectId`、`status`（`success|failed|timeout`）、`from`、`to`（RFC 3339）、`limit`、`cursor`；排序 `created_at DESC, call_id DESC`。
- 200：

```json
{"items":[{"callId":17,"sessionId":42,"project":{"projectId":1,"name":"支付中心"},"model":{"modelId":3,"displayName":"GPT-4.1","providerName":"OpenAI"},"status":"failed","promptPreview":"请分析以下日志…","promptCharCount":1820,"knowledgeInjection":[{"kbId":5,"kbName":"支付中心知识库","kbVersion":2,"entryCodes":["ENT-012"],"injectedChars":1840,"kbDeleted":false}],"latencyMs":120000,"retryCount":1,"errorCode":"timeout","errorMessage":"upstream request timed out","createdAt":"…","finishedAt":"…"}],"nextCursor":null}
```

- 无匹配返回空 `items` 与 `nextCursor:null`（AC-010-3），不报错。
- `promptPreview` 与 `errorMessage` 不含密钥；`resultText` 不在列表返回。
- `knowledgeInjection`：无注入为 `null`；有注入时每个条目带 `kbDeleted`（读取时按 `kbId` 左连接 `knowledge_base`，行或表不存在为 `true`），历史快照不因知识库删除而改写（ADR-042）。

##### GET /calls/{callId}

- 认证：需要。关联 US-010 / AC-010-2。
- 200：调用对象（含 `resultText`，成功时；含 `knowledgeInjection` 与 `kbDeleted`）；404：`call_not_found`。

## 健康检查（无匿名端点）

容器健康检查按 ADR-026 请求受保护端点并期望 401：

```sh
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/auth/session | grep -qx 401
```

## 前端调用约定

- 认证：`fetch(..., {credentials: 'same-origin'})`；前端不读取 Cookie 值；任意 401 → 跳 `/login?next=<站内路径>`。
- 写请求统一带 `Content-Type: application/json`（上传除外）；服务端校验 Origin。
- 错误：读取 `code` 做分支，`message` 直接展示；字段错误按 `details[].field` 定位到 `FormField`。
- 分页：TanStack Query 用 `useInfiniteQuery`，`getNextPageParam: (last) => last.nextCursor`。
- 调用面板：`POST /sessions/{id}/ai/complete` 前端超时设为 300s（大于服务端最坏 2×120s + 退避），失败后刷新时间线与调用记录；知识库引用由 knowledge-base 页面按同一端点提交，core 面板不注入时省略 `knowledgeRefs`。
- 上传：`FormData` 逐文件追加到 `files`；前端先做白名单/大小/数量三查，服务端仍独立校验。
