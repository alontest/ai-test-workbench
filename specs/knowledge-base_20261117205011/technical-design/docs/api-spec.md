# API Specification — knowledge-base

> 阶段：tech-design（步骤 6，`api=yes`）。依据 `technical-design/docs/architecture-decisions.md`（ADR-108 / ADR-109 / ADR-110 / ADR-112 / ADR-114）与 `docs/database-schema.md`。
> 基址 `/api/v1`，JSON；与 core 同源部署，前端由 core 静态托管。**全部端点受 core 的 `require_session` 保护**，无匿名端点。
> 本 spec 只新增知识库读/写与注入预览端点；**模型调用入口唯一**为 core 的 `POST /api/v1/sessions/{sessionId}/ai/complete`（见 §3），本 spec 不新增 `/knowledge-injection/calls`。

## 响应与错误约定

沿用 core（ADR-009），不自造外层包装：

- 资源端点直接返回资源 JSON，不套 `data`；写操作返回资源表示；删除成功 `204 No Content`。
- 列表统一 `{"items": [...], "nextCursor": "<opaque>" | null}`；游标为 base64url 编码，客户端原样回传，不解读。
- 时间字段 RFC 3339 UTC（`2026-11-18T02:30:00Z`）；布尔为 JSON boolean。
- **ID 类型**：`projectId` 为 JSON number（core `project_context` BigInt 主键）；`kbId` / `entryId` 为 JSON string（`CHAR(32)` hex）。
- 字段命名 camelCase。
- 错误体固定：

```json
{
  "code": "knowledge_invalid_entries",
  "message": "部分知识库条目已失效，确认后才能继续。",
  "details": [
    {"field": "knowledgeRefs", "message": "kb=7c9e... code=ENT-012 reason=superseded"}
  ],
  "requestId": "b7c1e0d2f3a4"
}
```

- `details` 恒为数组，元素至少含 `message`；字段级错误带 `field`。注入失效项固定放在 `details.invalidItems = [{kbId, code, reason}]`（reason ∈ `kb_deleted` / `entry_not_found` / `superseded`），预算错误固定放在 `details = {promptChars, injectedChars, totalChars, limit}`。
- 请求体校验失败 400 `validation_error`，`details` 逐字段列出；不写任何数据。
- 所有 `POST/DELETE` 校验 `Origin`（缺失退回 `Referer`）命中 core 的 `AW_PUBLIC_ORIGIN`，否则 403 `forbidden_origin`；上传为 `multipart/form-data`，JSON 写接口必须 `Content-Type: application/json`。
- 分页：知识库列表 `limit` 默认 50 / 1..200；条目列表 `limit` 默认 50 / 1..200（ADR-108）；`cursor` 可选。排序：知识库按 `updated_at DESC, kb_id`；条目按「`code` 精确 > `code` 前缀 > `title` > `summary` > `body`」，同档按 `code_key ASC, entry_id`。
- 检索串 `q`：长度 1..100（trim 后），转义 `% _ \` 并用 `ESCAPE '\'`；默认只搜当前版本。MySQL 对 ASCII 大小写不敏感、SQLite 仅 ASCII，非 ASCII 拉丁大小写差异不承诺一致（ADR-108）。

### 错误码表

| HTTP | code | 场景 |
|------|------|------|
| 400 | `validation_error` | 字段缺失/格式/范围错误（含 `q` 超长、`type` 非法、`limit` 越界） |
| 400 | `unsupported_file_type` | 文件扩展名不在 `.json` / `.md` / `.markdown`（`details` 逐文件） |
| 400 | `too_many_files` | 单次 > `AW_KB_MAX_FILES`（50） |
| 400 | `file_too_large` | 单文件超限（`index.json` >20MB，其他 >10MB；`details` 带实测值与上限） |
| 400 | `index_json_missing` | 本次上传不含 `index.json` |
| 400 | `index_json_invalid` | JSON 语法错误、缺最小结构（非空 `schema` + 非空 `entries`）、深度/条目数超护栏、全部条目被跳过 |
| 400 | `prompt_budget_exceeded` | `injectedChars + promptChars > AW_PROMPT_MAX_CHARS`（`details` 分段字数与上限） |
| 401 | `unauthorized` | 未登录/会话过期（core 统一返回） |
| 403 | `forbidden_origin` | Origin/Referer 不匹配（core 统一返回） |
| 404 | `project_not_found` | `projectId` 不存在 |
| 404 | `kb_not_found` | 知识库不存在或已被删除 |
| 404 | `entry_not_found` | 条目不存在或所属知识库已删除 |
| 404 | `session_not_found` | 会话不存在（core 语义） |
| 409 | `kb_name_conflict` | 同名逻辑库并发导入撞唯一约束，重试 1 次后仍冲突（并发保护，不是用户业务分支） |
| 409 | `knowledge_invalid_entries` | 失效条目未被精确确认（`details.invalidItems`）；不发起外部请求、不写 AiCallRecord |
| 409 | `knowledge_injection_empty` | 确认后有效条目为空，拒绝空注入调用 |
| 409 | `session_closed` | 会话已结束（core 语义） |
| 413 | `kb_import_too_large` | 单库合计 > `AW_KB_MAX_TOTAL_BYTES`（100MB） |
| 507 | `kb_write_failed` | 磁盘写入/rename 失败（已清理半成品） |
| 500 | `internal_error` | 未捕获异常（日志含 requestId，响应不含堆栈与正文） |

