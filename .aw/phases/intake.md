# intake：上下文扫描与需求分类（原步骤 0 + RA 第零步）

> **执行契约（AlonWorkflow，优先级高于下文任何“等待用户确认 / 标记 completed”的描述：本阶段做完由编排者停下来请用户确认，你不标记完成）**
>
> - 你是子代理，**不能与用户对话**。下文写“询问/展示/等待用户确认”处：把待确认内容写进产物，并在返回的 `CONFIRM` 字段列出；信息不足以继续时写 `<SPEC_DIR>/requirements-analysis/open-questions.md`（每题附选项与默认值），返回 `STATUS: need_user`。
> - 所有产物只写 `<SPEC_DIR>/requirements-analysis/`。知识库文档写 `<SPEC_DIR>/requirements-analysis/docs/`，用户确认后由编排者用 skill `kb-sync` 同步到 `docs/<MODULE>/requirements-analysis/`。不要直接写 `docs/`。
> - 多域时域地图写暂存区 `<SPEC_DIR>/_shared/domain-map.md`：已有域地图时由 `kb-sync` 带入暂存区作为底稿，在它上面修改；用户确认 intake 后由 `kb-sync` 提升到 `docs/_shared/domain-map.md`。
> - 本阶段必须产物以 `.aw/phases.json` 中 `intake` 为准（需求类型可能覆盖），`python3 .aw/aw.py check <SPEC_DIR> --phase intake` 可自检。
> - 阶段确认只能由用户在对话里给出，你不要替用户确认。

---

## 第零步：需求分类（必须最先执行）

收到用户需求后，**在做任何分析之前**，先判断需求类型并告知用户将走哪条路径：

### 需求类型识别

| 类型 | 判断依据 | 示例 |
|------|---------|------|
| 🆕 **新产品** | 全新项目，无已有代码库 | "我想做一个任务管理 App" |
| ➕ **功能新增** | 已有项目，增加新功能模块 | "在现有系统里加一个消息通知功能" |
| 🔧 **重构** | 已有功能，改变实现方式 | "把现有的 REST API 改成 GraphQL" |
| 🐛 **Bug 修复** | 已有功能出现异常行为 | "用户登录后跳转到错误页面" |
| 🎨 **UI/UX 调整** | 只涉及界面和交互变更 | "重新设计首页布局" |

### 各类型的阶段与门禁

类型决定走哪些阶段，以及各阶段必交哪些产物。阶段列表在 `aw new` 时按类型写进 `<SPEC_DIR>/spec.json`；intake 判定的类型或 `SCOPE` 和它不同时，由编排者执行 `python3 .aw/aw.py retype <SPEC_DIR> --type <类型> [--add <阶段>] [--drop <阶段>]`。下表就是 `.aw/phases.json` 的 `types`，两者不一致时以 phases.json 为准（`python3 .aw/aw.py check <SPEC_DIR> --phase <阶段>` 可自检）。

| 类型 | profile | 走的阶段 | 跳过的阶段 | 门禁差异 |
|---|---|---|---|---|
| 🆕 新产品 / ➕ 功能新增 | `feature` | 全部 7 个阶段 | 无 | 没有界面时（`SCOPE` ui=no）编排者 `retype --drop interaction-design` |
| 🔧 重构 | `refactor` | intake → 需求分析 → tech-arch → tech-design → tech-tasks → 测试验证 | `interaction-design` | 涉及界面变更时写 `SCOPE` 的 ui=yes，编排者 `retype --add interaction-design` |
| 🐛 Bug 修复 | `bugfix` | intake → 需求分析 → tech-arch → tech-tasks → 测试验证 | `interaction-design`、`tech-design` | 需求分析：不要求 `flowchart.md`，改为必交 `bug-flowchart.md`（错误行为、正确行为两张 mermaid 图，留在 spec 侧）；tech-arch：`design.md` 不要求技术选型，只要求风险登记表里至少一条回归风险；tech-tasks：不要求 `file-structure.md`，`change-spec.md` 可选；`SCOPE` 里 api=yes 或 data=yes 时编排者 `retype --add tech-design`，至少要有 `api-spec.md` / `database-schema.md` / `change-spec.md` 之一 |
| 🎨 UI/UX 调整 | `ui` | intake → 需求分析 → 交互设计 → tech-design → tech-tasks → 测试验证 | `tech-arch` | tech-design：只要求 `component-tree.md`（不要求 change-spec；没有 tech-arch，所以没有 ADR）；`SCOPE` 的 api / data 为 yes 时另要求对应文档 |

