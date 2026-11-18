# test-verification：测试用例与覆盖确认

> **执行契约（AlonWorkflow，优先级高于下文任何“等待用户确认 / 标记 completed”的描述：本阶段做完由编排者停下来请用户确认，你不标记完成）**
>
> - 你是子代理，**不能与用户对话**。下文写“询问/展示/等待用户确认”处：把待确认内容写进产物，并在返回的 `CONFIRM` 字段列出；信息不足以继续时写 `<SPEC_DIR>/test-verification/open-questions.md`（每题附选项与默认值），返回 `STATUS: need_user`。
> - 所有产物只写 `<SPEC_DIR>/test-verification/`。知识库文档写暂存区 `<SPEC_DIR>/test-verification/docs/`：暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；用户确认本阶段后，由编排者用 skill `kb-sync` 按合并方式提升到 `docs/<MODULE>/test-verification/`，`index.md` 由 `kb-sync` 生成。不要直接写 `docs/`。
> - 本阶段必须产物以 `.aw/phases.json` 中 `test-verification` 为准（需求类型可能覆盖），`python3 .aw/aw.py check <SPEC_DIR> --phase test-verification` 可自检。
> - 阶段确认只能由用户在对话里给出，你不要替用户确认。
> - 开发尚未开始：本阶段产出测试用例、覆盖矩阵与问题清单骨架；「第 2 步 自动化测试执行」在开发完成后由 `aw verify` 跑测试、aw-qa 回填人工 TC（TC 状态先标为 `pending`）。
> - 必须另写 `tc-map.json`（与 design.md 同目录），把 technical-design/tasks.md 中每个非 `[no-test]` 任务映射到它覆盖的 TC：`{"TASK-TD-001": ["TC-001", "TC-002"]}`。所有 TC 必须在 design.md 中定义，`aw check` 会核对。
> - 自动化 TC 的结果以 `aw verify` 读到的测试报告为准：用例名里必须带 TC 编号（写法见 `.aw/test-presets.json` 的 `naming`；.NET 的 TRX 报告不带 Trait，只能写进方法名或 DisplayName）。只能人工执行的 TC，在 `## 执行结果` 表里回填。
> - `design.md` 必须含 `TC-` 编号用例与覆盖矩阵（小节标题含“覆盖”）。
> - **技术栈约定（packs）**：测试框架跟随 tech-arch 已确认的技术栈。若 `.aw/install.json` 中已安装的 pack 在 `.aw/packs/<name>/pack.json` 里为该栈提供了测试约定，则加载并遵循；否则扫描项目已有测试框架并优先沿用。pack skill 只在该 skill 确实出现在你的可用 skills 列表中时执行。未安装匹配 pack 时按通用最佳实践设计，并在产物中注明，CONFIRM 中可提示 `alonwf pack add <pack>`。

---

# test-verification：测试验证与覆盖率报告

## 职责定位

基于业务规范和技术方案生成完整测试用例，明确每个测试的具体步骤、预期结果和需要验证的问题，执行 Round-Trip 验证，确认交付物满足所有原始需求，输出需求覆盖率报告。

---

## 输入

| 来源 | 读取文件 | 必需 | 关键字段 | 缺失时 |
|------|---------|------|---------|--------|
| requirements-analysis | `<SPEC_DIR>/requirements-analysis/docs/context.md` | 是 | 用户故事摘要、AC 完整列表 | 返回 `STATUS: upstream_defect`（UPSTREAM: requirements-analysis） |
| technical-design | `<SPEC_DIR>/technical-design/docs/context.md` | 是 | 任务列表摘要、风险摘要、架构摘要 | 返回 `STATUS: upstream_defect`（UPSTREAM: tech-tasks） |
| technical-design | `<SPEC_DIR>/technical-design/design.md` 的 `## 风险登记表` | 否 | 完整风险列表（Critical / Medium） | 只按 context.md 的风险摘要设计风险用例 |
| intake | `<SPEC_DIR>/requirements-analysis/raw-requirements.md` | 是 | 原始需求原文（Round-Trip 验证用） | 改读 `docs/<MODULE>/raw-requirements.md`（只读）；仍缺失则在 CONFIRM 中注明 |
| 本体切片（只读） | `<SPEC_DIR>/ontology-slices/test-verification.md`（编排者用 skill `ontology` 生成，存在才读） | 否 | 规则原文、触发条件、影响范围、状态和状态流转 | 项目没有本体参考层（`ontology-work/views/index.json`）时不生成：跳过本体对照，并在 CONFIRM 中注明 |

