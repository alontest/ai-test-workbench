# Tech Tasks — repo-integration

> 阶段：tech-tasks。来源：`requirements-analysis/docs/context.md`（7 US / 36 AC / 11 EARS）、`technical-design/change-spec.md`、`docs/api-spec.md`、`docs/database-schema.md`、`docs/component-tree.md`、`docs/file-structure.md`、`docs/architecture-decisions.md`（ADR-201 ~ ADR-217，architecture-locked）。
> 本体：无 `ontology-slices/tech-tasks.md`（项目无 `ontology-work/views/index.json`），任务不附 `ENT-` / `BR-` 编号；实体名沿用 ENT-C12 ~ ENT-C15。
> 编号：任务 `TASK-RI-201` 起；测试 `TC-201` 起（core 占 001~071，knowledge-base 占 101~150）。迁移固定 `0008_repo_integration`，`down_revision="0007"`。
> 本文件是后续实现岗的唯一任务来源；**所有任务状态均为 pending**，未开始实现。

## 任务分组

### 批次 A：基座与四表迁移 0008（TASK-RI-201 ~ TASK-RI-208）

目标：建立 `repos/` 纯逻辑层、四张表 ORM、迁移 `0008`、仓储层与启动配置；完成后可独立跑迁移与纯函数/仓储用例，不依赖任何 API。

- 依赖顺序：201 →（202/203/204 并行）→ 205 → 206 → 207；208 可与 205 并行。
- 出口条件：`alembic upgrade head` 在 SQLite 通过；`0008` 双方言迁移用例（TC-247）通过；纯函数与仓储用例全绿。
- 可并行：202 / 203 / 204；205 与 208。

### 批次 B：绑定与连通性测试（TASK-RI-211 ~ TASK-RI-217）

目标：跑通「创建绑定 → 保存前测试 → 保存 → 已保存测试 → 更新令牌 → 解绑」，含两个供应商适配器的仓库详情与统一错误映射。

- 依赖：批次 A 全部完成；211 → 212 →（213/214 并行）→ 215 → 216；217 依赖 211/216。
- 出口条件：数据库端点 1~6、9 与 TC-201 ~ TC-215、TC-242 ~ TC-244 全绿（SQLite）。

### 批次 C：同步与环境快照（TASK-RI-221 ~ TASK-RI-225）

目标：手动同步仓库详情 + 全部分支 + 最近 100 提交；claim 互斥、单事务覆盖、失败保留、记录分页。

- 依赖：批次 B 完成；221 → 222 → 223；224 可与 222 并行补 fixture；225 依赖 222。
- 出口条件：TC-216 ~ TC-223 全绿；并发、失败保留、限流、超预算用例可重复。

### 批次 D：浏览与按需读文件（TASK-RI-231 ~ TASK-RI-236）

目标：实时仓库/分支/提交/目录树、游标分页、`truncated`/`hasMore`、跨域 baseline、单文件读取与审计。

- 依赖：批次 C 完成；231 → 232 → 233；234 依赖 232/233；235/236 依赖 233/234。
- 出口条件：TC-224 ~ TC-241 与 TC-233 全绿；provider 只发 GET，无写操作。

### 批次 E：前端与验收（TASK-RI-241 ~ TASK-RI-246）

目标：项目上下文页增量面板、独立浏览路由、文件抽屉、失效/解绑只读态；端到端验收。

- 依赖：批次 D 完成；241 → 242/243 → 244 → 245 → 246。
- 出口条件：TC-250、TC-251 通过；1440×900 无横向滚动；控制台 0 错误；门禁 `uv run pytest -q` 与 `cd web && npm run test -- --run` 通过。

## 任务清单

- [ ] TASK-RI-201：实现 `repos/` 常量、DTO、错误族与脱敏基座 [no-test]
  - **描述**：建立纯逻辑包，集中常量、归一化 DTO、领域错误与日志脱敏工具，供适配器与服务层共用。
  - **涉及文件**：`src/workbench/repos/__init__.py`、`constants.py`、`types.py`、`errors.py`、`redaction.py`
  - **具体操作**：写入 ADR-216 的 10 个常量与 `REPO_SYNC_MAX_PAGES=200`；定义 `RepoProvider` 协议、`Page[T]`、`TreePage`、`FileContent`、`ProviderError`；`RepoDomainError` 只带 code/status/details；`safe_log_fields()` 白名单只允许 bindingId/provider/repoKey/statusCode/category。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：无
  - **对应 AC**：AC-REQ-25、AC-REQ-34
  - **TC**：无（被后续任务间接覆盖）
  - **估算**：4h [样板]，不确定性低
  - **状态**：pending
  - 免测理由：纯声明与类型定义，无运行时分支；由 202~207 的用例编译与导入覆盖。

