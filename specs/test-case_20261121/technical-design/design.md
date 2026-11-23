# Technical Design — Design（test-case + qa-skills + approvals 最小闭环）

> 阶段：tech-design（最小闭环立项）。
> 范围：`qa-skills` v0（底座） + `approvals` 轻量版（闸门） + `context-recommender`（零 LLM 成本自动上下文推荐） + `test-case`（两阶段测试设计、双向溯源锚点、失效标红 Stale、表格/树视图与多格式导出）。
> 编号约定：任务 `TASK-TC-301` 起；测试 `TC-301` 起（core 占 001~071，knowledge-base 占 101~150，repo-integration 占 201~252）。迁移固定 `0009_test_case_minimal_loop`，`down_revision="0008"`。

---

## 一、第一性原理与反方自检（Adversarial Review）

在进入表结构与接口设计前，先对 5 个最容易埋雷的架构边界做反方推演与根因消解：

### 1. `qa_skill` 作用域唯一键陷阱（SQL `NULL != NULL`）
- **反方质询**：若 `qa_skill` 用 `project_id IS NULL` 表示全局技能（`global`），直接建 `UniqueConstraint("project_id", "slug")` 在 MySQL 8.4 与 SQLite 中均无法阻止重复插入同名全局技能（SQL 标准中 `NULL` 与 `NULL` 不冲突）。
- **根因方案**：引入非空归一化列 `scope_key VARCHAR(64) NOT NULL`：
  - 全局技能：`scope = 'global'`，`project_id = NULL`，`scope_key = 'global'`；
  - 项目技能：`scope = 'project'`，`project_id = <id>`，`scope_key = 'project:<id>'`；
  - 唯一约束建在 `UniqueConstraint("scope_key", "slug", name="uq_qa_skill_scope_slug")`，同时加 `CheckConstraint("(scope = 'global' AND project_id IS NULL) OR (scope = 'project' AND project_id IS NOT NULL)", name="ck_qa_skill_scope_project")`。双方言 100% 确定性互斥。

### 2. 用例「待复核（Stale）」检测不能侵入 `knowledge-base` 写事务
- **反方质询**：当知识库重新导入（生成新 `kb_id`、旧库变 `superseded`）或删除时，如果在 `knowledge-base` 的 `import_service` / `lifecycle_service` 里跨表 UPDATE `test_case`，既破坏「跨域不直接改表」的红线，又会在部分更新时留下脏状态。
- **根因方案**：在 `test_case.kb_links`（JSON）中持久化生成/复核时刻的**知识锚点基线快照**：
  ```json
  [
    {
      "kbId": "32位hex",
      "kbNameKey": "order-domain",
      "code": "BR-001",
      "codeKey": "BR-001",
      "title": "订单超时关闭规则",
      "contentDigest": "64位sha256"
    }
  ]
  ```
  读取或筛选用例时，通过进程内只读比对当前项目 `current_flag = '1'` 的知识库与条目 `content_digest`，零触发器、100% 确定性地计算出每条用例的 `staleStatus`（`fresh` | `stale`）与 `staleReasons`：
  - `kb_deleted`：逻辑知识库（`project_id + kbNameKey`）下已无 `current_flag = '1'` 的生效版本；
  - `entry_removed`：当前生效版本中已不存在该 `codeKey`；
  - `entry_modified`：当前生效版本中该 `codeKey` 的 `content_digest != anchor.contentDigest`。
  用户在界面点击「确认复核（解除待复核）」或编辑保存用例时，将 `kb_links` 的基线快照刷新为当前最新 `kbId` 与 `contentDigest`（已删除的锚点自动移除或由用户替换）。

