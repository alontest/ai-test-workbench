# Test Verification Tasks — workbench-core

> 阶段：test-verification。任务 ID 前缀 `TASK-TV-`。
> 依据：`design.md` 的 70 个 TC、分层策略与人工验证清单；上游任务见 `technical-design/tasks.md`（TASK-TD-001 ~ 055，含批次 D 知识库注入扩展）。
> 状态：全部 `pending`。本阶段只产出计划与清单，不写实现代码；用例由开发任务（TASK-TD-*）落地时按 `design.md` 的自动化落点编写。

## 概览

- 任务总数：11
- P0：7（001 ~ 006、011）；P1：3（007 ~ 009）；P2：1（010）
- 预估工时：约 40h（不含开发实现；均为验证活动与记录）
- 覆盖：70 个 TC ↔ 50 个非 `[no-test]` 任务（见 `tc-map.json`）；42 功能 AC + 6 AC-TECH + 7 个跨 spec 扩展 TC

## 任务清单

- [ ] TASK-TV-001：建立测试基线与夹具
  - **描述**：在 `tests/conftest.py` 实现 `design.md` §测试数据与环境策略 的夹具：临时 SQLite 文件库、`create_app` 注入、`httpx.ASGITransport` 客户端、登录客户端、前置数据工厂、假 AI 适配器、可推进时钟、上传文件工厂。
  - **涉及文件**：`tests/conftest.py`（新增夹具）、`tests/factories.py`（如需要）
  - **具体操作**：每个用例独立 `tmp_path`；`alembic upgrade head`；默认带 `Origin: http://testserver`；禁止外网；测试结束清理临时目录。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-QA-1、AC-QA-4、AC-QA-7
  - **依赖**：TASK-TD-001、TASK-TD-010、TASK-TD-011
  - **覆盖 TC**：全部（基础设施）
  - **状态**：pending

- [ ] TASK-TV-002：批次 A 用例（基座与契约）
  - **描述**：编写 config、crypto、password、redaction、engine、迁移、API 骨架、入口常量、存储、启动自检的用例。
  - **涉及文件**：`tests/test_config.py`、`tests/test_crypto.py`、`tests/test_password.py`、`tests/test_redaction.py`、`tests/test_engine.py`、`tests/test_db_migrations.py`、`tests/test_api_skeleton.py`、`tests/test_entrances.py`、`tests/test_storage.py`、`tests/test_startup.py`
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-011-2、AC-003-1、AC-003-3、AC-007-1/2、AC-005-1、AC-001-1、AC-002-3、AC-TECH-1/2/3/6
  - **依赖**：TASK-TV-001
  - **覆盖 TC**：TC-002、TC-009、TC-017、TC-019、TC-021、TC-039、TC-040、TC-042、TC-049、TC-051、TC-056、TC-057、TC-058、TC-059、TC-060、TC-061、TC-063
  - **状态**：pending

- [ ] TASK-TV-003：认证与访问控制用例
  - **描述**：登录、令牌哈希、错误提示、锁定、并发计数、空闲过期、登出、Cookie 属性、`next` 校验。
  - **涉及文件**：`tests/test_auth_service.py`、`tests/test_auth_api.py`
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-011-1 ~ AC-011-7
  - **依赖**：TASK-TV-001、TASK-TD-019、TASK-TD-020
  - **覆盖 TC**：TC-001 ~ TC-012（TC-009 由 TASK-TV-002 覆盖，可合并执行）
  - **状态**：pending

- [ ] TASK-TV-004：项目、提供商与模型用例
  - **描述**：项目 CRUD、重名、校验；提供商加密/掩码/启停/连接测试；模型登记、重名、参数范围、默认参数。
  - **涉及文件**：`tests/test_projects_service.py`、`tests/test_projects_api.py`、`tests/test_providers_service.py`、`tests/test_providers_api.py`、`tests/test_models.py`
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-008-1 ~ AC-008-3、AC-003-1 ~ AC-003-4、AC-004-1 ~ AC-004-3、AC-005-2
  - **依赖**：TASK-TV-001、TASK-TD-022 ~ TASK-TD-029
  - **覆盖 TC**：TC-013 ~ TC-025、TC-050
  - **状态**：pending

- [ ] TASK-TV-005：会话、输入、制品与调用用例
  - **描述**：会话创建/筛选/时间线/终态/删除；文本与上传；调用成功/失败/前置拒绝/重试超时；批次 B 冒烟。
  - **涉及文件**：`tests/test_sessions_service.py`、`tests/test_sessions_api.py`、`tests/test_fail_session_hook.py`、`tests/test_inputs_api.py`、`tests/test_artifacts_service.py`、`tests/test_artifacts_api.py`、`tests/test_ai_gateway.py`、`tests/test_ai_adapters.py`、`tests/test_calls_api.py`、`tests/test_batch_b_smoke.py`
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-009-1 ~ AC-009-5、AC-006-1 ~ AC-006-3、AC-007-1 ~ AC-007-3、AC-005-1 ~ AC-005-5、AC-001-3、AC-TECH-1/4
  - **依赖**：TASK-TV-001、TASK-TD-030 ~ TASK-TD-041、TASK-TD-047
  - **覆盖 TC**：TC-026 ~ TC-045、TC-049、TC-050、TC-062
  - **状态**：pending