**本体切片怎么用**：按切片里的规则（触发条件、影响范围）和状态流转设计边界用例，「涉及本体」里写到的规则和状态流转都要有用例覆盖（扩一跳带进来的相邻条目按需覆盖）；用例的「涉及本体」写它覆盖的编号。

---

## 输出文件

### specs 输出（可执行规格）

写入 `<SPEC_DIR>/test-verification/`：

| 文件　　　　　　　| 内容　　　　　　　　　　　　　　　　　　　　　　　　　 |
| -------------------| --------------------------------------------------------|
| `requirements.md` | 测试覆盖范围、质量目标、验收标准　　　　　　　　　　　 |
| `design.md`　　　 | 测试策略、框架选型、测试用例列表、执行结果、覆盖率报告 |
| `tasks.md`　　　　| 测试任务列表　　　　　　　　　　　　　　　　　　　　　 |

### docs 输出（知识库文档）

写入 `<SPEC_DIR>/test-verification/docs/`。暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；没有底稿时首次新建。用户确认本阶段后，由编排者用 skill `kb-sync` 按下表的合并方式提升到知识库：

| 文件 | 类型 | 内容 |
|------|------|------|
| `regression.md` | 附加 | 回归用例清单，按 TC 分节（每个 TC 一个 `## TC-NNN` 小节）；本次有值得长期保留的回归用例时写 |
| `index.md` | `kb-sync` 生成 | 文件清单、合并方式、来源 spec；由 `kb-sync` 生成到知识库，不要写 |

合并方式：`regression.md` 按章节改（按 TC）。

test-verification 无下游阶段，不生成 `context.md`。

---

## 强制执行的 Skills（按序）

> **执行原则**：步骤 1 生成测试用例后，需用户确认覆盖范围；步骤 2 在代码实现后执行；步骤 3 生成最终报告。

### 第 1 步 — test-case-generator（测试用例生成）
使用 skill `test-case-generator`
目的：将所有 AC 和 RISK 转化为结构化测试用例，覆盖正向、异常、边界三类场景。

**测试框架选型（根据架构确认结果联动，无预设默认语言）**：

1. 已有项目：扫描测试清单与配置（如 `.csproj`、`package.json`、`pytest.ini`、`go.mod`、`pyproject.toml`），优先沿用已有测试框架。
2. 已确认技术栈且已安装匹配 pack：遵循该 pack 的 `conventions/` 中测试约定（例如 dotnet pack：xUnit + Moq + WebApplicationFactory；item 前端 pack：Vitest + 对应 Testing Library + MSW）。
3. 新项目且无匹配 pack：按已确认栈给出常见选项供 CONFIRM（例如 pytest / jest / vitest / go test / xUnit），**不要预设某种语言**。

**覆盖要求**：
- 每条 AC 至少 1 条正向测试用例
- 每条含错误条件的 AC 额外 1 条异常测试用例
- 每条 🔴 Critical 风险至少 2 条测试用例（触发 + 边界）
- 每条 🟡 Medium 风险至少 1 条测试用例

**后端测试覆盖要求**（随已确认栈调整；.NET 细节见 dotnet pack）：
- 每个 API 端点至少 1 条集成测试（验证完整请求/响应链路）
- 每个领域服务/核心业务方法至少 1 条单元测试
- 认证/权限端点必须包含：未认证请求返回 401、无权限请求返回 403
- 若 flowflex pack 已安装：另按该 pack 的雪花 ID 约定验证响应中 ID 字段类型