### 3. 自动上下文推荐（Context Recommender）的代码路径来源真相
- **反方质询**：`repo-integration` 的 `sync_service.py` 在同步时只拉取 `repo`、`branch`、`commit` 三类快照（不拉全仓目录树，避免大仓数万文件超时）。若推荐器只查 `RepoMetadataSnapshot WHERE kind = 'tree'`，在真实云效/GitHub 仓库上会推荐出 0 条代码路径。
- **根因方案**：推荐器走**零 LLM 成本的三源确定性聚合**：
  1. **知识条目匹配 + 一跳邻居扩展**：对项目下 `current_flag = '1'` 的 `KnowledgeEntry` 按 `code` 精确提及（+100）、`title` 匹配（+40）、`tables/fields/code_paths` 匹配（+30）、`summary/body` 词项匹配（+15）打分；命中的主条目自动拉取同库 1 跳 `neighbors`（标记 `matchSource: "neighbor_1hop"`）。
  2. **代码路径三路召回**：
     - `kb_code_path`：命中知识条目自带的 `code_paths` 数组（天然带业务规则溯源 `linkedKbCodes`）；
     - `recent_repo_read`：该项目激活 `RepoBinding` 下近期成功读取过的 `RepoFileReadRecord.path`；
     - `input_path_mention`：用户输入文本中显式出现的源码路径特征（如 `src/...`、`*.py`、`*.java`、`*.ts`）。

### 4. 两阶段生成与 Skill AI 提案必须严守「唯一模型出口」
- **反方质询**：`AiGateway.complete` 与 `AiCallRecord` 强依赖非空 `session_id`（外键关联 `analysis_session`）。如果用例库或技能库绕过会话直调网关，会违反 `AiCallRecord.session_id` 外键约束或破坏审计闭环。
- **根因方案**：
  - 阶段 1（生成测试设计检查点矩阵）、阶段 2（生成结构化测试用例）、以及 Skill AI 修订提案，**全部走 `calls.complete(session_id, ...)` → `AiGateway.complete`**；
  - 若请求未传入既有 `sessionId`，服务层自动在该项目下创建一条 `entrance_key = "case-library"` 的 `AnalysisSession`，并将输入、模型输出、注入快照完整记入 `SessionEvent` 与 `AiCallRecord`；
  - 生成的测试设计计划（`TestCaseDesignPlan`）、测试用例（`TestCase`）与审批单（`ApprovalRequest`）全部保留 `session_id` 与 `call_id` 双向追溯。

### 5. `ENTRANCES` 状态切换对既有单测（`TC-051` / `TC-054` / `TC-056`）的兼容
- **反方质询**：`tests/test_entrances.py` 与 `tests/test_entrances_api.py` 原本断言全部 6 个入口均为 `planned`；`EntrancePage.tsx` 在 `status === "live"` 时需保留 `data-testid="entrance-live"` 挂载点。
- **根因方案**：
  - 当 `case-library` 在批次 D 切为 `live` 时，同步更新 `test_entrances.py`、`test_entrances_api.py`、`HomePage.test.tsx`，验证 `case-library` 为 `live` 且其余 5 个入口为 `planned`；
  - `EntrancePage.tsx` 在 `status === "live"` 的 `data-testid="entrance-live"` 容器内按 `entrance.key === "case-library"` 渲染 `<CaseLibraryWorkspace />`，既满足 `TC-056` 挂载点契约，又让 `/entrances/case-library` 真正可用。

---

## 二、数据库设计（迁移 `0009_test_case_minimal_loop`）

严格遵守双方言纪律：
- 大文本统一用 `medium_text()`（`Text().with_variant(MEDIUMTEXT, "mysql")`）；
- 自增主键（若用）绝不在 `CHECK` 中引用；本模块业务主表统一使用 `CHAR(32)`（`uuid4().hex`）作为主键，与 `knowledge_base` / `repo_integration` 一致；
- JSON 列统一用 `sa.JSON`，不建索引。

### 表 1：`qa_skill`（QA 技能主表）

| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `skill_id` | `CHAR(32)` | PK | `uuid4().hex` |
| `scope` | `VARCHAR(20)` | NOT NULL | `'global'` \| `'project'` |
| `scope_key` | `VARCHAR(64)` | NOT NULL | `'global'` 或 `'project:<project_id>'` |
| `project_id` | `BigInteger/Integer` | NULL, FK `project_context.project_id` ON DELETE CASCADE | `global` 时为 NULL |
| `slug` | `VARCHAR(100)` | NOT NULL | 技能英文标识，如 `two-stage-test-case-design` |
| `name` | `VARCHAR(200)` | NOT NULL | 技能显示名称 |
| `domain` | `VARCHAR(32)` | NOT NULL | `'test-case'` \| `'diagnosis'` \| `'regression-list'` \| `'test-report'` \| `'general'` |
| `description` | `VARCHAR(500)` | NOT NULL | 一句话用途说明 |
| `triggers` | `JSON` | NOT NULL | 触发入口或标签数组，如 `["case-library"]` |
| `content_md` | `MEDIUMTEXT/TEXT` | NOT NULL | 当前生效的 Markdown 正文 |
| `current_version` | `Integer` | NOT NULL, default 1 | 当前生效版本号（`>= 1`） |
| `is_builtin` | `Boolean` | NOT NULL, default False | 是否系统内置初版 |
| `created_at` | `DateTime` | NOT NULL | UTC |
| `updated_at` | `DateTime` | NOT NULL | UTC |