- [ ] TASK-RI-202：实现仓库标识、路径、ref、域名与检索词校验 + SSRF 防护
  - **描述**：所有外部输入在发请求前校验；域名只允许公网 https origin。
  - **涉及文件**：`src/workbench/repos/validation.py`、`src/workbench/repos/ssrf.py`、`tests/test_repo_validation.py`
  - **具体操作**：`parse_repo_identifier()` 支持 GitHub `owner/repo`、云效 `group/repo` 与数字 ID；`validate_repo_path()` 拒绝 `..`、绝对路径、`\0`、控制字符、段长>255、总长>1024；`validate_ref()` 白名单 `[A-Za-z0-9._/-]` 并拒绝 `..`、`@{`、空白、`~^:?*[`；`validate_api_base_url()` 仅 https、origin、443；`assert_public_https_origin()` 解析 A/AAAA 并拒绝私网/回环/链路本地/保留地址；GitHub 固定域名。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-201
  - **对应 AC**：AC-017-2、AC-022-5、AC-REQ-25、AC-REQ-31
  - **TC**：TC-202、TC-206、TC-239、TC-252
  - **估算**：8h [逻辑]，不确定性中（DNS 解析与保留地址表需逐项覆盖）
  - **状态**：pending

- [ ] TASK-RI-203：实现仓库令牌加密、解密与掩码
  - **描述**：复用 core 的 AES-256-GCM 与密文格式，但使用独立密钥 `AW_REPO_TOKEN_KEY`。
  - **涉及文件**：`src/workbench/repos/crypto.py`、`tests/test_repo_crypto.py`
  - **具体操作**：`encrypt_token()` 调 `workbench.core.crypto.encrypt(..., key=repo_key)`；`decrypt_token()` 拒绝 revoked/空密文，失败抛 `CredentialUnavailable`；`mask_token()` 输出 `<prefix>****<last4>`、短令牌 `****`；禁止回落到 `AW_ENCRYPTION_KEY`；异常文本不含密文。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-RI-201（测试用注入密钥；`AW_REPO_TOKEN_KEY` 读取由 TASK-RI-208 接线，两者可并行）
  - **对应 AC**：AC-017-1、AC-017-4、AC-REQ-25
  - **TC**：TC-201、TC-204、TC-246
  - **估算**：4h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-204：实现不透明分页游标
  - **描述**：base64url(JSON) + HMAC-SHA256(16B)，绑定查询指纹，防篡改与跨查询复用。
  - **涉及文件**：`src/workbench/repos/cursor.py`、`tests/test_repo_cursor.py`
  - **具体操作**：编码 `{v,b,p,r,ref,path,qfp,page}`；签名密钥由 `AW_REPO_TOKEN_KEY` 派生（`sha256(b"cursor:"+key)`）；解码校验版本、签名、`bindingId`/`repoKey`/`ref`/`path`/检索词指纹；失败 → `400 invalid_cursor`；不泄露游标内容。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-RI-201
  - **对应 AC**：AC-020-1、AC-020-2、AC-021-1
  - **TC**：TC-232
  - **估算**：4h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-205：实现四张表 ORM 与模型注册
  - **描述**：按 `docs/database-schema.md` 建四个模型，列、CHECK、索引、可空唯一与表参数与文档一致。
  - **涉及文件**：`src/workbench/db/models/repo_binding.py`、`repo_sync_record.py`、`repo_metadata_snapshot.py`、`repo_file_read_record.py`、`src/workbench/db/models/__init__.py`
  - **具体操作**：使用 `pk_type()` / `utcnow()` / `MYSQL_TABLE_ARGS`；`token_ciphertext` 不进任何 DTO；JSON 列只用 `sa.JSON`；唯一键含 `active_flag`；枚举列加 `CheckConstraint`；子表 FK `ON DELETE CASCADE`。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-201
  - **对应 AC**：AC-017-3、AC-019-1、AC-022-4、AC-023-4 / AC-023-6
  - **TC**：TC-247（由迁移用例覆盖）
  - **估算**：6h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-206：创建迁移 `0008_repo_integration` 与双方言迁移用例
  - **描述**：按 0005/0006 的写法创建四张表，`revision="0008"`、`down_revision="0007"`。
  - **涉及文件**：`migrations/versions/0008_repo_integration.py`、`tests/test_repo_migrations.py`
  - **具体操作**：`upgrade()` 先父表后子表；`downgrade()` 反序；不引入方言专属 DDL；SQLite 与 MySQL 各跑 `upgrade head → downgrade 0007 → upgrade head`；断言四表、索引、CHECK、CASCADE 存在；合并前核对 `alembic heads` 只有 `0008`。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-205
  - **对应 AC**：AC-019-1、AC-022-4、AC-023-5
  - **TC**：TC-247
  - **估算**：8h [逻辑]，不确定性中（MySQL 容器与 CHECK 行为）
  - **状态**：pending

- [ ] TASK-RI-207：实现 `RepoRepository`（绑定、claim、快照覆盖、记录、baseline）
  - **描述**：把四张表的读写集中到仓储层，服务层不写 SQL。
  - **涉及文件**：`src/workbench/db/repositories/repos.py`、`tests/test_repo_sync_service.py`（仓储部分）
  - **具体操作**：绑定 CRUD 与唯一性查询；原子 claim `UPDATE … WHERE status!='revoked' AND (sync_started_at IS NULL OR < now-TTL)` 返回 rowcount；快照 `replace_snapshot(binding_id, repo, branches, commits)` 单事务删旧插新；同步记录分页；读取审计写入；baseline 取最新快照；解绑清密文/置 `active_flag=NULL`。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-205、TASK-RI-206
  - **对应 AC**：AC-017-3、AC-019-2、AC-019-3、AC-019-6、AC-022-4、AC-023-4
  - **TC**：TC-217、TC-218、TC-219、TC-233（部分）
  - **估算**：12h [逻辑]，不确定性中（SQLite 与 MySQL 的 rowcount/事务语义）
  - **状态**：pending