**前端测试覆盖要求**（随已确认栈调整；有 UI 时执行）：
- 每个页面组件至少覆盖以下场景：
  - 初始加载状态（loading skeleton / spinner 是否渲染）
  - 数据正常返回后的渲染（列表条数、字段值是否正确显示）
  - 空数据状态（empty state 组件是否渲染）
  - 错误状态（API 失败时错误提示是否显示）
  - 用户交互（表单提交、按钮点击、分页切换等核心操作）
- 使用 MSW（Mock Service Worker）拦截 API 请求，不依赖真实后端
- 表单组件必须测试：必填校验、格式校验、提交成功/失败反馈
- 列表页必须测试：分页、搜索/筛选条件变化后重新请求

**每个测试用例必须包含**：
- 测试目的（验证什么问题）
- 前置条件（系统状态、数据准备）
- 具体操作步骤（原子级，可直接执行）
- 预期结果（明确可验证，不得使用"正常显示"等模糊描述）
- 测试数据示例（边界值、异常值）

输出：完整测试用例列表（TC-001, TC-002...）→ 写入 `<SPEC_DIR>/test-verification/design.md` 的 `## 测试用例列表` 小节。**只用下方模板的用例格式**（`### TC-NNN：标题` + 中文字段）：skill 输出的 Steps / Expected / Priority 等字段按模板字段改写，不要并存两种格式。

---

> ⏸️ **确认节点**：步骤 1 完成后，展示测试用例总览和覆盖矩阵，等待用户确认覆盖范围无遗漏后，才能标记阶段完成。

---

### 第 2 步 — auto-test-runner（自动化测试执行）
使用 skill `auto-test-runner`
目的：检测项目测试框架，尝试执行自动化测试，收集真实结果。

**重要**：若项目代码尚未实现（无可运行的测试文件），`## 执行结果` 表里所有 TC 标记为 `pending`，不得伪造执行结果。仅在真实测试运行后才更新为 `pass` / `fail` / `skip`。

输出：执行结果 → 更新 `<SPEC_DIR>/test-verification/design.md` 的 `## 执行结果` 小节（沿用模板的列，不另建 executionResults 表），覆盖率 → 更新 `## 需求覆盖率报告` 小节。TC 结果只写这张表（每个 TC 一行，`执行状态` 写 pass / fail / skip / pending，失败原因写进 `备注` 列），用例下不写状态字段；回填完执行 `python3 .aw/aw.py check <SPEC_DIR> --phase test-verification`，按它报告的缺漏 / 认不出逐条修正后再执行一次。

### 第 3 步 — 生成测试问题清单（ISSUE LIST）
基于测试用例，生成开发阶段需要重点关注的问题清单：

**问题分类**：
- 🔴 **安全问题**：认证绕过、SQL 注入、XSS、CSRF、越权访问
- 🟡 **数据问题**：边界值处理、空值处理、并发写入、数据一致性
- 🟢 **体验问题**：加载状态、错误提示、空状态、响应式布局
- 🔵 **性能问题**：大数据量分页、慢查询、内存泄漏

每个问题必须关联到具体的 TC 编号。

输出：测试问题清单 → 写入 `<SPEC_DIR>/test-verification/design.md` 的 `## 测试问题清单` 小节

---

## Round-Trip 验证规范

### 验证步骤

1. 读取 `<SPEC_DIR>/requirements-analysis/raw-requirements.md`，列出所有原始需求
2. 确认每条原始需求都有对应的 AC
3. 确认每条 AC 都有对应的 TC
4. 确认每条 TC 都有执行结果（pass / fail / skip / pending）
5. 统计覆盖率：有对应 TC 的需求数 / 总需求数

### 验证矩阵

```markdown
| 原始需求 | 关联 AC | 关联 TC | 执行结果 | 覆盖状态 |
|---------|---------|---------|---------|---------|
| {需求描述} | AC-001-1 | TC-001 | pass | ✅ passed |
| {需求描述} | AC-002-1 | TC-002 | pending | ⏳ pending |
| {需求描述} | - | - | - | ⚠️ not_covered |
```

---

## 执行规范

### TC 状态规则