- **约束与索引**：
  - `ck_qa_skill_scope`: `scope IN ('global', 'project')`
  - `ck_qa_skill_scope_project`: `(scope = 'global' AND project_id IS NULL) OR (scope = 'project' AND project_id IS NOT NULL)`
  - `ck_qa_skill_domain`: `domain IN ('test-case', 'diagnosis', 'regression-list', 'test-report', 'general')`
  - `ck_qa_skill_version`: `current_version >= 1`
  - `uq_qa_skill_scope_slug`: `UNIQUE(scope_key, slug)`
  - `ix_qa_skill_project_domain`: `INDEX(project_id, domain)`

### 表 2：`qa_skill_version`（QA 技能不可变版本历史）

| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `version_id` | `CHAR(32)` | PK | `uuid4().hex` |
| `skill_id` | `CHAR(32)` | NOT NULL, FK `qa_skill.skill_id` ON DELETE CASCADE | 所属技能 |
| `version` | `Integer` | NOT NULL | 版本号（1, 2, ...） |
| `content_md` | `MEDIUMTEXT/TEXT` | NOT NULL | 该版本完整 Markdown 正文 |
| `change_summary` | `VARCHAR(500)` | NOT NULL | 变更说明 |
| `source_type` | `VARCHAR(32)` | NOT NULL | `'builtin'` \| `'human'` \| `'agent_proposal'` \| `'rollback'` |
| `approval_id` | `CHAR(32)` | NULL | 关联审批单 ID（若经审批产生） |
| `session_id` | `BigInteger/Integer` | NULL | 关联会话 ID |
| `created_at` | `DateTime` | NOT NULL | UTC |

- **约束与索引**：
  - `ck_qa_skill_version_num`: `version >= 1`
  - `ck_qa_skill_version_source`: `source_type IN ('builtin', 'human', 'agent_proposal', 'rollback')`
  - `uq_qa_skill_version_skill_ver`: `UNIQUE(skill_id, version)`

### 表 3：`approval_request`（轻量审批单）

| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `approval_id` | `CHAR(32)` | PK | `uuid4().hex` |
| `project_id` | `BigInteger/Integer` | NULL, FK `project_context.project_id` ON DELETE CASCADE | 关联项目（全局资产修订可为空或带发起项目） |
| `session_id` | `BigInteger/Integer` | NULL, FK `analysis_session.session_id` ON DELETE SET NULL | 发起会话 |
| `call_id` | `BigInteger/Integer` | NULL | 关联 `AiCallRecord.call_id` |
| `target_type` | `VARCHAR(32)` | NOT NULL | `'qa_skill'`（后续可扩展 `'knowledge_entry'` / `'external_write'`） |
| `target_id` | `CHAR(32)` | NOT NULL | 目标 `skill_id` |
| `target_title` | `VARCHAR(200)` | NOT NULL | 目标名称快照 |
| `action_type` | `VARCHAR(32)` | NOT NULL | `'update_skill'` \| `'create_skill'` |
| `base_version` | `Integer` | NOT NULL | 提案基于的 `current_version` |
| `before_content` | `MEDIUMTEXT/TEXT` | NOT NULL | 变更前全文快照 |
| `after_content` | `MEDIUMTEXT/TEXT` | NOT NULL | 变更后全文提案 |
| `unified_diff` | `MEDIUMTEXT/TEXT` | NOT NULL | 标准 Unified Diff 文本 |
| `rationale` | `VARCHAR(1000)` | NOT NULL | 修改理由 / 触发指令摘要 |
| `status` | `VARCHAR(20)` | NOT NULL, default `'pending'` | `'pending'` \| `'approved'` \| `'rejected'` |
| `decision_note` | `VARCHAR(500)` | NULL | 批准/驳回备注 |
| `applied_version` | `Integer` | NULL | 批准落盘后的新版本号 |
| `created_at` | `DateTime` | NOT NULL | UTC |
| `decided_at` | `DateTime` | NULL | 审批决定时间 |

