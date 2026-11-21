# Test Strategy — repo-integration

> 阶段：tech-design（补充产出：测试策略与 TC 编号）。依据 ADR-217、`docs/api-spec.md`、`docs/database-schema.md`、`docs/architecture-decisions.md`。
> **编号规则**：core 占 TC-001 ~ TC-071，knowledge-base 占 TC-101 ~ TC-150；本 spec 使用 **TC-201 ~ TC-252**（52 条）。用例名统一 `test_tcNNN_<行为>`（如 `test_tc201_create_binding_encrypts_token_and_returns_mask`）。后续新增用例从 TC-253 顺延，不复用编号。

## 1. 测试分层与基础设施

| 层 | 范围 | 设施 |
|----|------|------|
| 纯函数单测 | `repos/` 的 validation / crypto / cursor / ssrf / redaction | 直接调用，无 DB、无网络 |
| 适配器测试 | GitHub / 云效六方法、分页、限流、错误映射 | `httpx.MockTransport` + 录制 fixture；**不发真实网络** |
| 服务级测试 | 绑定、测试、同步、浏览、文件、解绑 | 测试 `Session`（SQLite 临时文件库，WAL + `busy_timeout`）+ 临时数据库文件 |
| API 级测试 | 15 个端点 | `httpx.ASGITransport` + `create_app()` fixture；core 登录 fixture 或 `dependency_overrides` |
| 迁移测试 | `0008` 在 SQLite 与 MySQL 各跑一次 | 默认套件 SQLite；CI 追加 MySQL 8.4 service 容器 |
| 安全断言 | 令牌与文件正文不进入响应/错误体/日志/记录 | `caplog` + 响应体扫描；令牌与正文用随机哨兵串（`ghp_RISENTINEL<uuid>`、`SENTINEL-<uuid>`） |
| 前端组件 | 面板状态、徽标、表单、抽屉 | Vitest + Testing Library（core 已有配置） |
| 端到端 | 绑定 → 测试 → 同步 → 浏览 → 读文件 → 解绑 | Playwright（不进默认门禁，由 E2E 批次执行） |

通用纪律：

- 所有供应商调用用 `MockTransport` 回放 fixture；fixture 覆盖 200、401、403（含限流头）、404、429、超时、5xx、非法 JSON、截断、满页、大文件、非 UTF-8、二进制。
- 令牌统一用哨兵值；每个涉及令牌的用例断言响应体、错误体、`caplog`、`repo_sync_record.error_message`、`repo_file_read_record` 中完整令牌出现次数为 0。
- 时间相关断言注入固定 `now`（如 `2026-11-20T02:00:00Z`），不用 `sleep`。
- 限额用小值覆盖（如 `REPO_FILE_MAX_BYTES` 通过测试常量或 service 注入调整为 1,024），避免生成大文件。
- 每个测试独立临时数据库文件与 `tmp_path`；不读写本机真实 `$AW_DATA_DIR`。
- 前端测试用 MSW 或直接 mock `apiFetch`；不连真实后端。

## 2. 用例清单（TC-201 ~ TC-252）