`kb_import_too_large` 优先于 `file_too_large` 判定：先逐文件校验单文件上限，再校验单次文件数与合计字节；同一请求只返回第一个命中的错误码，`details` 列出全部命中项。

## 端点列表

### 知识库管理

#### POST /api/v1/knowledge-bases

- **描述**：上传 `index.json` + 可选 `.md` / `.markdown`，校验解析后创建知识库（同名自动升版本）。部分条目跳过仍是 201。
- **认证**：Session（`require_session`）；CSRF Origin 校验。
- **关联 US**：US-012（AC-012-1 ~ AC-012-7）、US-015（生成时间）、AC-REQ-18 / AC-REQ-19 / AC-REQ-24。
- **请求**：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `projectId` | number | 是 | 归属项目；不存在 → 404 `project_not_found` |
| `name` | string | 否 | ≤200；缺省按 ADR-104 六级推导 |
| `files[]` | file | 是 | 1..50 个；必须含一个 `index.json` |

- **200/201 响应**：`201`

```json
{
  "kb": {
    "kbId": "6f1c9a0e5b7d4c2a8e3f1b0d9c7a6e54",
    "projectId": 12,
    "name": "支付域知识库",
    "version": 2,
    "current": true,
    "status": "ready",
    "generatedAt": "2026-09-28T00:00:00Z",
    "entryCount": 184,
    "fileCount": 6,
    "totalByteSize": 2481923,
    "supersededCount": 1,
    "latestKbId": "6f1c9a0e5b7d4c2a8e3f1b0d9c7a6e54",
    "createdAt": "2026-11-18T02:30:00Z"
  },
  "importReport": {
    "files": [{"name": "index.json", "size": 812345, "accepted": true}],
    "skippedEntries": [{"index": 17, "line": 214, "code": "ENT-bad id", "reason": "invalid_id"}],
    "unmatchedFiles": ["notes.md"],
    "duplicateBodies": [{"code": "ENT-012", "fileName": "b.md"}],
    "counts": {"files": 6, "bytes": 2481923, "entries": 184, "skipped": 1},
    "versionBumped": true,
    "previousVersion": 1,
    "meta": {"fingerprint": "…", "graphFingerprint": "…", "warnings": 0}
  }
}
```

- **错误响应**：400 `unsupported_file_type` / `too_many_files` / `file_too_large` / `index_json_missing` / `index_json_invalid` / `validation_error`；404 `project_not_found`；409 `kb_name_conflict`；413 `kb_import_too_large`；507 `kb_write_failed`。
- **前端调用示例**：

```ts
const fd = new FormData();
fd.append("projectId", String(projectId));
for (const f of files) fd.append("files", f);
const res = await api.post<KbImportResponse>("/knowledge-bases", fd);
```

#### GET /api/v1/knowledge-bases

- **描述**：知识库列表（全局或按项目）；默认只返回当前版本。行内含 `supersededCount` 供「另有 N 个旧版本（只读）」。
- **认证**：Session。
- **关联 US**：US-012（AC-012-1 / AC-012-6）、US-015、US-016。
- **请求参数**：`projectId`（number，可选）、`includeSuperseded`（boolean，默认 `false`）、`limit`（默认 50，1..200）、`cursor`。
- **200 响应**：`{"items": [KnowledgeBaseSummary], "nextCursor": null}`；`KnowledgeBaseSummary` 字段同上方 `kb` 对象（含 `project: {id, name}`）。
- **错误响应**：400 `validation_error`；404 `project_not_found`（指定了不存在的项目）。
- **前端调用**：`api.get("/knowledge-bases", { params: { projectId, includeSuperseded, limit, cursor } })`