- **约束与索引**：
  - `ck_approval_request_target_type`: `target_type IN ('qa_skill')`
  - `ck_approval_request_action_type`: `action_type IN ('update_skill', 'create_skill')`
  - `ck_approval_request_status`: `status IN ('pending', 'approved', 'rejected')`
  - `ck_approval_request_base_version`: `base_version >= 0`
  - `ix_approval_request_status_created`: `INDEX(status, created_at)`
  - `ix_approval_request_project_created`: `INDEX(project_id, created_at)`

### 表 4：`test_case_design_plan`（阶段 1：测试设计检查点矩阵）

| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `plan_id` | `CHAR(32)` | PK | `uuid4().hex` |
| `project_id` | `BigInteger/Integer` | NOT NULL, FK `project_context.project_id` ON DELETE CASCADE | 所属项目 |
| `session_id` | `BigInteger/Integer` | NOT NULL, FK `analysis_session.session_id` ON DELETE CASCADE | 关联分析会话 |
| `call_id` | `BigInteger/Integer` | NULL | 阶段 1 `AiCallRecord.call_id` |
| `skill_id` | `CHAR(32)` | NULL | 所用 `qa_skill.skill_id` |
| `skill_version` | `Integer` | NULL | 所用技能版本 |
| `title` | `VARCHAR(200)` | NOT NULL | 本次测试设计主题 |
| `requirement_text` | `MEDIUMTEXT/TEXT` | NOT NULL | 需求/变更输入正文 |
| `checkpoints` | `JSON` | NOT NULL | 检查点数组：`[{checkpointId, module, scenario, category, priority, rationale, kbCodes, codePaths, selected}]` |
| `kb_links` | `JSON` | NOT NULL | 注入/引用的知识条目锚点快照数组 |
| `code_paths` | `JSON` | NOT NULL | 关联代码文件路径数组 |
| `status` | `VARCHAR(20)` | NOT NULL, default `'draft'` | `'draft'` \| `'generated'` |
| `created_at` | `DateTime` | NOT NULL | UTC |
| `updated_at` | `DateTime` | NOT NULL | UTC |

- **约束与索引**：
  - `ck_test_case_design_plan_status`: `status IN ('draft', 'generated')`
  - `ix_test_case_design_plan_project_created`: `INDEX(project_id, created_at)`

### 表 5：`test_case`（阶段 2：结构化测试用例库）

| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `case_id` | `CHAR(32)` | PK | `uuid4().hex` |
| `project_id` | `BigInteger/Integer` | NOT NULL, FK `project_context.project_id` ON DELETE CASCADE | 所属项目 |
| `plan_id` | `CHAR(32)` | NULL, FK `test_case_design_plan.plan_id` ON DELETE SET NULL | 来源设计计划 ID |
| `checkpoint_id` | `VARCHAR(64)` | NULL | 来源检查点标识 |
| `session_id` | `BigInteger/Integer` | NULL, FK `analysis_session.session_id` ON DELETE SET NULL | 生成该用例的会话 ID |
| `call_id` | `BigInteger/Integer` | NULL | 阶段 2 `AiCallRecord.call_id` |
| `skill_id` | `CHAR(32)` | NULL | 所用 `qa_skill.skill_id` |
| `skill_version` | `Integer` | NULL | 所用技能版本 |
| `case_code` | `VARCHAR(64)` | NOT NULL | 项目内可读编号，如 `TC-ORD-001` |
| `module` | `VARCHAR(120)` | NOT NULL | 所属模块/特性层级（用于层级树/类脑图聚合） |
| `title` | `VARCHAR(300)` | NOT NULL | 用例标题 |
| `priority` | `VARCHAR(16)` | NOT NULL, default `'P1'` | `'P0'` \| `'P1'` \| `'P2'` \| `'P3'` |
| `case_type` | `VARCHAR(32)` | NOT NULL, default `'functional'` | `'functional'` \| `'boundary'` \| `'exception'` \| `'security'` \| `'concurrency'` |
| `preconditions` | `JSON` | NOT NULL | 前置条件字符串数组 |
| `steps` | `JSON` | NOT NULL | 步骤数组：`[{stepNo, action, expected}]` |
| ` expected_summary` | `MEDIUMTEXT/TEXT` | NOT NULL | 总体预期结果摘要 |
| `kb_links` | `JSON` | NOT NULL | 知识锚点快照：`[{kbId, kbNameKey, code, codeKey, title, contentDigest}]` |
| `code_paths` | `JSON` | NOT NULL | 关联代码路径字符串数组 |
| `created_at` | `DateTime` | NOT NULL | UTC |
| `updated_at` | `DateTime` | NOT NULL | UTC |