- [ ] TASK-RI-208：接入 `AW_REPO_TOKEN_KEY` 与启动自检、提升 httpx 运行时依赖
  - **描述**：新增独立密钥配置与校验；把 httpx 从 dev 组提升到运行时依赖（版本不变）。
  - **涉及文件**：`src/workbench/config.py`、`src/workbench/startup.py`、`pyproject.toml`、`tests/test_repo_config.py`
  - **具体操作**：`Settings.repo_token_key`（`SecretStr | None`）；缺失、非 base64、长度≠32 → `SettingsError`；`repo_token_key_bytes` 只读属性；启动自检追加 schema head 含 `0008`；`pyproject.toml` 的 `dependencies` 追加 `httpx>=0.28,<0.29`（dev 组保留）；不新增其它环境变量。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-RI-201
  - **对应 AC**：AC-REQ-25
  - **TC**：TC-248
  - **估算**：4h [样板]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-211：实现绑定服务与 API schema（创建/列表/详情/更新令牌）
  - **描述**：绑定生命周期编排、唯一性、加密、掩码与 DTO 序列化。
  - **涉及文件**：`src/workbench/services/repos/binding_service.py`、`serializers.py`、`api/schemas/repo.py`、`tests/test_repo_binding_api.py`
  - **具体操作**：`create()` 校验 → `repo_key=casefold(provider:repo_name)` → 唯一性 → 加密/掩码 → 写 `unverified`；`list()` 按 createdAt DESC + limit/cursor；`update_token()` 只改三列；`serialize_binding()` 排除密文；时间 RFC 3339；`projectId` number、`bindingId` string。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-201 ~ 204、TASK-RI-207
  - **对应 AC**：AC-017-1 ~ AC-017-4、AC-017-6
  - **TC**：TC-201 ~ TC-205、TC-207
  - **估算**：12h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-212：实现 `BaseProvider`、统一错误映射与响应体上限
  - **描述**：所有供应商共用 `httpx.AsyncClient`、状态码/响应头优先、错误分类、5 MiB JSON 上限与 1 MiB 文件上限。
  - **涉及文件**：`src/workbench/repos/providers/base.py`、`src/workbench/repos/providers/__init__.py`、`tests/test_repo_provider_github.py`（映射表）
  - **具体操作**：`follow_redirects=False`、`max_retries=0`；`_classify(status, headers, body)` 按 ADR-206 顺序判定；`retryAfterAt` 取 `retry-after` / `x-ratelimit-reset`；`_bounded_json()` 读至 5 MiB+1；`_bounded_stream()` 读至 1 MiB+1；异常只抛 `ProviderError`；`build_provider(binding)` 注册表。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-201、TASK-RI-202
  - **对应 AC**：AC-018-1 ~ AC-018-4、AC-019-5、AC-REQ-26、AC-REQ-28
  - **TC**：TC-213、TC-234
  - **估算**：10h [逻辑]，不确定性中（限流信号与 403 判定）
  - **状态**：pending

- [ ] TASK-RI-213：实现 GitHub 适配器（六方法）
  - **描述**：GitHub REST 只读端点、分页、限流头、过期头与 contents 目录/文件。
  - **涉及文件**：`src/workbench/repos/providers/github.py`、`tests/test_repo_provider_github.py`
  - **具体操作**：`/user/repos`（search）、`/repos/{owner}/{repo}`、`/branches`、`/commits`（since/until/page/per_page）、`/contents/{path}`（目录列表，1,000 条上限置 `truncated`）、文件内容（`size` 先判 1 MiB，base64 解码，`encoding=none` 视为超限）；解析 `Link rel="next"`、`x-ratelimit-*`、`retry-after`、`GitHub-Authentication-Token-Expiration`；Authorization 只放请求头。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-212
  - **对应 AC**：AC-018-1、AC-020-1、AC-021-1 ~ AC-021-3、AC-022-1 ~ AC-022-3、AC-023-3
  - **TC**：TC-208 ~ TC-215、TC-224、TC-229 ~ TC-231
  - **估算**：12h [逻辑]，不确定性中（fixture 覆盖）
  - **状态**：pending

- [ ] TASK-RI-214：实现云效 Codeup 适配器（六方法）
  - **描述**：中心站/地域站路径、`x-*` 分页、`files/tree` 与 `files/blobs`、429 无头处理。
  - **涉及文件**：`src/workbench/repos/providers/yunxiao.py`、`tests/test_repo_provider_yunxiao.py`
  - **具体操作**：`/organizations/{orgId}/repositories`（page/perPage/search）、`/repositories/{repoId}`、`/branches`、`/commits`（refName 必填）、`/files/tree`（type=DIRECT，无分页）、`/files/blobs`（ref + filePath 编码，`content` 默认 base64，`size` 先判）；`x-yunxiao-token` 只放请求头；分页终止用 `x-next-page` / `x-total-pages`；429 → rate_limited、`retryAfterAt=null`。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-212
  - **对应 AC**：AC-018-1、AC-020-1、AC-021-1 ~ AC-021-3、AC-022-1 ~ AC-022-3、AC-023-3
  - **TC**：TC-208 ~ TC-215、TC-224、TC-229 ~ TC-231
  - **估算**：12h [逻辑]，不确定性中（中心站/地域站路径与编码）
  - **状态**：pending