#### GET /api/v1/knowledge-bases/{kbId}

- **描述**：详情 + 项目 + 全部版本 + 计数 + 导入报告 + `latestKbId`（删除确认所需数据一次取齐）。
- **认证**：Session。
- **关联 US**：US-012（AC-012-6）、US-013（AC-013-4）、US-016（AC-016-1）。
- **200 响应**：

```json
{
  "kb": {"kbId": "…", "name": "…", "version": 1, "current": false, "status": "superseded",
         "generatedAt": null, "entryCount": 180, "fileCount": 6, "createdAt": "…"},
  "project": {"id": 12, "name": "支付域"},
  "versions": [{"kbId": "…", "version": 2, "current": true, "status": "ready",
                "generatedAt": "2026-09-28T00:00:00Z", "entryCount": 184, "createdAt": "…"}],
  "importReport": {"skippedEntries": [], "unmatchedFiles": [], "duplicateBodies": [], "counts": {}},
  "latestKbId": "6f1c…",
  "supersededBy": {"kbId": "6f1c…", "version": 2}
}
```

- **错误响应**：404 `kb_not_found`。
- **前端调用**：`api.get(`/knowledge-bases/${kbId}`)`

#### GET /api/v1/knowledge-bases/{kbId}/versions

- **描述**：版本列表 + `latestKbId`；供版本选择器与「查看最新版」。
- **认证**：Session。
- **关联 US**：US-013（AC-013-4）、US-015。
- **200 响应**：`{"items": [{"kbId","version","current","status","createdAt","generatedAt","entryCount","fileCount"}], "latestKbId": "…", "nextCursor": null}`
- **错误响应**：404 `kb_not_found`。

#### DELETE /api/v1/knowledge-bases/{kbId}

- **描述**：删除**逻辑知识库**——`project_id + name_key` 命中的全部版本、条目（级联）与已存文件；历史会话、事件、制品与调用记录不改。高风险操作，前端必须二次确认。
- **认证**：Session + Origin。
- **关联 US**：US-016（AC-016-1 ~ AC-016-3）、AC-REQ-23。
- **200 响应**：`204 No Content`。
- **错误响应**：404 `kb_not_found`。文件清理失败只记日志并返回 204（ADR-117），不向用户暴露文件系统细节。
- **前端调用**：`api.delete(`/knowledge-bases/${kbId}`)`

### 条目浏览与检索

#### GET /api/v1/knowledge-entries

- **描述**：全局浏览/检索。支持按项目、知识库、类型筛选，以及编号前缀、完整编号、关键词（标题/摘要/正文）；返回类型分栏计数与总数。
- **认证**：Session。
- **关联 US**：US-013（AC-013-1 / AC-013-3）、US-015（AC-015-1 / AC-015-2）、AC-REQ-20。
- **请求参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `projectId` | number | — | 项目筛选 |
| `kbId` | string | — | 知识库（版本）筛选 |
| `type` | string | — | `term` / `entity` / `state` / `rule` / `process` / `api` / `domain_event` / `other` |
| `q` | string | — | 1..100；编号精确/前缀或关键词 |
| `includeSuperseded` | boolean | `false` | 是否含旧版本条目 |
| `limit` | number | 50 | 1..200 |
| `cursor` | string | — | 服务端游标 |

- **200 响应**：

```json
{
  "items": [{
    "entryId": "a1b2…", "code": "ENT-012", "title": "支付订单", "type": "entity",
    "kbId": "6f1c…", "kbName": "支付域知识库", "kbVersion": 2,
    "superseded": false, "bodyMissing": false,
    "freshness": {"at": "2026-09-01T00:00:00Z", "state": "stale"},
    "conflict": {"hasConflict": true}
  }],
  "countsByType": {"term": 12, "entity": 40, "state": 8, "rule": 31,
                   "process": 9, "api": 22, "domain_event": 4, "other": 3},
  "total": 184,
  "nextCursor": "eyJyYW5rIjoxLCJjb2RlIjoiRU5ULTAxMiJ9"
}
```

- **错误响应**：400 `validation_error`（`q` 超长、`type` 非法、`limit` 越界、cursor 损坏）；404 `project_not_found` / `kb_not_found`。
- **前端调用**：`api.get("/knowledge-entries", { params: { projectId, kbId, type, q, includeSuperseded, limit, cursor } })`