| 状态 | 含义 |
|------|------|
| `pending` | 测试用例已定义，但代码未实现，无法执行 |
| `pass` | 测试运行并通过 |
| `fail` | 测试运行但断言失败，必须填写 failureReason |
| `skip` | 测试被跳过（手动测试或环境限制） |

**严禁**在代码未实现时将状态标记为 `pass`。

### 完成标准

- 执行全部 2 个 Skill（按顺序）
- 所有 TC 均有执行状态（`pending` 是合法状态，代表等待代码实现）
- 覆盖率报告已生成，所有需求均有对应状态
- 标记 test-verification 为 `completed`

---

## 输出文件规范

### <SPEC_DIR>/test-verification/requirements.md

```markdown
# Test Verification — Requirements

## 交付范围

### 必须交付
| 交付物 | 验收标准 |
|--------|---------|
| 测试用例列表 | 每条 AC 至少 1 条正向测试用例 |
| 执行结果报告 | 所有 TC 均有执行状态（pass/fail/skip/pending） |
| 需求覆盖率报告 | 所有需求均有对应 TC（覆盖率 = 有 TC 的需求 / 总需求） |

### Out of Scope
- 性能测试：需单独规划
- 安全渗透测试：需专项安排

## 验收标准（EARS 格式）

### AC-QA-1
WHEN 测试用例生成完成 THEN 系统 SHALL 确保每条 AC 至少对应一条正向测试用例

### AC-QA-2
WHEN 含错误条件的 AC 存在 THEN 系统 SHALL 额外生成至少一条异常测试用例

### AC-QA-3
WHEN 🔴 Critical 风险存在 THEN 系统 SHALL 生成至少两条测试用例（触发 + 边界）

### AC-QA-4
WHEN 代码实现完成后执行测试 THEN 系统 SHALL 生成需求覆盖率报告
```

### <SPEC_DIR>/test-verification/design.md

```markdown
# Test Verification — Design

## 测试策略

### 决策 1：{测试框架选型}
- **选择**：{选择了哪个测试框架}
- **理由**：{基于技术栈的依据}
- **备选方案**：{其他框架}
- **权衡**：{接受的取舍}

### 决策 2：{测试分层策略}
- **选择**：{单元/集成/E2E 的比例和边界}
- **理由**：{基于风险和成本的依据}

## 测试分层

| 层次 | 覆盖范围 | 工具 | 占比 |
|------|---------|------|------|
| 单元测试 | 纯函数、工具方法、组件渲染 | {框架} | {%} |
| 集成测试 | API 接口、数据库操作 | {框架} | {%} |
| 手动验收 | UI 交互、关键用户流程 | 手动 | {%} |

## 测试用例列表

### TC-001：{用例标题}
- **测试目的**：验证 {具体验证什么问题，如"用户使用正确凭据能否成功登录"}
- **测试类型**：单元测试 / 集成测试 / 手动验收
- **关联需求**：AC-001-1
- **涉及本体**：{本用例覆盖的规则 / 状态编号，如 BR-order-amount-limit；没有就省略本行}
- **前置条件**：
  - 系统状态：{如"数据库中存在邮箱为 test@example.com 的用户"}
  - 测试数据：`{ "email": "test@example.com", "password": "Password123!" }`
- **测试步骤**：
  1. {原子操作，如"发送 POST /api/auth/login 请求"}
  2. {原子操作，如"请求体包含 email 和 password 字段"}
  3. {原子操作，如"检查响应状态码"}
  4. {原子操作，如"检查响应体包含 token 字段"}
- **预期结果**：
  - HTTP 状态码：200
  - 响应体：`{ "success": true, "data": { "token": "<JWT string>" } }`
  - token 可解码，包含正确的 userId
- **边界/异常数据**：{如"密码长度恰好为 8 位的最小值"}

## 测试问题清单（ISSUE LIST）

> 开发阶段需要重点关注和验证的问题

### 🔴 安全问题
| Issue ID | 问题描述 | 关联 TC | 验证方式 |
|---------|---------|---------|---------|
| SEC-001 | {如"未登录用户能否访问受保护的 API 端点"} | TC-{N} | {如"发送无 Token 的请求，验证返回 401"} |
| SEC-002 | {如"用户 A 能否访问用户 B 的私有数据"} | TC-{N} | {如"使用用户 A 的 Token 请求用户 B 的资源"} |

### 🟡 数据问题
| Issue ID | 问题描述 | 关联 TC | 验证方式 |
|---------|---------|---------|---------|
| DATA-001 | {如"提交空字符串时系统如何处理"} | TC-{N} | {如"发送 email 为空字符串的请求"} |
| DATA-002 | {如"并发创建相同邮箱账号时是否有竞态条件"} | TC-{N} | {如"同时发送两个相同邮箱的注册请求"} |

### 🟢 体验问题
| Issue ID | 问题描述 | 关联 TC | 验证方式 |
|---------|---------|---------|---------|
| UX-001 | {如"列表为空时是否显示空状态提示"} | TC-{N} | {如"清空数据后访问列表页"} |
| UX-002 | {如"网络请求中是否显示 loading 状态"} | TC-{N} | {如"模拟慢网络，观察 UI 反馈"} |

### 🔵 性能问题
| Issue ID | 问题描述 | 关联 TC | 验证方式 |
|---------|---------|---------|---------|
| PERF-001 | {如"列表数据量超过 1000 条时分页是否正常"} | TC-{N} | {如"插入 1000 条测试数据后测试分页"} |

## 执行结果

> 注：以下状态在代码实现并运行测试后更新。当前为规划阶段，所有 TC 状态为 pending。

| TC ID | 用例标题 | 测试类型 | 执行状态 | 执行时间 | 备注 |
|-------|---------|---------|---------|---------|------|
| TC-001 | {标题} | 集成测试 | pending | - | 等待代码实现 |

## 需求覆盖率报告

| 原始需求 | 关联 AC | 关联 TC | 执行结果 | 覆盖状态 |
|---------|---------|---------|---------|---------|
| {需求描述} | AC-001-1 | TC-001 | pending | ⏳ pending |

**TC 覆盖率**：{N}/{Total} = {%}（所有需求均有对应 TC）
**执行通过率**：待代码实现后统计
**问题清单**：🔴 {N} 个安全问题 | 🟡 {N} 个数据问题 | 🟢 {N} 个体验问题 | 🔵 {N} 个性能问题
```