- [ ] TASK-RI-215：实现连通性服务（保存前/后、四类结果、10s）
  - **描述**：一次只读 `get_repository`，按四类结果落库（仅已保存）。
  - **涉及文件**：`src/workbench/services/repos/connectivity_service.py`、`tests/test_repo_connectivity_api.py`
  - **具体操作**：已保存：解密 → provider → 成功置 `connected` + `lastVerified*`；auth/permission/not_found 置 `token_invalid`；其他不改状态；未保存：直接使用表单值，零落库零日志正文；总预算 10s；结果固定枚举 + `retryAfterAt`；测试不写会话/制品/AiCallRecord。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-211、TASK-RI-212、TASK-RI-213、TASK-RI-214
  - **对应 AC**：AC-018-1 ~ AC-018-5、AC-023-1、AC-023-3
  - **TC**：TC-208 ~ TC-212、TC-214、TC-215
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-216：实现绑定 API 端点 1~6 与路由接线
  - **描述**：暴露列表/创建/详情/更新令牌/已保存测试/未保存测试，统一错误映射。
  - **涉及文件**：`src/workbench/api/v1/repo_bindings.py`、`src/workbench/api/v1/router.py`、`tests/test_repo_binding_api.py`、`tests/test_repo_api_contract.py`
  - **具体操作**：`/projects/{projectId}/repo-bindings` GET/POST；`/repo-bindings/{id}` GET；`/repo-bindings/{id}/token` PATCH；`/repo-bindings/{id}/test-connection` POST；`/repo-bindings/test-connection` POST；全部挂 `require_session`（全局）与 `require_same_origin`；`limit` 默认 30/1–100；错误码按 api-spec；`ProviderError` 只映射固定码。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-211、TASK-RI-215
  - **对应 AC**：AC-017-1 ~ AC-017-4、AC-018-1 ~ AC-018-5、AC-017-6
  - **TC**：TC-201 ~ TC-215（API 级）
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-217：实现解绑生命周期、状态守卫与端点 9
  - **描述**：解绑清密文、置 revoked、active_flag=NULL；所有外呼入口统一拦截。
  - **涉及文件**：`src/workbench/services/repos/binding_service.py`、`src/workbench/repos/errors.py`、`src/workbench/api/v1/repo_bindings.py`、`tests/test_repo_lifecycle_api.py`
  - **具体操作**：`unbind()` 幂等；`decrypt_token()` 拒绝 revoked；服务入口 `assert_active()` 返回 409 `binding_revoked`；baseline 例外；解绑后 provider 调用次数 0；重新绑定生成新行。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-211、TASK-RI-216、TASK-RI-207
  - **对应 AC**：AC-023-1、AC-023-4 ~ AC-023-6、AC-REQ-33
  - **TC**：TC-227、TC-242 ~ TC-244
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-221：补齐两个适配器的分支/提交分页
  - **描述**：分支全量翻页、提交单页 100 条，供应商分页翻译与终止条件。
  - **涉及文件**：`src/workbench/repos/providers/github.py`、`yunxiao.py`、`tests/test_repo_provider_*.py`
  - **具体操作**：GitHub `per_page=100` + Link；云效 `perPage` ≤100 + `x-next-page`；提交按时间倒序；`REPO_SYNC_MAX_PAGES` 护栏；空分支/空提交返回空数组；不把供应商 `total` 当页数。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-213、TASK-RI-214
  - **对应 AC**：AC-019-1、AC-019-6、AC-020-2、AC-021-1
  - **TC**：TC-216、TC-220、TC-221、TC-225、TC-229
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-222：实现同步服务（claim、拉取、单事务覆盖、失败保留）
  - **描述**：手动同步基线，数据库原子 claim 互斥，失败保留旧快照。
  - **涉及文件**：`src/workbench/services/repos/sync_service.py`、`tests/test_repo_sync_service.py`
  - **具体操作**：claim → `running` 记录 → 仓库详情 → 全部分支 → 最近 100 提交 → 单事务替换快照 + 更新绑定摘要 + 记录 success → 释放 claim；异常记录 failed 并保留旧快照；reclaim 遗留 running → `failed(interrupted)`；总预算 120s；进程内 per-binding `asyncio.Lock` 快速失败。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-221、TASK-RI-207
  - **对应 AC**：AC-019-1 ~ AC-019-6、AC-REQ-27、AC-REQ-28
  - **TC**：TC-216 ~ TC-223
  - **估算**：16h [逻辑]，不确定性中（事务与并发）
  - **状态**：pending