| TC | 用例名（简） | 层级 | 覆盖 AC / 规则 | 关键断言 |
|----|-------------|------|---------------|---------|
| TC-201 | `test_tc201_create_binding_encrypts_token_and_returns_mask` | API | AC-017-1 / AC-REQ-25 | 201；库中 `token_ciphertext` 为 `v1:` 密文、`token_masked` 正确；响应无完整令牌 |
| TC-202 | `test_tc202_create_binding_rejects_invalid_fields` | API | AC-017-2 / AC-REQ-25 | 缺令牌 / 非法标识 / 非 https 域名 → 400 `token_required` / `invalid_repo_identifier` / `invalid_api_base_url`；不写任何行 |
| TC-203 | `test_tc203_duplicate_binding_rejected_original_unchanged` | API | AC-017-3 | 同项目同 provider 同 repo → 409 `repo_binding_duplicate`；原行密文与掩码不变 |
| TC-204 | `test_tc204_update_token_only_replaces_token_and_mask` | API | AC-017-4 / AC-023-2 | `bindingId`、快照、同步记录不变；密文与掩码更新；后续解密使用新令牌 |
| TC-205 | `test_tc205_binding_count_has_no_hard_limit` | API | AC-017-6 / AMB-025 | 同一项目可创建 >5 个不同仓库绑定；列表返回全部（分页）；不返回数量错误 |
| TC-206 | `test_tc206_api_base_url_validation_and_provider_defaults` | API + 单测 | AC-017-2 / ADR-213 | 云效默认域名；GitHub 固定域名（传其他值 400）；http / 路径 / 查询 / 端口非 443 → 400 |
| TC-207 | `test_tc207_binding_not_found_and_project_not_found` | API | AC-REQ-25 | 未知 `bindingId` → 404 `binding_not_found`；未知 `projectId` → 404 `project_not_found`；不泄露资源存在性 |
| TC-208 | `test_tc208_saved_test_success_sets_connected` | API | AC-018-1 / AC-018-5 / AC-REQ-26 | 200 `result=success`；含默认分支与测试时间；`status=connected`、`lastVerifiedAt` 更新 |
| TC-209 | `test_tc209_auth_failure_marks_token_invalid` | API | AC-018-2 / AC-023-1 / AC-REQ-32 | 401 → `result=auth-error`、`status=token_invalid`；响应与日志无令牌 |
| TC-210 | `test_tc210_network_and_timeout_do_not_change_status` | API | AC-018-3 / AC-REQ-26 | DNS/连接拒绝/读取超时 → `result=unreachable`；不写同步记录、不改状态与快照 |
| TC-211 | `test_tc211_permission_denied_not_misclassified` | API | AC-018-4 / AC-REQ-26 | 403 无速率信号 → `result=permission-denied`（非 auth-error / unreachable）；`status=token_invalid` |
| TC-212 | `test_tc212_unsaved_test_writes_nothing` | API | AC-018-1 / AMB-028 | 200 结果；`repo_binding` / `repo_sync_record` / `repo_file_read_record` 行数均为 0；`bindingStatus=null` |
| TC-213 | `test_tc213_provider_error_mapping_table` | 单测 | ADR-206 / AC-REQ-26 / AC-REQ-28 | 逐行覆盖映射表：403+限流头 → rate_limited；403 其他 → permission_denied；429、超时、5xx、非法 JSON 各归其类 |
| TC-214 | `test_tc214_token_expiration_header_null_when_absent` | 单测 + API | AC-023-3 | 有 `GitHub-Authentication-Token-Expiration` → 解析为 `tokenExpiresAt`；无头或格式非法 → `null`；不推测、不提示即将过期 |
| TC-215 | `test_tc215_connectivity_respects_ten_second_budget` | 服务 | AC-018-1 | 上游挂起超过 10s → 中止并归 `unreachable`（timeout）；不产生同步记录 |
| TC-216 | `test_tc216_sync_success_replaces_snapshot_and_updates_summary` | API | AC-019-1 / AC-019-4 / AC-019-6 | 快照 1 仓库 + N 分支 + ≤100 提交；`repo_sync_record=success`；`lastSyncSuccessAt`、耗时、基线更新 |
| TC-217 | `test_tc217_concurrent_sync_returns_409_without_second_record` | 服务 | AC-019-2 | claim 冲突 → 409 `sync_in_progress`；`repo_sync_record` 仅 1 条 |
| TC-218 | `test_tc218_stale_claim_reclaimed_and_marked_interrupted` | 服务 | ADR-207 / RISK-205 | 遗留 `running` + claim 超过 TTL → 归并 `failed/interrupted`；新同步可继续 |
| TC-219 | `test_tc219_sync_failure_preserves_old_snapshot_and_time` | API | AC-019-3 / AC-REQ-27 | 分支分页中途失败 → 快照行与 `lastSyncSuccessAt` 不变；只新增失败记录 |
| TC-220 | `test_tc220_sync_rate_limit_reports_retry_after_without_retry` | API | AC-019-5 / AC-REQ-28 | 429 → `errorCategory=rate_limit`、`retryAfterAt` 正确；适配器只调用 1 次，无自动重试 |
| TC-221 | `test_tc221_sync_stores_metadata_only` | API | AC-019-6 / AC-REQ-34 | `payload` 无文件正文；无 `kind=tree` 行；提交 100 条且倒序；仓库/分支全量覆盖 |
| TC-222 | `test_tc222_sync_records_paginated_desc` | API | AC-019-4 | 记录按 `startedAt DESC`；`limit`+`cursor` 翻页不重不漏；从未同步返回空数组 |
| TC-223 | `test_tc223_sync_budget_aborts_without_partial_snapshot` | 服务 | ADR-211 | 总预算 120s 超时 → `failed/other`；不写半成品快照 |
| TC-224 | `test_tc224_repositories_live_search_and_default` | API | AC-020-1 / AC-REQ-29 / AC-REQ-35 | 实时请求；`search` 透传；默认绑定仓库；适配器只发 GET |
| TC-225 | `test_tc225_branches_live_pagination_and_default_branch` | API | AC-020-2 / AC-REQ-29 | 分支分页；`isDefault` 标记；切换 ref 后提交/树使用新 ref |
| TC-226 | `test_tc226_unsynced_browse_returns_empty_state` | API | AC-020-3 / ADR-208 | 从未同步 → 200 `{metadataSynced:false, items:[], guide:"sync_first"}`；不发外呼、不返回错误页 |
| TC-227 | `test_tc227_revoked_binding_blocks_provider_calls` | API | AC-023-4 / AMB-031 | 浏览/读文件/同步/测试 → 409 `binding_revoked`；provider 调用次数 0 |
| TC-228 | `test_tc228_token_invalid_live_502_and_baseline_still_readable` | API | AC-020-4 / AC-023-1 | 实时端点 → 502 `provider_auth_failed`；`GET /baseline` 200 且含上次同步时间 |
| TC-229 | `test_tc229_commits_live_desc_with_short_sha` | API | AC-021-1 / AC-021-4 | 倒序；`shortSha` 7 位；标题/作者/时间；空提交返回空数组 |
| TC-230 | `test_tc230_tree_lazy_pages_and_has_more` | API | AC-021-2 | 逐级 `path`；`hasMore` + `nextCursor`；加载下一页合并；缩进层级由前端 |
| TC-231 | `test_tc231_tree_truncated_not_reported_as_complete` | API | AC-021-3 / AC-REQ-30 | GitHub 返回 1,000 条 → `truncated=true`；UI 展示固定提示（组件测试） |
| TC-232 | `test_tc232_cursor_tamper_and_cross_query_rejected` | API | ADR-208 | 篡改签名 / 换 binding / 换 ref 复用 → 400 `invalid_cursor`；合法游标翻页正确 |
| TC-233 | `test_tc233_baseline_reads_snapshot_without_provider` | API | AC-020-4 / AC-023-5 / ADR-208 | 返回仓库/分支/提交快照与 `lastSyncSuccessAt`；provider 调用 0；解绑后仍可读 |
| TC-234 | `test_tc234_metadata_response_cap_and_invalid_json` | 单测 | ADR-209 / ADR-210 | 响应 >5 MiB 或 JSON 非法 → `invalid_response`；不 OOM、不返回原始响应 |
| TC-235 | `test_tc235_file_read_success_records_metadata_only` | API | AC-022-1 / AC-022-4 / AC-REQ-34 | 200 返回 `content` + path/ref/size/fetchedAt；`repo_file_read_record=success`；库中无正文 |
| TC-236 | `test_tc236_file_too_large_rejected_without_truncation` | API | AC-022-2 / AC-REQ-31 | >1 MiB → 413 `repo_file_too_large`；`details` 含实际大小与上限；未截断；记录 `refused/too_large` |
| TC-237 | `test_tc237_binary_content_rejected` | API | AC-022-3 | `encoding=base64` 或内容含 NUL → 415 `repo_file_binary`；记录 `refused/binary` |
| TC-238 | `test_tc238_non_utf8_rejected` | API | AC-022-3 | UTF-8 解码失败 → 422 `repo_file_not_utf8`；不展示乱码；记录 `refused/not_utf8` |
| TC-239 | `test_tc239_invalid_path_or_ref_rejected_before_request` | API + 单测 | AC-022-5 / AC-REQ-31 | `..`、绝对路径、控制字符、非法 ref → 400 `invalid_path` / `invalid_ref`；provider 调用 0；读取记录 0 |
| TC-240 | `test_tc240_file_read_on_revoked_binding_409` | API | AC-023-4 / AMB-031 | 409 `binding_revoked`；provider 调用 0；不写读取记录 |
| TC-241 | `test_tc241_file_content_never_in_logs_or_records` | 安全 | AC-REQ-34 / BR-C25 | 成功与拒绝路径的日志、错误体、记录表均无正文哨兵；错误只含分类/大小 |
| TC-242 | `test_tc242_unbind_clears_token_and_stops_requests` | API | AC-023-4 / AC-REQ-33 | `status=revoked`、`active_flag=NULL`、密文/掩码为空、`revokedAt` 非空；后续 provider 调用 0 |
| TC-243 | `test_tc243_unbind_keeps_snapshots_and_history` | API | AC-023-5 / AC-REQ-33 | 仓库/分支/提交快照与同步/读取记录不变；历史会话/制品/调用记录不受影响 |
| TC-244 | `test_tc244_rebind_creates_new_binding_and_token` | API | AC-023-6 | 新 `bindingId`、新密文；不复用旧同步记录；旧行仍 `revoked` |
| TC-245 | `test_tc245_all_endpoints_require_session` | API | ADR-212 | 15 个端点无 Cookie → 401 `unauthorized`；不泄露资源存在性 |
| TC-246 | `test_tc246_token_never_in_logs_errors_or_records` | 安全 | AC-REQ-25 / BR-C21 | 创建/测试/同步/读文件/失败路径的响应、错误体、日志、记录表完整令牌出现 0 次 |
| TC-247 | `test_tc247_migration_0008_on_both_dialects` | 迁移 | ADR-203 / RISK-207 | SQLite + MySQL 各跑 `upgrade head` → `downgrade 0007` → `upgrade head`；四表、索引、CHECK、CASCADE 存在 |
| TC-248 | `test_tc248_repo_token_key_required_and_valid` | 配置 | ADR-216 / RISK-210 | 缺失 / 非 base64 / 长度≠32 → 启动失败；合法值启动成功；`AW_ENCRYPTION_KEY` 不受影响 |
| TC-249 | `test_tc249_error_body_and_time_format` | API | ADR-212 | 错误体 `{code,message,details[],requestId}`；`details` 数组；时间为 RFC 3339 UTC |
| TC-250 | `test_tc250_panel_states_and_permission_hint` | 前端 | AC-017-5 / AC-018-5 / AC-023-1 | 四态徽标、掩码、测试四类结果、`stale` 失效、权限说明、单一失效横幅 |
| TC-251 | `test_tc251_full_repo_flow_e2e` | E2E | US-017 ~ US-023 | Playwright：绑定 → 测试 → 同步 → 浏览 → 读文件 → 解绑；已解绑入口置灰 |
| TC-252 | `test_tc252_ssrf_blocks_private_and_redirects` | 单测 + 服务 | ADR-213 / RISK-202 | 私网/回环/链路本地/保留地址、http、非 443、重定向 → 拒绝；GitHub 固定域名 |

