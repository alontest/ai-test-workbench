# Test Verification Requirements — workbench-core

> 阶段：test-verification。模块：ai-test-workbench（本 spec 只覆盖 `workbench-core` 域）。
> 上游：`requirements-analysis/docs/context.md`（US 11 / AC 42 / EARS 17）、`technical-design/tasks.md`（55 个任务、70 个 TC）、`technical-design/docs/context.md`；另含实现期补充并已由 `aw verify` 通过的 TC-071（DB 错误映射方言可移植性）。
> 依据：`approvals.md` 的 `tech-design · 2026-11-18 11:35:21 · 重新确认` 与 `tech-tasks · 2026-11-18 11:35:21 · 重新确认`（跨 spec 知识库注入扩展 ADR-042；55 任务 / 70 TC）。
> 本体：`ontology-slices/test-verification.md` 不存在（项目无 `ontology-work/views/index.json`），本阶段不做本体对照，TC 的「涉及本体」一律记为「无」。
> 开发尚未开始（仓库只有骨架 `src/workbench/__init__.py`、`tests/conftest.py`），本阶段只产出用例、映射与执行计划；所有 TC 的初始结果为 `待执行`。

## 1. 交付范围

### 1.1 必须交付

| 交付物 | 说明 | 落点 |
|--------|------|------|
| 测试策略与分层 | 框架选型、单元/集成/迁移/人工验收的分工与占比 | `design.md` §测试策略、§测试分层 |
| 71 个 TC 用例 | TC-001 ~ TC-071（TC-001 ~ 063 基线；TC-064 ~ 070 知识库注入扩展；TC-071 DB 错误映射方言差异），逐条含目的、前置、原子步骤、可验证预期、边界数据、pytest 落点 | `design.md` §测试用例列表 |
| TC ↔ AC ↔ 任务映射 | 42 条功能 AC + 6 条 AC-TECH 全覆盖；每个非 `[no-test]` 任务映射到覆盖它的 TC | `design.md` §覆盖矩阵、`tc-map.json` |
| 测试数据与环境策略 | 临时 SQLite 文件库、MySQL 第二方言、假 AI 适配器、时钟注入、上传夹具 | `design.md` §测试数据与环境策略 |
| 缺陷分级与回归口径 | 缺陷等级、修复后回归范围、偶发失败处理 | `design.md` §缺陷分级与回归口径 |
| 人工验证清单 | 只能人工执行的项目、执行者、产出物与落点 | `design.md` §人工验证清单 |
| CI 与本地验证分工 | `aw verify`（SQLite）为权威，CI 三 job 各自的门禁作用与证据边界 | `design.md` §CI 与本地验证分工 |
| 验收清单 | 关闭前需满足的全部门槛 | `design.md` §验收清单 |
| 回归清单 | 每个 TC 的来源、步骤、预期，供后续 spec 复用 | `docs/regression.md` |

### 1.2 Out of Scope

- 性能测试与容量测试（并发压测、长稳、内存泄漏）单独规划，不在本阶段。
- 安全渗透测试（越权扫描、口令爆破工具、依赖漏洞扫描）单独规划；本阶段只覆盖 AC 明示的鉴权、Origin、脱敏与路径穿越断言。
- Playwright E2E 不进必过门禁，只作为人工验收的补充证据。
- Vitest 结果不进入 `.aw` 证据；其失败由 CI `frontend-tests` job 与分支保护兜底（既定口径，不改）。
- 真实第三方 AI 提供商可用性（需要真实密钥与外网）只做可选人工连通验证。
- 知识库（US-012 ~ US-016）与仓库集成（US-017 ~ US-023）不在本 spec，不设 TC。

## 2. 验收标准（EARS，AC-QA）

**AC-QA-1（正向覆盖）**
GIVEN `requirements-analysis/docs/context.md` 的 42 条功能 AC
WHEN 评审 TC 列表
THEN 每条 AC 至少有一个正向 TC，且 TC 在 `design.md` 中以 `### TC-NNN` 定义并给出可执行的 pytest 落点。