- [ ] TASK-RI-223：实现同步 API 端点 7~8 与记录序列化
  - **描述**：`POST /sync` 与 `GET /sync-records`；失败也是 200 + failed 记录。
  - **涉及文件**：`src/workbench/api/v1/repo_bindings.py`、`src/workbench/services/repos/serializers.py`、`tests/test_repo_sync_api.py`
  - **具体操作**：`/repo-bindings/{id}/sync` POST → `{record, binding}`；409 `sync_in_progress` / `binding_revoked`；`/sync-records` limit 20/1–100 + cursor 按 startedAt DESC；`errorCategory` 固定枚举；`retryAfterAt` RFC 3339。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-222
  - **对应 AC**：AC-019-2 ~ AC-019-5
  - **TC**：TC-216、TC-219、TC-220、TC-222
  - **估算**：8h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-224：补齐同步失败/限流/并发/超预算 fixture 与用例
  - **描述**：用 `MockTransport` 构造分支分页中途失败、429、遗留 claim、预算超时。
  - **涉及文件**：`tests/test_repo_sync_service.py`、`tests/fixtures/repo/*.json`、`tests/test_repo_provider_github.py`
  - **具体操作**：录制 401/403+限流头/403/404/429/5xx/超时/非法 JSON/满页；断言旧快照与 `lastSyncSuccessAt` 不变；断言 0 自动重试；断言 running 归并 interrupted。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-222、TASK-RI-223
  - **对应 AC**：AC-019-2、AC-019-3、AC-019-5、AC-REQ-28
  - **TC**：TC-213、TC-217 ~ TC-220、TC-223
  - **估算**：8h [逻辑]，不确定性中（fixture 覆盖）
  - **状态**：pending

- [ ] TASK-RI-225：实现快照 payload 归一化与 baseline 读取
  - **描述**：把供应商字段归一化为 `payload`，baseline 只读快照、不发外呼。
  - **涉及文件**：`src/workbench/services/repos/sync_service.py`、`browse_service.py`、`serializers.py`、`tests/test_repo_sync_api.py`
  - **具体操作**：repo/branch/commit 三类 payload 固定字段；不写 `kind=tree`；baseline 取每类最新 `fetched_at`；返回 `metadataSynced`、`lastSyncSuccessAt`、`repo/branches/commits`；解绑后仍可读。
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-RI-222
  - **对应 AC**：AC-019-4、AC-019-6、AC-020-4、AC-023-5
  - **TC**：TC-221、TC-233、TC-243
  - **估算**：6h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-231：补齐适配器的仓库列表、目录树与文件读取
  - **描述**：实时浏览与按需读文件的三个方法在 GitHub / 云效两侧落地。
  - **涉及文件**：`src/workbench/repos/providers/github.py`、`yunxiao.py`、`tests/test_repo_provider_*.py`
  - **具体操作**：GitHub `/user/repos`、`/contents` 目录列表（1,000 条截断）、`/contents/{path}` 文件；云效 `repositories`、`files/tree`（DIRECT）、`files/blobs`（filePath 编码、size 先判）；文件内容流式读取到 1 MiB+1；`encoding` 归一化为 `text|base64`；二进制/NUL/非 UTF-8 交服务层判定。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-221
  - **对应 AC**：AC-020-1、AC-021-2 ~ AC-021-4、AC-022-1 ~ AC-022-3
  - **TC**：TC-224、TC-230、TC-231、TC-235 ~ TC-238
  - **估算**：14h [逻辑]，不确定性中（云效无分页与文件端点形态）
  - **状态**：pending

- [ ] TASK-RI-232：实现浏览服务（仓库/分支/提交/目录树 + 游标）
  - **描述**：实时请求、游标翻译、`truncated`/`hasMore`、未同步空态、token_invalid 502。
  - **涉及文件**：`src/workbench/services/repos/browse_service.py`、`tests/test_repo_browse_api.py`
  - **具体操作**：校验 binding/revoked/同步基线；仓库/分支/提交/树分别映射；`limit` 默认 30（树 100）；游标指纹；GitHub 900 条/1,000 条上限置 truncated；云效无分页；401/403/404 置 token_invalid 并抛 502；429/网络/5xx 不改状态。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-231、TASK-RI-204、TASK-RI-207
  - **对应 AC**：AC-020-1 ~ AC-020-4、AC-021-1 ~ AC-021-3、AC-REQ-29、AC-REQ-30
  - **TC**：TC-224 ~ TC-234
  - **估算**：14h [逻辑]，不确定性中（分页与错误映射）
  - **状态**：pending

- [ ] TASK-RI-233：实现文件服务（前置校验、大小/编码、审计）
  - **描述**：校验在请求前；读取后按大小与编码判定；成功/拒绝写审计。
  - **涉及文件**：`src/workbench/services/repos/file_service.py`、`tests/test_repo_file_api.py`
  - **具体操作**：`validate_repo_path/ref` → 未解绑 → provider → `size>1,048,576` 拒绝（不截断）；base64/NUL → 415；UTF-8 解码失败 → 422；成功写 `success`；拒绝写 `refused`；非法路径不写记录；正文不入库/日志。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-231、TASK-RI-207
  - **对应 AC**：AC-022-1 ~ AC-022-5、AC-REQ-31、AC-REQ-34
  - **TC**：TC-235 ~ TC-241
  - **估算**：12h [逻辑]，不确定性中（编码边界）
  - **状态**：pending