### 需求类型 × 变更性质

需求类型决定走哪些阶段（上表）；变更性质决定知识库底稿怎么改。两者分开判断，再按下表组合：

| 需求类型 | 常见的变更性质 | 少见组合怎么处理 |
|---|---|---|
| 🆕 新产品 | 🆕 全新模块 | 已有代码库：改判为 ➕ 功能新增 |
| ➕ 功能新增 | ➕ 功能扩展、🆕 全新模块 | 🔄 重大重构：仍按功能新增走阶段；tech-arch 推翻旧决策时写新 ADR 并注明取代哪一条 |
| 🔧 重构 | 🔄 重大重构、🔧 局部修改 | 🆕 全新模块：没有可重构的东西，改判为 🆕 新产品或 ➕ 功能新增 |
| 🐛 Bug 修复 | 🔧 局部修改 | 🔄 重大重构：修复需要改架构时改判为 🔧 重构（Bug 修复的 tech-arch 只确认沿用现有架构） |
| 🎨 UI/UX 调整 | 🔧 局部修改、➕ 功能扩展 | 要改接口或数据：改判为 ➕ 功能新增（UI/UX 调整没有 tech-arch） |

| 变更性质 | 知识库底稿怎么改 |
|---|---|
| 🆕 全新模块 | 没有底稿，首次建立 |
| ➕ 功能扩展 | 在底稿上追加新内容 |
| 🔧 局部修改 | 只改底稿里对应的章节 |
| 🔄 重大重构 | 通常仍在底稿上改；只有架构完全推翻时才整体重写（ADR 仍只追加，新条目注明取代） |

### 各类型的 skill 裁剪

#### 🆕 新产品（全流程）
```
需求分析（全部 7 步）→ 交互设计 → 技术方案（选型/架构、设计、任务三个确认点）→ 测试验证
```
执行所有 Skills：用户研究综合（skill `market-research`）→ `competitor-analysis` → `priority-matrix` → `feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator`

#### ➕ 功能新增（跳过市场/竞品）
```
需求分析（步骤 3-7）→ 交互设计 → 技术方案 → 测试验证
```
跳过：`market-research`、`competitor-analysis`
执行：`priority-matrix` → `feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator`

#### 🔧 重构（跳过市场/竞品/优先级；涉及界面时才有交互设计）
```
需求分析（步骤 4-7）→（SCOPE ui=yes 时）交互设计 → 技术方案 → 测试验证
```
跳过：`market-research`、`competitor-analysis`、`priority-matrix`
执行：`feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator`
需求分析 `design.md` 不做市场/竞品/优先级分析，写 `## 需求类型`、`## 商业目标`（重构目标）与 `## 核心决策`。
重构涉及界面变更时，在 intake.md 的 `SCOPE` 行写 `ui=yes`：编排者执行 `aw.py retype <SPEC_DIR> --add interaction-design`，不用换类型。