### <SPEC_DIR>/test-verification/tasks.md

```markdown
# Test Verification — Tasks

## 概览
- 总任务数：{N} | P0 任务数：{N} | 预估工时：{N} 天

## 任务列表

### TASK-TV-001：{任务名称}
- **描述**：{足够详细，执行者无需追问即可开始}
- **优先级**：P0 / P1 / P2
- **复杂度**：XS（<4h）/ S（<1d）/ M（2-3d）
- **关联需求**：{AC/TC 编号}
- **依赖**：无 / TASK-TV-{N}
- **状态**：pending
```

> 任务 ID 前缀改为 `TASK-TV-`（Test Verification）

### <SPEC_DIR>/test-verification/docs/regression.md（附加）

```markdown
# 回归用例

## TC-001：{用例标题}
- **来源 spec**：{spec 目录名}
- **步骤**：{复现步骤}
- **预期**：{预期结果}
```

按 TC 分节，只改受影响的 TC；新增回归用例追加新小节。

---

## 完整性校验

| 文件 | 位置 | 缺失时 |
|------|------|--------|
| `requirements.md` | specs | 校验失败，阶段保持 `in_progress` |
| `design.md` | specs | 校验失败，阶段保持 `in_progress` |
| `tasks.md` | specs | 校验失败，阶段保持 `in_progress` |
| `index.md` | docs | `kb-sync` 生成（不要写） |
| `regression.md` | docs | 附加，门禁不检查 |

所有必需文件均为 `generated` → 校验通过，标记 test-verification 为 `completed`。

---

## 返回格式（给编排者，≤20 行，不贴文件正文）

```
STATUS: done | need_user | upstream_defect
FILES: <本次写入/修改的相对路径>
CONFIRM: <需要用户复核的要点，≤5 条>
UPSTREAM: <upstream_defect 时写 "<phase>: <原因>"，否则留空>
```