- [ ] TASK-RI-234：实现浏览/文件/baseline 端点 10~15
  - **描述**：暴露实时浏览、单文件与跨域 baseline，统一错误码与分页。
  - **涉及文件**：`src/workbench/api/v1/repo_browse.py`、`src/workbench/api/v1/router.py`、`tests/test_repo_browse_api.py`、`tests/test_repo_api_contract.py`
  - **具体操作**：`/repositories|/branches|/commits|/tree|/file|/baseline`；`search`/`limit`/`cursor` 校验；`repoId` 可选；`ref` 必填（树/提交/文件）；`path` 默认空串；错误码按 api-spec；baseline 不触发外呼；15 个端点全部 session 保护。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-232、TASK-RI-233、TASK-RI-225
  - **对应 AC**：AC-020-1 ~ AC-020-4、AC-021-1 ~ AC-021-4、AC-022-1 ~ AC-022-5
  - **TC**：TC-224 ~ TC-241、TC-245
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-235：补齐浏览/文件安全用例与令牌/正文哨兵断言
  - **描述**：跨流程扫描响应、错误体、日志与记录表；Path traversal 与 SSRF 用例。
  - **涉及文件**：`tests/test_repo_security_logs.py`、`tests/test_repo_file_api.py`、`tests/test_repo_validation.py`
  - **具体操作**：令牌哨兵贯穿创建/测试/同步/读文件/失败；正文哨兵贯穿读文件成功/超限/二进制/非 UTF-8；断言完整令牌与正文出现 0 次；路径穿越在请求前拒绝且无记录；私网域名/重定向拒绝。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-232、TASK-RI-233
  - **对应 AC**：AC-022-5、AC-REQ-25、AC-REQ-34
  - **TC**：TC-239、TC-241、TC-246、TC-252
  - **估算**：6h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-236：实现跨域 baseline 契约与解绑只读态
  - **描述**：baseline 只按 bindingId 读取，解绑/令牌失效仍可读；跨域调用方只允许 baseline 与 file。
  - **涉及文件**：`src/workbench/services/repos/browse_service.py`、`src/workbench/api/v1/repo_browse.py`、`tests/test_repo_lifecycle_api.py`
  - **具体操作**：baseline 返回 `revoked`、`status`、`lastSyncSuccessAt`、快照；解绑后 200 只读；浏览页目录树/文件入口置灰（前端）；不暴露密文/令牌。
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **依赖**：TASK-RI-225、TASK-RI-234
  - **对应 AC**：AC-023-4、AC-023-5、AC-REQ-33
  - **TC**：TC-233、TC-242、TC-243
  - **估算**：4h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-241：实现前端 API 类型、客户端与 hooks 基座
  - **描述**：与 api-spec 对齐的 TS 类型、15 个端点封装、TanStack Query hooks 与 key 工厂。
  - **涉及文件**：`web/src/features/repos/api/*.ts`、`web/src/features/repos/hooks/*.ts`、`web/src/features/repos/index.ts`
  - **具体操作**：复用 `lib/api/client.ts`；`projectId: number`、`bindingId: string`；`queryString` 处理分页；hooks 返回三态；文件查询 `staleTime=0`；不在 localStorage 持久化令牌/内容；错误类型复用 `ApiError`。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-234
  - **对应 AC**：AC-017-1、AC-019-4、AC-020-1
  - **TC**：TC-250（基础设施）
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-242：实现项目页仓库绑定面板与表单
  - **描述**：`RepoBindingPanel`、列表/行/徽标、新增表单、权限说明、令牌字段、聚合失效横幅、过期提示。
  - **涉及文件**：`web/src/features/repos/components/RepoBindingPanel.tsx`、`RepoBindingList.tsx`、`RepoBindingRow.tsx`、`RepoStatusBadge.tsx`、`RepoBindingForm.tsx`、`ProviderSegmented.tsx`、`TokenField.tsx`、`RepoPermissionHint.tsx`、`TokenExpiryHint.tsx`、`TokenInvalidBanner.tsx`、`*.module.css`
  - **具体操作**：区块在项目详情表单下方；四态徽标；令牌只显示掩码；表单保存前测试且字段变更置 `stale`；复用 core `ConnectionTestBadge` 并扩展 `permission-denied` / `stale`；解绑行置灰；页面唯一失效横幅。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-241
  - **对应 AC**：AC-017-1 ~ AC-017-6、AC-018-1 ~ AC-018-5、AC-023-1、AC-023-3
  - **TC**：TC-250
  - **估算**：14h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-243：实现同步控件、同步记录、更新令牌与解绑对话框
  - **描述**：同步按钮/上次同步/基线、折叠记录表、更新令牌表单、五后果解绑确认。
  - **涉及文件**：`web/src/features/repos/components/SyncControl.tsx`、`SyncRecordTable.tsx`、`UpdateTokenForm.tsx`、`RevokedBindingRow.tsx`、`UnbindDialog.tsx`、`*.module.css`
  - **具体操作**：同步中禁用；首次「从未同步」；失败横幅带「上次成功时间」；限流显示 `retryAfterAt`；更新令牌只替换令牌与掩码；解绑模态列出五条后果并焦点回退。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-242
  - **对应 AC**：AC-017-4、AC-019-2 ~ AC-019-5、AC-023-2 ~ AC-023-4
  - **TC**：TC-250
  - **估算**：10h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-244：实现仓库浏览页、选择器、目录树、提交与文件抽屉
  - **描述**：独立路由页、实时选择器、逐级目录树、提交分页、480px 文件抽屉、失效/解绑只读态。
  - **涉及文件**：`web/src/features/repos/pages/RepoBrowsePage.tsx`、`components/RepoBrowseHeader.tsx`、`RepoBreadcrumb.tsx`、`RepoBaselineStrip.tsx`、`RepoPicker.tsx`、`BranchPicker.tsx`、`RepoTree.tsx`、`TreeNode.tsx`、`TreeTruncatedNote.tsx`、`CommitList.tsx`、`CommitRow.tsx`、`FileViewerDrawer.tsx`、`RepoEmptyUnsynced.tsx`、`RevokedNotice.tsx`、`*.module.css`
  - **具体操作**：默认绑定仓库/默认分支；切换分支重载提交与树；`hasMore` 追加加载；`truncated` 固定提示；文件抽屉 Esc/遮罩关闭并还焦；超限/二进制/非 UTF-8/非法路径错误态；已解绑选择器、树行、文件入口 `aria-disabled` 且不发请求。
  - **优先级**：P0
  - **复杂度**：L（3–5d）
  - **依赖**：TASK-RI-242、TASK-RI-243
  - **对应 AC**：AC-020-1 ~ AC-020-4、AC-021-1 ~ AC-021-4、AC-022-1 ~ AC-022-5、AC-023-4
  - **TC**：TC-250、TC-251
  - **估算**：16h [逻辑]，不确定性低
  - **状态**：pending

