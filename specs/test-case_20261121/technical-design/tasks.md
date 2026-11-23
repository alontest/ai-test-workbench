# Tech Tasks — test-case + qa-skills + approvals 最小闭环

> 阶段：tech-tasks。上游：`specs/test-case_20261121/technical-design/design.md`。
> 编号：任务 `TASK-TC-301` 起；测试 `TC-301` 起。迁移固定 `0009_test_case_minimal_loop`，`down_revision="0008"`。

## 任务分组

### 批次 A：五表迁移 0009、`qa-skills` v0 与 `approvals` 轻量版后端（TASK-TC-301 ~ TASK-TC-303）
- 目标：落地迁移 `0009` 与 5 张 ORM 表；实现 `qa-skills`（内置种子技能、CRUD、版本历史、回滚、AI Diff 提案）与 `approvals`（列表、详情、Unified Diff、批准落盘、驳回不落盘）。
- 出口条件：`alembic upgrade head` 通过，`test_mysql_ddl_rules.py` 绿；`TC-301` ~ `TC-308` 全绿。

### 批次 B：自动上下文推荐（Context Recommender）与 `test-case` 两阶段生成/Stale/导出后端（TASK-TC-304 ~ TASK-TC-306）
- 目标：实现零 LLM 成本的上下文推荐端点（KB 条目匹配 + 1 跳邻居 + 三路代码路径召回）；实现阶段 1 检查点矩阵规划、阶段 2 结构化用例生成、KB 变更/删除后的动态 Stale 标红与确认复核、以及 CSV/Markdown/JSON 导出。
- 出口条件：`TC-309` ~ `TC-317` 全绿。

### 批次 C：入口状态点亮与前端三页闭环（TASK-TC-307 ~ TASK-TC-310）
- 目标：将 `case-library` 状态切换为 `live`；实现 `/extensions/skills`（QA 技能库页）、`/extensions/approvals`（审批中心页）、`/entrances/case-library`（用例库双视图 + 两阶段生成 + 上下文推荐 + Stale 复核 + 导出）及全部前端单测。
- 出口条件：`TC-318` ~ `TC-320` 与前端 Vitest 全绿，后端 Pytest 全绿。

---

## 任务清单

- [x] TASK-TC-301：实现迁移 `0009_test_case_minimal_loop` 与 5 张 ORM 模型
  - **涉及文件**：`migrations/versions/0009_test_case_minimal_loop.py`、`src/workbench/db/models/qa_skill.py`、`src/workbench/db/models/qa_skill_version.py`、`src/workbench/db/models/approval_request.py`、`src/workbench/db/models/test_case_design_plan.py`、`src/workbench/db/models/test_case.py`、`src/workbench/db/models/__init__.py`、`tests/test_tc_minimal_loop_migrations.py`
  - **具体操作**：按 `design.md` 建立 5 张表与双方言约束；验证 `scope_key + slug` 唯一约束与 MySQL DDL 渲染守卫。
  - **TC**：TC-301、TC-302
  - **状态**：completed

- [x] TASK-TC-302：实现 `qa-skills` 服务与 API（内置 v0 种子、人工 CRUD、版本回滚、AI 修订提案）
  - **涉及文件**：`src/workbench/services/skills.py`、`src/workbench/api/v1/skills.py`、`tests/test_skills_and_approvals_api.py`
  - **具体操作**：幂等初始化内置《两阶段测试设计与用例生成规范》v0；支持 `global` / `project` 技能创建与更新；支持通过 `calls.complete` 生成 Unified Diff 并创建 `pending` 审批单（不静默改技能）；支持一键回滚到历史版本。
  - **TC**：TC-303、TC-304、TC-305、TC-306
  - **状态**：completed

- [x] TASK-TC-303：实现 `approvals` 审批中心服务与 API（列表、详情、批准落盘、驳回保留）
  - **涉及文件**：`src/workbench/services/approvals.py`、`src/workbench/api/v1/approvals.py`、`tests/test_skills_and_approvals_api.py`
  - **具体操作**：实现 `pending -> approved / rejected` 状态机；批准时单事务更新 `qa_skill.content_md` 与 `current_version` 并追加 `qa_skill_version`（`source_type='agent_proposal'`）；驳回时原技能不变；重复审批返回 409 `approval_already_decided`。
  - **TC**：TC-307、TC-308
  - **状态**：completed

- [x] TASK-TC-304：实现自动上下文推荐服务与 API（Context Recommender）
  - **涉及文件**：`src/workbench/services/context_recommender.py`、`src/workbench/api/v1/test_cases.py`、`tests/test_test_cases_api.py`
  - **具体操作**：基于输入文本对项目当前 `KnowledgeBase` 条目打分并扩展 1 跳 `neighbors`；聚合命中条目 `code_paths`、项目激活仓库 `RepoFileReadRecord` 与文本路径提及。
  - **TC**：TC-309、TC-310
  - **状态**：completed

- [x] TASK-TC-305：实现 `test-case` 两阶段生成服务与 API（阶段 1 检查点矩阵 → 阶段 2 结构化用例）
  - **涉及文件**：`src/workbench/services/test_cases.py`、`src/workbench/api/v1/test_cases.py`、`tests/test_test_cases_api.py`
  - **具体操作**：阶段 1 调用 `calls.complete` 生成检查点矩阵并落库 `TestCaseDesignPlan`；阶段 2 按用户勾选的 `selectedCheckpointIds` 调用 `calls.complete` 生成结构化用例并绑定 `kb_links`（含 `contentDigest`）与 `code_paths`。
  - **TC**：TC-311、TC-312、TC-313
  - **状态**：completed

- [x] TASK-TC-306：实现 `test-case` Stale 动态标红、确认复核与多格式导出（CSV / Markdown / JSON）
  - **涉及文件**：`src/workbench/services/test_cases.py`、`src/workbench/api/v1/test_cases.py`、`tests/test_test_cases_api.py`
  - **具体操作**：对比用例 `kb_links` 快照与当前生效知识库条目的 `content_digest` 计算 `staleStatus` 与 `staleReasons`（`entry_modified` / `entry_removed` / `kb_deleted`）；提供 `acknowledge-stale` 刷新基线；提供 `csv` / `markdown` / `json` 导出。
  - **TC**：TC-314、TC-315、TC-316、TC-317
  - **状态**：completed

- [x] TASK-TC-307：点亮 `case-library` 为 `live` 并实现前端 `SkillsPage`、`<ApprovalsPage />` 与 `<CaseLibraryPage />`
  - **涉及文件**：`src/workbench/core/entrances.py`、`web/src/features/extensions/SkillsPage.tsx`、`web/src/features/extensions/ApprovalsPage.tsx`、`web/src/features/test-cases/CaseLibraryPage.tsx`、`web/src/features/entrances/EntrancePage.tsx`、`web/src/features/extensions/routes.tsx` 及对应前后端单测
  - **具体操作**：`case-library` 切为 `live`；完成技能管理+AI提案、审批中心 Diff 批准/驳回、用例库两阶段生成+表格/层级树双视图+Stale 复核+导出。
  - **TC**：TC-318、TC-319、TC-320
  - **状态**：completed