#### 🐛 Bug 修复（最精简路径）
```
需求分析（步骤 5-6 + 错误 / 正确行为对比图）→ 技术方案（tech-arch 确认沿用现有架构 → tech-tasks 拆任务）→ 测试验证
```
跳过：`market-research`、`competitor-analysis`、`priority-matrix`、`feature-spec`、`flowchart-generator`、`tech-stack-advisor`、`risk-analysis`、`file-structure-generator`
执行：`requirements-clarify` → `user-story-writer` → `architecture-confirm` → `task-breakdown` → `test-case-generator` → `auto-test-runner`
- 需求分析：手写两张 mermaid 对比图到 `<SPEC_DIR>/requirements-analysis/bug-flowchart.md`——**错误行为**（bug 触发路径和异常结果）与**正确行为**（修复后的正确流程）。它们留在 spec 侧，不进知识库；只有正确流程本身变了，才在知识库流程图的底稿上改对应 US 的图。
- tech-arch：用 `architecture-confirm` 记录“沿用现有架构”的 ADR；`design.md` 不写技术选型，`## 风险登记表` 至少写一条回归风险（门禁检查「回归风险」）。
- tech-tasks：不写文件结构；改哪些文件、每个文件改什么写进 `<SPEC_DIR>/technical-design/change-spec.md`（可选，留在 spec 侧）。
- 修复涉及接口或数据模型时，`SCOPE` 写 `api=yes` / `data=yes`：编排者执行 `aw.py retype <SPEC_DIR> --add tech-design`，只要求对应的接口 / 数据文档。

#### 🎨 UI/UX 调整（跳过市场/竞品，直接交互设计，没有 tech-arch）
```
需求分析（步骤 4-7）→ 交互设计（全部）→ 技术方案（组件 + 任务）→ 测试验证
```
跳过：`market-research`、`competitor-analysis`、`priority-matrix`、`tech-stack-advisor`、`risk-analysis`、`architecture-confirm`、`database-design`、`api-design`
执行：`feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator` → `component-breakdown` → `file-structure-generator` → `task-breakdown`
需求分析 `design.md` 不做市场/竞品/优先级分析，写 `## 需求类型`、`## 商业目标` 与 `## 核心决策`。沿用现有前端栈，不记录 ADR。

### 分类后的告知格式

> 需求类型识别为：**{类型}**
>
> 本次将执行以下路径：
> - ✅ 需求分析：{执行的 Skills}
> - {✅/⏭️} 交互设计：{执行 / 跳过，原因}
> - ✅ 技术方案：{执行的 Skills}
> - ✅ 测试验证
>
> 如果分类有误，请告知，我会调整路径。

---

## 首要步骤：上下文扫描与归档路径确认

在开始任何分析之前，**必须**先执行以下步骤：

**步骤 0-1：扫描已有文件**
- 先读 `kb-sync` 生成的 `<SPEC_DIR>/requirements-analysis/kb-inventory.md`（没有就自己列）：本模块知识库、共享知识库 `docs/_shared/`（域地图、本体流程层）与本体参考层 `ontology-work/views/`（只读）的文件清单；有参考层时 skill `ontology` 还会写 `<SPEC_DIR>/ontology-slices/intake.md`（业务对象摘要）
- 查看 `docs/` 目录，寻找与当前需求相关的模块文件夹
- 查看 `specs/` 目录，寻找历史 spec 记录（格式：`<MODULE>_{timestamp}/`）
- 查看相关代码文件（如有）

**步骤 0-2：确认模块名称**
询问用户模块名称（如未提供），确定：
- `<MODULE>`：模块名，kebab-case（如 `user-auth`）
- 本次 spec 路径：`<SPEC_DIR>/requirements-analysis/`
- 知识库路径：`docs/<MODULE>/requirements-analysis/`（只读参考；各阶段产物在用户确认后由 `kb-sync` 同步过去）

**步骤 0-3：输出扫描结论**
> - 相关模块：`<MODULE>`（已存在 / 不存在）
> - 历史 spec：找到 N 条 / 无记录
> - 已有 docs：列出相关文件 / 无
> - 变更性质：{🆕 全新模块 / ➕ 功能扩展 / 🔧 局部修改 / 🔄 重大重构}
> - 知识库：{已有，将增量更新 / 首次建立}（用户确认后由 `kb-sync` 同步）

确定路径后，把用户原始需求**原文**（不改写、不摘要）写入 `<SPEC_DIR>/requirements-analysis/raw-requirements.md`。不要写 `docs/<MODULE>/raw-requirements.md`：用户确认 intake 后由 `kb-sync` 把本文件追加过去（保留历史记录）。

## intake 产物（写入 `<SPEC_DIR>/requirements-analysis/`）