- [ ] TASK-RI-245：接线路由、侧边栏、项目页挂载与设计 token [no-test]
  - **描述**：把浏览页与面板接入 core 的 router / AppShell / ProjectsPage，并追加 3 个 token。
  - **涉及文件**：`web/src/router.tsx`、`web/src/app/AppShell.tsx`、`web/src/features/projects/ProjectsPage.tsx`、`web/src/features/projects/ProjectForm.tsx`、`web/src/styles/tokens.css`
  - **具体操作**：追加 `/projects/:projectId/repos/:bindingId`；「基座管理」加「仓库浏览」；项目页详情表单下方渲染 `<RepoBindingPanel data-mount="repo-binding-panel">`；「仓库地址」hint 改自由备注；tokens 追加 `--color-overlay` / `--spacing-5` / `--repo-drawer-width`。
  - **优先级**：P0
  - **复杂度**：XS（<4h）
  - **依赖**：TASK-RI-242、TASK-RI-244
  - **对应 AC**：AC-017-5、AC-020-1
  - **TC**：无（由 TC-250 / TC-251 覆盖挂载）
  - **估算**：4h [样板]，不确定性低
  - **状态**：pending
  - 免测理由：路由与挂载接线，无独立业务分支；由 TC-250 组件测试与 TC-251 E2E 覆盖。

- [ ] TASK-RI-246：前端组件测试、Playwright 闭环与验收证据
  - **描述**：补 TC-250 组件测试与 TC-251 全链路；采集截图与控制台证据。
  - **涉及文件**：`web/src/features/repos/*.test.tsx`、`web/e2e/repo.spec.ts`、`specs/repo-integration_20261117205011/technical-design/docs/test-strategy.md`（证据回填）
  - **具体操作**：Vitest 覆盖四态徽标、四类测试结果、`stale`、掩码、截断提示、抽屉错误态、解绑置灰；Playwright 覆盖绑定 → 测试 → 同步 → 浏览 → 读文件 → 解绑；1440×900 无横向滚动、控制台 0 错误；不连真实供应商。
  - **优先级**：P0
  - **复杂度**：M（1–2d）
  - **依赖**：TASK-RI-245
  - **对应 AC**：US-017 ~ US-023（全量）
  - **TC**：TC-250、TC-251
  - **估算**：12h [逻辑]，不确定性中（E2E 稳定性）
  - **状态**：pending

## AC → TC → 测试落点