- **约束与索引**：
  - `ck_test_case_priority`: `priority IN ('P0', 'P1', 'P2', 'P3')`
  - `ck_test_case_type`: `case_type IN ('functional', 'boundary', 'exception', 'security', 'concurrency')`
  - `ix_test_case_project_module`: `INDEX(project_id, module)`
  - `ix_test_case_project_updated`: `INDEX(project_id, updated_at)`

---

## 三、API 端点契约（14 个端点）

所有端点挂载在 `/api/v1` 下，统一使用 `require_session` 鉴权与项目标准错误体 `error_body`。

### 1. QA 技能库（`qa-skills`）
1. `GET /api/v1/skills?projectId=<optional>&domain=<optional>`
   - 返回全局技能（自动幂等种子化内置《两阶段测试设计与用例生成规范》v0）+ 指定项目的专属技能列表。
2. `GET /api/v1/skills/{skillId}`
   - 返回技能详情 + `versions` 历史版本列表。
3. `POST /api/v1/skills`
   - 人工创建 `global` 或 `project` 作用域技能（写 v1 历史记录，`source_type="human"`）。
4. `PUT /api/v1/skills/{skillId}`
   - 人工直接编辑技能正文（版本号 `+1`，写 `qa_skill_version`，`source_type="human"`）。
5. `POST /api/v1/skills/{skillId}/proposals`
   - **对话式 AI 修订提案**：入参 `{projectId, modelId, sessionId?, instruction}`；
   - 内部通过 `calls.complete` 调用 `AiGateway.complete` 生成修订后 Markdown，计算标准 Unified Diff，落库一条 `status="pending"` 的 `ApprovalRequest` 并返回审批单详情（**绝不静默覆写 `qa_skill`**）。
6. `POST /api/v1/skills/{skillId}/rollback`
   - 一键回滚到指定历史版本号 `{targetVersion}`：生成新版本号 `current_version + 1`（`source_type="rollback"`），不抹除既有版本历史。

### 2. 审批中心轻量版（`approvals`）
7. `GET /api/v1/approvals?status=<optional>&projectId=<optional>`
   - 查询审批单列表（支持按 `pending` / `approved` / `rejected` 与 `projectId` 过滤）。
8. `GET /api/v1/approvals/{approvalId}`
   - 查看审批单详情（含 `unifiedDiff`、`beforeContent`、`afterContent`、`sessionId`、`callId`）。
9. `POST /api/v1/approvals/{approvalId}/approve`
   - 批准提案：校验状态为 `pending`；在单事务内将目标 `qa_skill` 升级为 `current_version + 1`、写入 `qa_skill_version`（`source_type="agent_proposal"`, `approval_id`），并将审批单置为 `approved` + `appliedVersion`。若审批期间目标技能已被他人修改导致冲突，可根据 `force` 或基于最新快照安全推进并记录版本。
10. `POST /api/v1/approvals/{approvalId}/reject`
    - 驳回提案：状态置为 `rejected`，记录 `decisionNote`，目标 `qa_skill` 完全不变。

### 3. 自动上下文推荐（`context-recommender`）
11. `POST /api/v1/projects/{projectId}/context-recommendations`
    - 入参：`{text: str, limit?: int = 8}`；
    - 出参：
      - `recommendedKbEntries`: `[{kbId, kbName, kbNameKey, code, title, type, summary, score, matchSource: "direct" | "neighbor_1hop", viaCode: str | null, contentDigest}]`
      - `recommendedCodePaths`: `[{path, source: "kb_code_path" | "recent_repo_read" | "input_path_mention", linkedKbCodes: [str], bindingId: str | null}]`