#### GET /api/v1/knowledge-bases/{kbId}/entries

- **同级描述**：库内快捷路径，同一实现；项目由 `kbId` 推导，`type` / `q` / `limit` / `cursor` 同 §知识库条目。
- **认证**：Session。
- **关联 US**：US-013（AC-013-1 / AC-013-3）。
- **200 响应**：同 `GET /knowledge-entries`（`countsByType` 在本库范围内统计）。
- **错误响应**：404 `kb_not_found`；400 `validation_error`。

#### GET /api/v1/knowledge-entries/{entryId}

- **描述**：条目详情：正文/摘要、字段、表、代码路径、一跳邻居、来源文件、新鲜度、冲突、版本信息。
- **认证**：Session。
- **关联 US**：US-013（AC-013-2 / AC-013-4 / AC-013-5）、US-015（AC-015-1 / AC-015-2 / AC-015-3）、AC-REQ-20 / AC-REQ-22。
- **200 响应**：

```json
{
  "entryId": "a1b2…", "code": "ENT-012", "title": "支付订单", "type": "entity",
  "kb": {"kbId": "6f1c…", "name": "支付域知识库", "version": 2, "generatedAt": "2026-09-28T00:00:00Z",
         "current": false, "superseded": true, "latestKbId": "9a0b…"},
  "summary": "…", "body": "…", "bodyMissing": false, "bodySourceFile": "payment-domain.md",
  "sourceDoc": "payment-domain.md", "anchor": "ent-payment-order",
  "fields": {"order_id": "string"}, "tables": ["payment_order"],
  "codePaths": ["src/pay/order.py"],
  "neighbors": [{"code": "ST-order-created", "title": "订单已创建",
                 "entryId": "c3d4…", "kbId": "6f1c…", "exists": true}],
  "freshness": {"at": "2026-09-01T00:00:00Z", "state": "stale"},
  "conflicts": [{"kbName": "支付域知识库", "version": 1, "generatedAt": "2026-08-01T00:00:00Z"}],
  "createdAt": "2026-11-18T02:30:00Z"
}
```

- 邻居按编号在**同项目当前版本**内解析；不存在时 `exists=false`、不带 `entryId`。
- **错误响应**：404 `entry_not_found`。
- **前端调用**：`api.get(`/knowledge-entries/${entryId}`)`

### 会话知识注入

#### GET /api/v1/sessions/{sessionId}/knowledge-injection/candidates

- **描述**：当前会话所属项目的**当前版本**条目 + 徽标，供注入选择器；已删除/被取代不出现。支持 `q` / `type` 与分页（单库可达 2 万条，必须分页）。
- **认证**：Session。
- **关联 US**：US-014（AC-014-1）、US-015（AC-015-3）。
- **请求参数**：`q`（1..100）、`type`、`limit`（默认 50，1..200）、`cursor`。
- **200 响应**：`{"projectId": 12, "items": [EntryListItem], "countsByType": {...}, "total": 184, "nextCursor": null}`；条目字段同 `GET /knowledge-entries`。
- **错误响应**：404 `session_not_found`。
- **前端调用**：`api.get(`/sessions/${sessionId}/knowledge-injection/candidates`, { params })`

#### POST /api/v1/sessions/{sessionId}/knowledge-injection/preview

- **描述**：只读预览：按同一组装实现计算分段字符数、失效项、新鲜度/冲突提示与 `overLimit`；**不落库、不调用模型**。超限返回 200 + `overLimit=true`（不是错误），供界面实时反馈。
- **认证**：Session + Origin。
- **关联 US**：US-014（AC-014-1 / AC-014-3）、US-015（AC-015-3 / AC-015-4）、AC-REQ-21 / AC-REQ-22。
- **请求**：