| AC | TC | 测试落点 |
|----|----|---------|
| AC-017-1 | TC-201, TC-246 | `tests/test_repo_binding_api.py`、`tests/test_repo_security_logs.py` |
| AC-017-2 | TC-202, TC-206 | `tests/test_repo_binding_api.py`、`tests/test_repo_validation.py` |
| AC-017-3 | TC-203 | `tests/test_repo_binding_api.py` |
| AC-017-4 | TC-204 | `tests/test_repo_binding_api.py` |
| AC-017-5 | TC-250 | `web/src/features/repos/RepoBindingPanel.test.tsx` |
| AC-017-6 | TC-205 | `tests/test_repo_binding_api.py` |
| AC-018-1 | TC-208, TC-212, TC-215 | `tests/test_repo_connectivity_api.py` |
| AC-018-2 | TC-209 | `tests/test_repo_connectivity_api.py` |
| AC-018-3 | TC-210 | `tests/test_repo_connectivity_api.py` |
| AC-018-4 | TC-211 | `tests/test_repo_connectivity_api.py` |
| AC-018-5 | TC-208, TC-250 | `tests/test_repo_connectivity_api.py`、`RepoBindingPanel.test.tsx` |
| AC-019-1 | TC-216 | `tests/test_repo_sync_api.py` |
| AC-019-2 | TC-217 | `tests/test_repo_sync_service.py` |
| AC-019-3 | TC-219 | `tests/test_repo_sync_api.py` |
| AC-019-4 | TC-216, TC-222 | `tests/test_repo_sync_api.py` |
| AC-019-5 | TC-220 | `tests/test_repo_sync_api.py` |
| AC-019-6 | TC-216, TC-221 | `tests/test_repo_sync_api.py` |
| AC-020-1 | TC-224 | `tests/test_repo_browse_api.py` |
| AC-020-2 | TC-225 | `tests/test_repo_browse_api.py` |
| AC-020-3 | TC-226 | `tests/test_repo_browse_api.py` |
| AC-020-4 | TC-228, TC-233 | `tests/test_repo_browse_api.py` |
| AC-021-1 | TC-229 | `tests/test_repo_browse_api.py` |
| AC-021-2 | TC-230 | `tests/test_repo_browse_api.py` |
| AC-021-3 | TC-231 | `tests/test_repo_browse_api.py`、`RepoTree.test.tsx` |
| AC-021-4 | TC-229, TC-230 | `tests/test_repo_browse_api.py` |
| AC-022-1 | TC-235 | `tests/test_repo_file_api.py` |
| AC-022-2 | TC-236 | `tests/test_repo_file_api.py` |
| AC-022-3 | TC-237, TC-238 | `tests/test_repo_file_api.py` |
| AC-022-4 | TC-235 | `tests/test_repo_file_api.py` |
| AC-022-5 | TC-239 | `tests/test_repo_validation.py`、`tests/test_repo_file_api.py` |
| AC-023-1 | TC-209, TC-227, TC-228 | `tests/test_repo_connectivity_api.py`、`tests/test_repo_browse_api.py` |
| AC-023-2 | TC-204 | `tests/test_repo_binding_api.py` |
| AC-023-3 | TC-214 | `tests/test_repo_provider_github.py` |
| AC-023-4 | TC-227, TC-242 | `tests/test_repo_lifecycle_api.py` |
| AC-023-5 | TC-233, TC-243 | `tests/test_repo_lifecycle_api.py` |
| AC-023-6 | TC-244 | `tests/test_repo_lifecycle_api.py` |
| AC-REQ-25 | TC-201, TC-202, TC-203, TC-204, TC-205, TC-207, TC-246 | `tests/test_repo_binding_api.py`、`tests/test_repo_security_logs.py` |
| AC-REQ-26 | TC-208, TC-210, TC-211, TC-213 | `tests/test_repo_connectivity_api.py`、`tests/test_repo_provider_github.py` |
| AC-REQ-27 | TC-216, TC-217, TC-219, TC-220, TC-223 | `tests/test_repo_sync_service.py`、`tests/test_repo_sync_api.py` |
| AC-REQ-28 | TC-213, TC-220 | `tests/test_repo_provider_github.py`、`tests/test_repo_sync_api.py` |
| AC-REQ-29 | TC-224, TC-225, TC-226, TC-228 | `tests/test_repo_browse_api.py` |
| AC-REQ-30 | TC-229, TC-230, TC-231 | `tests/test_repo_browse_api.py` |
| AC-REQ-31 | TC-236, TC-237, TC-238, TC-239 | `tests/test_repo_file_api.py` |
| AC-REQ-32 | TC-204, TC-209, TC-214 | `tests/test_repo_binding_api.py`、`tests/test_repo_connectivity_api.py` |
| AC-REQ-33 | TC-242, TC-243, TC-244 | `tests/test_repo_lifecycle_api.py` |
| AC-REQ-34 | TC-221, TC-235, TC-241 | `tests/test_repo_sync_api.py`、`tests/test_repo_file_api.py`、`tests/test_repo_security_logs.py` |
| AC-REQ-35 | TC-224, TC-250 | `tests/test_repo_browse_api.py`、`RepoBindingPanel.test.tsx` |

## 估算汇总

| 批次 | 任务数 | 估算 |
|------|-------|------|
| A 基座与四表迁移 0008 | 8 | 50h |
| B 绑定与连通性测试 | 7 | 72h |
| C 同步与环境快照 | 5 | 46h |
| D 浏览与按需读文件 | 6 | 60h |
| E 前端与验收 | 6 | 66h |
| **合计** | **32** | **294h（≈37 人日）** |

- **关键路径**（单人不并行）：TASK-RI-201 → 202 → 205 → 206 → 207 → 211 → 212 → 213 → 215 → 216 → 217 → 221 → 222 → 223 → 231 → 232 → 233 → 234 → 241 → 242 → 244 → 246，约 **234h（≈29 人日）**。
- 批次内 202/203/204、213/214、242/243 可并行，压缩后约 26–29 人日。