### 4. 用例库与两阶段测试设计（`test-case`）
12. `POST /api/v1/projects/{projectId}/test-case-designs/plan`（**阶段 1：生成测试设计检查点矩阵**）
    - 入参：`{modelId, sessionId?, skillId?, title, requirementText, kbRefs: [{kbId, entryCodes}], codePaths: [str]}`；
    - 流程：读取选定（或默认内置）`qa-skill` 的阶段 1 规范 + 注入选定 `kbRefs` 与 `codePaths` → 走 `calls.complete` 调模型 → 解析结构化检查点矩阵（含确定性兜底解析器，防止模型输出代码块包裹或格式轻微偏移）→ 落库 `TestCaseDesignPlan` 并返回。
13. `POST /api/v1/test-case-designs/{planId}/generate`（**阶段 2：按勾选检查点生成结构化用例并入库**）
    - 入参：`{modelId?, selectedCheckpointIds: [str], checkpointsOverride?: [...]}`；
    - 流程：校验至少勾选 1 个检查点 → 走 `calls.complete` 调模型生成结构化步骤与预期 → 绑定 `kb_links`（含当时的 `contentDigest` 快照）与 `code_paths` → 批量落库 `TestCase` 并返回新生成的用例列表。
14. 用例库查询、编辑、复核与导出：
    - `GET /api/v1/projects/{projectId}/test-cases?module=<optional>&priority=<optional>&staleOnly=<optional>&q=<optional>`：返回用例列表 + 动态计算的 `staleStatus`（`fresh` | `stale`）、`staleReasons` 与汇总统计（总用例数、待复核数、模块分布树）。
    - `PATCH /api/v1/test-cases/{caseId}`：编辑用例标题/步骤/优先级/关联锚点。
    - `DELETE /api/v1/test-cases/{caseId}`：删除单条用例。
    - `POST /api/v1/test-cases/{caseId}/acknowledge-stale`：确认复核，将 `kb_links` 刷新为当前最新知识库条目摘要，解除 `stale` 标红。
    - `GET /api/v1/projects/{projectId}/test-cases/export?format=csv|markdown|json`：多格式导出（含关联 KB 编号、代码路径与待复核状态）。

---

## 四、前端路由与交互落点

1. **`/extensions/skills`（`SkillsPage` 转 live）**：
   - 左栏技能列表（全局内置 + 当前项目技能，带作用域徽标与版本号）+ 右栏技能 Markdown 阅读/编辑、版本历史抽屉与一键回滚；
   - 支持「AI 协助修订（生成 Diff 提案）」对话框：输入修订指令 + 选择模型 → 生成提案并一键跳转审批中心（或当场预览 Unified Diff）。
2. **`/extensions/approvals`（`ApprovalsPage` 转 live）**：
   - 状态筛选（待审批 `pending` / 已批准 `approved` / 已驳回 `rejected`）；
   - 展开或主从查看完整 **Unified Diff**（红绿行高亮）、修改理由、关联会话/调用记录链接；
   - 「批准并落盘」与「驳回（附意见）」按钮。
3. **`/entrances/case-library`（`CaseLibraryPage` 转 live，挂载于 `data-testid="entrance-live"`）**：
   - **顶部项目切换 + 统计栏**：总用例数、P0/P1 占比、**待复核（Stale）告警胶囊**（可一键只看 Stale）、导出按钮（`CSV` / `Markdown` / `JSON`）与「+ 两阶段生成用例」主操作；
   - **两阶段生成工作抽屉/面板**：
     - 输入需求文本 → 点击「智能推荐上下文」自动勾选命中 KB 条目（含 1 跳邻居）与代码路径 + 选择 QA 技能；
     - **阶段 1**：生成「测试设计检查点矩阵」，支持勾选/全选/微调检查点；
     - **阶段 2**：确认勾选检查点 → 生成结构化用例并写入用例库；
   - **双视图切换**：
     - **表格视图**：展示编号、模块、标题、优先级、类型、**溯源锚点胶囊（KB 编号 + 代码路径）**、**Stale 待复核标红徽标 + 一键确认复核**；
     - **层级树视图（类脑图）**：按 `模块 → 场景/类型 → 用例节点` 树状展开，直观检查测试覆盖盲区。