## 3. AC ↔ TC 映射

| AC | 覆盖 TC |
|----|---------|
| AC-017-1 | TC-201, TC-246 |
| AC-017-2 | TC-202, TC-206 |
| AC-017-3 | TC-203 |
| AC-017-4 | TC-204 |
| AC-017-5 | TC-250 |
| AC-017-6 | TC-205 |
| AC-018-1 | TC-208, TC-212, TC-215 |
| AC-018-2 | TC-209 |
| AC-018-3 | TC-210 |
| AC-018-4 | TC-211 |
| AC-018-5 | TC-208, TC-250 |
| AC-019-1 | TC-216 |
| AC-019-2 | TC-217 |
| AC-019-3 | TC-219 |
| AC-019-4 | TC-216, TC-222 |
| AC-019-5 | TC-220 |
| AC-019-6 | TC-216, TC-221 |
| AC-020-1 | TC-224 |
| AC-020-2 | TC-225 |
| AC-020-3 | TC-226 |
| AC-020-4 | TC-228, TC-233 |
| AC-021-1 | TC-229 |
| AC-021-2 | TC-230 |
| AC-021-3 | TC-231 |
| AC-021-4 | TC-229, TC-230 |
| AC-022-1 | TC-235 |
| AC-022-2 | TC-236 |
| AC-022-3 | TC-237, TC-238 |
| AC-022-4 | TC-235 |
| AC-022-5 | TC-239 |
| AC-023-1 | TC-209, TC-227, TC-228 |
| AC-023-2 | TC-204 |
| AC-023-3 | TC-214 |
| AC-023-4 | TC-227, TC-242 |
| AC-023-5 | TC-233, TC-243 |
| AC-023-6 | TC-244 |
| AC-REQ-25 | TC-201, TC-202, TC-203, TC-204, TC-205, TC-207, TC-246 |
| AC-REQ-26 | TC-208, TC-210, TC-211, TC-213 |
| AC-REQ-27 | TC-216, TC-217, TC-219, TC-220, TC-223 |
| AC-REQ-28 | TC-213, TC-220 |
| AC-REQ-29 | TC-224, TC-225, TC-226, TC-228 |
| AC-REQ-30 | TC-229, TC-230, TC-231 |
| AC-REQ-31 | TC-236, TC-237, TC-238, TC-239 |
| AC-REQ-32 | TC-204, TC-209, TC-214 |
| AC-REQ-33 | TC-242, TC-243, TC-244 |
| AC-REQ-34 | TC-221, TC-235, TC-241 |
| AC-REQ-35 | TC-224, TC-250 |