```json
{
  "refs": [{"kbId": "6f1c…", "code": "ENT-012"}],
  "userPrompt": "帮我分析这个订单状态机"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `refs[].kbId` | string | 是 | 版本由 `kbId` 决定（可选择旧版本） |
| `refs[].code` | string | 是 | 编号原文，服务端 `casefold` 匹配 |
| `userPrompt` | string | 是 | 用户提示原文；服务端计字，不信任前端 |

- **200 响应**：

```json
{
  "items": [{"kbId": "6f1c…", "kbName": "支付域知识库", "kbVersion": 2,
             "code": "ENT-012", "title": "支付订单", "chars": 812, "source": "body"}],
  "invalidItems": [{"kbId": "6f1c…", "code": "BR-003", "reason": "superseded"}],
  "promptChars": 14, "injectedChars": 812, "totalChars": 826, "limit": 200000,
  "overLimit": false,
  "warnings": [{"kind": "stale", "kbId": "6f1c…", "code": "ENT-012", "detail": "freshness_at=2026-09-01"}]
}
```

- `totalChars` 可为 0..N 的任意值；`overLimit = totalChars > limit`。响应**不包含**组装后的注入文本（避免正文经网络重复传输与日志泄露），只回条目的 `chars` 与标识。
- **错误响应**：400 `validation_error`；404 `session_not_found`。失效项与超限在本端点**不是错误**。
- **前端调用**：

```ts
api.post(`/sessions/${sessionId}/knowledge-injection/preview`, {
  refs: selected.map(({ kbId, code }) => ({ kbId, code })),
  userPrompt: prompt,
});
```

## 3. 跨 spec：core 的 `/ai/complete`（唯一调用入口）

> 端点归 core，本 spec 只实现其调用的进程内服务。以下为两侧对齐契约，core 的 `api-spec.md` 为准。

- **端点**：`POST /api/v1/sessions/{sessionId}/ai/complete`（core）。
- **请求体新增可选字段**：`knowledgeRefs: [{kbId, entryCodes: string[]}]`、`confirmInvalidCodes: [{kbId, code}]`；与既有 `{prompt, temperature?, maxTokens?}` 并列。`prompt` 长度 1..200,000。
- **core 的处理顺序**：校验会话/模型 → 展平 `knowledgeRefs` 为 `[KbEntryRef]` → 调用 `KnowledgeInjectionService.prepare_for_call(session_id, project_id, prompt, refs, confirm_invalid_codes)` → 得到 `text` + `snapshot` → 调用 `AiGateway.complete(..., prepared=text, injection=snapshot)`。
- **错误映射**（均不发起外部请求、不写 AiCallRecord）：409 `knowledge_invalid_entries`（`details.invalidItems`）、409 `knowledge_injection_empty`、400 `prompt_budget_exceeded`（`details` 分段字数）；未注册服务时 409 `knowledge_unavailable`（core）。
- **确认语义**（ADR-110）：失效集非空且 `confirmInvalidCodes` 与失效集**完全相等**（服务端按 `(kbId, code)` 确定性排序后比较）才继续；否则 409 并回传完整失效集。确认后有效集为空 → 409 `knowledge_injection_empty`。用户取消（前端不发请求）→ 不产生 AiCallRecord。
- **前端**：选择器状态是扁平 `{kbId, code}`；提交前用 `toKnowledgeRefs(refs)` 按 `kbId` 分组。收到 409 `knowledge_invalid_entries` 时打开 `KbInvalidEntryDialog`，确认后把 `details.invalidItems` 原样作为 `confirmInvalidCodes` 重试；取消则关闭对话框且不重试。

## 4. 端点总览

| # | 方法 | 路径 | 描述 | 认证 | 关联 US |
|---|------|------|------|------|---------|
| 1 | POST | `/api/v1/knowledge-bases` | 导入（multipart） | Session | US-012 |
| 2 | GET | `/api/v1/knowledge-bases` | 知识库列表 | Session | US-012 / 015 / 016 |
| 3 | GET | `/api/v1/knowledge-bases/{kbId}` | 知识库详情 | Session | US-012 / 013 / 016 |
| 4 | GET | `/api/v1/knowledge-bases/{kbId}/versions` | 版本列表 | Session | US-013 / 015 |
| 5 | DELETE | `/api/v1/knowledge-bases/{kbId}` | 删除逻辑库 | Session | US-016 |
| 6 | GET | `/api/v1/knowledge-entries` | 全局浏览/检索 | Session | US-013 / 015 |
| 7 | GET | `/api/v1/knowledge-bases/{kbId}/entries` | 库内条目（同一实现） | Session | US-013 |
| 8 | GET | `/api/v1/knowledge-entries/{entryId}` | 条目详情 | Session | US-013 / 015 |
| 9 | GET | `/api/v1/sessions/{sessionId}/knowledge-injection/candidates` | 注入候选 | Session | US-014 / 015 |
| 10 | POST | `/api/v1/sessions/{sessionId}/knowledge-injection/preview` | 注入预览（只读） | Session | US-014 / 015 |

> 跨域端点：本 spec 无跨域（多域）标记；与 core 的交互是进程内接口，不是 HTTP 跨域调用。