- [ ] TASK-TV-006：调用查询、入口与 UI 第二实现
  - **描述**：调用记录查询/详情/空态；入口配置与占位页；按 `design.md` 的 TC 编号补 Vitest 组件用例（不进 `.aw` 证据）。
  - **涉及文件**：`tests/test_calls_query.py`、`tests/test_entrances_api.py`、`web/src/**/*.test.tsx`
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-010-1 ~ AC-010-3、AC-001-1 ~ AC-001-3、AC-002-1 ~ AC-002-3
  - **依赖**：TASK-TV-001、TASK-TD-042 ~ TASK-TD-046
  - **覆盖 TC**：TC-031、TC-046 ~ TC-048、TC-051 ~ TC-056（pytest 权威；Vitest 同编号第二实现）
  - **状态**：pending

- [ ] TASK-TV-007：MySQL 与 CI 证据采集
  - **描述**：确认 CI 三 job 在公开仓库运行，采集 SQLite/MySQL/Vitest 的运行记录与失败原因；确认 TC-059 在本地 SQLite 也产生结果。
  - **涉及文件**：无代码改动；证据写入 `test-verification/evidence/manual/ci-runs.md`
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **关联需求**：AC-TECH-2、AC-TECH-3、AC-QA-8
  - **依赖**：TASK-TD-018、TASK-TV-002
  - **覆盖 TC**：TC-058、TC-059（job 1/2）、UI 第二实现（job 3）
  - **状态**：pending

- [ ] TASK-TV-008：人工验收执行与证据归档
  - **描述**：按 M-01 ~ M-06 执行视觉、Playwright、部署、备份恢复、TLS Cookie、长调用体验；产出物写入 `test-verification/evidence/manual/`。
  - **涉及文件**：`test-verification/evidence/manual/`（截图/日志/记录）
  - **优先级**：P1
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-QA-5、AC-011-7、AC-TECH-1/4、AC-TECH-6（RISK-015）
  - **依赖**：TASK-TD-048、TASK-TD-049、TASK-TV-006
  - **覆盖 TC**：无新增 TC；支撑 M-01 ~ M-06 与 `[no-test]` 任务验收
  - **状态**：pending

- [ ] TASK-TV-009：verify 回填、问题清单结论与覆盖率报告
  - **描述**：开发完成后执行 `python3 .aw/aw.py verify`，把 `evidence/verify.json` 的 `tcs` 回填 `design.md` 的 `## 执行结果`；逐条给 ISSUE LIST 结论；更新 `## 需求覆盖率报告`；跑 `aw.py check --phase test-verification`。
  - **涉及文件**：`test-verification/design.md`
  - **优先级**：P1
  - **复杂度**：S（<1d）
  - **关联需求**：AC-QA-4、AC-QA-6、AC-QA-8
  - **依赖**：TASK-TV-002 ~ TASK-TV-008、TASK-TV-011
  - **覆盖 TC**：TC-001 ~ TC-070（结果回填）
  - **状态**：pending

- [ ] TASK-TV-010：回归清单维护
  - **描述**：按 `docs/regression.md` 的 TC 分节维护来源、步骤与预期；后续修复或新 spec 复用时按节更新。
  - **涉及文件**：`test-verification/docs/regression.md`
  - **优先级**：P2
  - **复杂度**：XS（<4h）
  - **关联需求**：AC-QA-1、AC-QA-6
  - **依赖**：TASK-TV-002 ~ TASK-TV-006、TASK-TV-011
  - **覆盖 TC**：TC-001 ~ TC-070（清单维护）
  - **状态**：pending

- [ ] TASK-TV-011：知识库注入扩展用例（批次 D）
  - **描述**：编写迁移 `0006`、网关注入留痕、`/ai/complete` 入口、失效确认与预算、`kbDeleted` 序列化与时间线展示的 pytest 用例；用假 `InjectionPreparer` 锁定跨 spec 契约。
  - **涉及文件**：`tests/test_db_migrations.py`、`tests/test_ai_gateway_injection.py`、`tests/test_sessions_ai_complete.py`、`tests/test_knowledge_contract.py`、`tests/test_calls_api.py`、`tests/test_sessions_api.py`
  - **具体操作**：按 `design.md` TC-064 ~ TC-070 的步骤与边界断言；pytest 覆盖事件/接口/迁移，TC-070 的 UI 渲染由 Vitest（CI job 3）作为第二实现；不新增 TC-071+，不重复知识库 spec 的导入/检索用例。
  - **优先级**：P0
  - **复杂度**：M（2–3d）
  - **关联需求**：AC-005-1、AC-009-3、AC-010-2、AC-TECH-2、AC-TECH-3
  - **依赖**：TASK-TV-001、TASK-TD-051 ~ 055
  - **覆盖 TC**：TC-064 ~ TC-070
  - **状态**：pending