## 4. 测试落点（文件级）

| 文件 | 覆盖 TC |
|------|---------|
| `tests/test_repo_config.py` | TC-248 |
| `tests/test_repo_validation.py` | TC-202, TC-206, TC-239 |
| `tests/test_repo_crypto.py` | TC-201, TC-246 |
| `tests/test_repo_cursor.py` | TC-232 |
| `tests/test_repo_provider_github.py` | TC-208 ~ TC-215, TC-224, TC-230, TC-231, TC-234 |
| `tests/test_repo_provider_yunxiao.py` | TC-208 ~ TC-215, TC-224, TC-230, TC-231 |
| `tests/test_repo_binding_api.py` | TC-201 ~ TC-207 |
| `tests/test_repo_connectivity_api.py` | TC-208 ~ TC-215 |
| `tests/test_repo_sync_service.py` | TC-216 ~ TC-223 |
| `tests/test_repo_sync_api.py` | TC-216, TC-219, TC-220, TC-222 |
| `tests/test_repo_browse_api.py` | TC-224 ~ TC-234 |
| `tests/test_repo_file_api.py` | TC-235 ~ TC-241 |
| `tests/test_repo_lifecycle_api.py` | TC-227, TC-242 ~ TC-244 |
| `tests/test_repo_security_logs.py` | TC-241, TC-246 |
| `tests/test_repo_migrations.py` | TC-247 |
| `tests/test_repo_api_contract.py` | TC-245, TC-249 |
| `web/src/features/repos/*.test.tsx` | TC-250 |
| `web/e2e/repo.spec.ts` | TC-251 |

## 5. 门禁与执行

- 后端门禁 `uv run pytest -q`；测试报告需逐条出现 TC 编号，且新增 TC 必须同提交登记到 `test-verification/tc-map.json`（由 `tests/test_spec_tc_sync.py` 断言）。
- 默认套件（SQLite）必须全绿；CI 额外启动 MySQL 8.4 容器跑同一套用例（至少 `test_repo_migrations.py` 与全部 API 用例）。
- 前端 Vitest 覆盖 TC-250；Playwright（TC-251）为交付前人工/CI 可选门禁，不阻塞后端批次。
- 失败处理：先修实现；确认用例本身写错才改用例，并在提交说明里写明原因。
- 未验证项：真实云效/GitHub 的限流数值、云效单文件上限、GitHub fine-grained PAT 过期头格式（见 `design.md`「未核实外部事实与处理口径」）；测试不连真实供应商，不用真实令牌。