**AC-QA-2（异常与边界覆盖）**
GIVEN 含错误条件或数值边界的 AC（AC-003-2、AC-005-2/3/5、AC-006-2/3、AC-007-2、AC-008-1、AC-009-4、AC-011-3/4/5）
WHEN 评审 TC 列表
THEN 每条 AC 至少有一个异常或边界 TC，且用例中写明具体边界值（200000/200001 字符、10MB/10MB+1、10/11 个文件、5 次失败、8 小时、120s/10s 超时）。

**AC-QA-3（Critical 风险覆盖）**
GIVEN `technical-design/design.md` 风险登记表的 7 个 🔴 Critical（RISK-001/002/005/009/010/011/012）
WHEN 评审覆盖矩阵
THEN RISK-001/002/005/010/011/012 各至少 2 个 TC（触发 + 边界）；RISK-009 由 In Scope 约束与 `[no-test]` 范围说明覆盖，不新增运行时 TC。

**AC-QA-4（结果可追溯、不伪造）**
GIVEN 开发完成后的测试报告
WHEN 回填 `## 执行结果`
THEN 每个 TC 的结果只来自 `aw.py verify` 读到的 pytest 结果或真实执行过的人工验证；未执行写 `待执行`，禁止把未实现的用例写成 `通过`。

**AC-QA-5（人工验证可复核）**
GIVEN 只能人工执行的验证项（UI 视觉、Playwright、部署与备份演练、TLS 下 Cookie）
WHEN 执行人工验收
THEN 每项都有执行记录与产出物（截图/日志/命令输出），落点见 `design.md` §人工验证清单。

**AC-QA-6（Round-Trip 覆盖）**
GIVEN `requirements-analysis/raw-requirements.md` 的原始需求
WHEN 做 Round-Trip 验证
THEN 每条原始需求都能追到 AC、TC 与执行结果，覆盖率 = 有对应 TC 的需求数 / 总需求数，且矩阵如实标注 `⏳ pending`。

**AC-QA-7（用例名可被 `aw verify` 识别）**
GIVEN `.aw/test-presets.json` 的 pytest 命名规则
WHEN 编写用例
THEN 每个 TC 至少有一个函数名包含 TC 编号的 pytest 用例（`def test_tcNNN_*()`），71 个 TC 全部可由 `python3 .aw/aw.py verify` 从 JUnit 报告识别。

**AC-QA-8（门禁分工不混用）**
GIVEN 既定验证口径
WHEN 记录结果
THEN 明确区分「本地 SQLite pytest 结果」「CI MySQL job」「CI Vitest job」「人工验收」四类证据；SQLite 绿不得表述为双方言通过，Vitest 绿不得表述为 `aw verify` 通过。

## 3. 依赖与假设

- 测试框架跟随已确认技术栈：pytest + pytest-asyncio + httpx `ASGITransport`；前端 Vitest + Testing Library（CI job 3）。仓库未安装任何 pack（`.aw/install.json` 的 `packs` 为空），按通用最佳实践并在 `design.md` 注明。
- 本地 `aw verify` 只跑 SQLite（`.aw/config.json` 仅配置 pytest）；MySQL 由 CI job 2 覆盖。
- 5 个 `[no-test]` 任务（TASK-TD-001/018/048/049/050）不映射 TC，由构建、CI 实际运行、部署与备份手工演练验收。
- 跨 spec TC 编号约定：core 使用 TC-001 ~ TC-071；knowledge-base 计划使用 TC-101 起；repo-integration 计划使用 TC-201 起。编号段不重叠、不复用。
- 本地 `aw verify` 只跑 SQLite；TC-071 是 CI `mysql-tests` job 暴露方言差异（MySQL 3819/1062/1451/1452）后补的回归用例，说明本地 SQLite 绿不等于双方言通过。
- 知识库边界：TC-064 ~ TC-070 只验证 core 的迁移列、注入留痕、唯一入口 `/ai/complete`、错误映射、`kbDeleted` 序列化与展示；知识库导入、检索、失效判定与正文组装由 knowledge-base spec（TC-101 起）覆盖，本 spec 用假 `InjectionPreparer` 验证契约。
- 测试数据一律在临时目录生成，不提交大文件与真实密钥；`AW_ADMIN_PASSWORD`、`AW_ENCRYPTION_KEY` 用测试固定值。

## 4. 状态

pending（2026-11-18 产出；等待用户确认本阶段。TC 全部 `待执行`，开发完成后由 `aw verify` 回填）