| 文件 | 内容 |
|---|---|
| `raw-requirements.md` | 用户原始需求**原文**（用户确认 intake 后由 `kb-sync` 追加到 `docs/<MODULE>/raw-requirements.md`） |
| `intake.md` | 见下方模板；另含上下文扫描结论、域复杂度评估（触发条件见 skill `domain-splitter`；多域时列出建议拆分，每个域由用户单独发起一次 aw-start） |
| `kb-inventory.md` | `kb-sync` 生成，知识库文件清单；只读，不要写 |
| `<SPEC_DIR>/_shared/domain-map.md` | 多域时必需：用 skill `domain-splitter` 写域地图（`## 域清单`、`## 域间依赖`、`## 跨域接口约定`）；用户确认后由 `kb-sync` 提升到共享知识库 |

### <SPEC_DIR>/requirements-analysis/intake.md

```markdown
# Intake

## 需求类型
{🆕 新产品 / ➕ 功能新增 / 🔧 重构 / 🐛 Bug 修复 / 🎨 UI/UX 调整}

## 变更性质
{🆕 全新模块 / ➕ 功能扩展 / 🔧 局部修改 / 🔄 重大重构}

## 执行路径
- 需求分析：{执行的 Skills}
- 交互设计：{执行 / 跳过，原因}
- 技术方案：{执行的 Skills}
- 测试验证：{执行的 Skills}

## 上下文扫描
{相关模块、历史 spec、已有 docs}

## 类型与变更性质组合
{按「需求类型 × 变更性质」表判定；少见组合写明怎么处理}

## 域复杂度评估
多域：{是 / 否}
{单域 / 多域的理由；多域时的建议拆分，域地图写在 `<SPEC_DIR>/_shared/domain-map.md`}

SCOPE: ui=<yes|no> api=<yes|no> data=<yes|no>
```

需求类型与 `--type` 的对应：🆕 新产品 / ➕ 功能新增=`feature`、🔧 重构=`refactor`、🐛 Bug 修复=`bugfix`、🎨 UI/UX 调整=`ui`。
若你判定的类型与 `<SPEC_DIR>/spec.json` 的 `type` 不同，在返回的 CONFIRM 中写 `PROFILE: <建议值>`，由编排者执行 `aw.py retype`。

在 `intake.md` 末尾另起一行声明改动范围，编排者据此用 `retype` 增减阶段（不声明则按类型的默认阶段）：

```
SCOPE: ui=<yes|no> api=<yes|no> data=<yes|no>
```

- `ui`：是否有界面。`no` 时 interaction-design 的 `design.md` 写「输出契约」（CLI 行为、文案、退出码），不要求线框图与 Design Tokens。🔧 重构写 `yes` 时，编排者加回交互设计阶段；功能新增写 `no` 时，编排者去掉交互设计阶段。
- `api`：是否新增或修改对外接口。`yes` 时 tech-design 必须产出 `docs/api-spec.md`。🐛 Bug 修复写 `yes` 时，编排者加回 tech-design。
- `data`：是否改动数据模型。`yes` 时 tech-design 必须产出 `docs/database-schema.md`。🐛 Bug 修复写 `yes` 时，编排者加回 tech-design。

三个键都要写，取值只能是 `yes` 或 `no`。拿不准时写 `yes`。

「域复杂度评估」小节里的 `多域：是 / 否` 二选一写死。写 `多域：是` 时，必须写 `<SPEC_DIR>/_shared/domain-map.md` 且含 `## 域清单`；「跨域接口约定」表的调用方 / 被调用方写各域的 module-name，后续各域的技术方案据此检查跨域标记。`## 执行进度` 小节由 `kb-sync` 在每个域关闭时维护，不要手写。

---

## 返回格式（给编排者，≤20 行，不贴文件正文）

```
STATUS: done | need_user | upstream_defect
FILES: <本次写入/修改的相对路径>
CONFIRM: <需要用户复核的要点，≤5 条>
UPSTREAM: <upstream_defect 时写 "<phase>: <原因>"，否则留空>
```
