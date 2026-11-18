# tech-arch：技术选型、风险与架构决策（原 technical-design 步骤 1–3.5）

> **执行契约（AlonWorkflow，优先级高于下文任何“等待用户确认 / 标记 completed”的描述：本阶段做完由编排者停下来请用户确认，你不标记完成）**
>
> - 你是子代理，**不能与用户对话**。下文写“询问/展示/等待用户确认”处：把待确认内容写进产物，并在返回的 `CONFIRM` 字段列出；信息不足以继续时写 `<SPEC_DIR>/technical-design/open-questions.md`（每题附选项与默认值），返回 `STATUS: need_user`。
> - 所有产物只写 `<SPEC_DIR>/technical-design/`。知识库文档写暂存区 `<SPEC_DIR>/technical-design/docs/`：暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；用户确认本阶段后，由编排者用 skill `kb-sync` 按合并方式提升到 `docs/<MODULE>/technical-design/`，`index.md` 由 `kb-sync` 生成。不要直接写 `docs/`。
> - 本阶段必须产物以 `.aw/phases.json` 中 `tech-arch` 为准（需求类型可能覆盖），`python3 .aw/aw.py check <SPEC_DIR> --phase tech-arch` 可自检。
> - 阶段确认只能由用户在对话里给出，你不要替用户确认。
> - **技术栈约定（packs）**：先探测项目已有技术栈（清单文件、lockfile、已有代码）。新项目或无法判断时，使用 skill `tech-stack-advisor` 给出多种选项，**不要预设某种语言**，把选项写入产物并在 `CONFIRM` 中请用户决定。然后查看 `.aw/install.json` 的 `packs` 与 `.aw/packs/<name>/pack.json`：若已安装的 pack 声明了与当前（已探测或用户选定）技术栈匹配的约定，则加载其 `conventions/` 以及列出的 skills。pack skill 只在该 skill 确实出现在你的可用 skills 列表中时执行；未安装匹配 pack 时，按通用最佳实践设计，并在 `docs/architecture-decisions.md` 注明「未安装 <pack>，未套用其约定」，在 CONFIRM 中提示用户可用 `alonwf pack add <pack>` 安装。
> - 本阶段只做步骤 1–3.5。产物：`design.md`（含 `## 技术选型`、`## 风险登记表`）与 `docs/architecture-decisions.md`（每条决策以 `ADR-` 编号）。
> - 发现需求层根本性缺陷 → 返回 `STATUS: upstream_defect`，`UPSTREAM: requirements-analysis: <原因>`。

---

## 职责定位

将业务规范和交互设计转化为完整的技术实现蓝图，产出架构决策、数据库 Schema、API 规范、项目文件结构、开发环境配置和开发任务列表，让开发者拿到文档即可开始编码。

---

## 输入

| 来源 | 读取文件 | 必需 | 关键字段 | 缺失时 |
|------|---------|------|---------|--------|
| requirements-analysis | `<SPEC_DIR>/requirements-analysis/docs/context.md` | 是 | 用户故事摘要、AC 完整列表、数据实体 | 返回 `STATUS: upstream_defect`（UPSTREAM: requirements-analysis） |
| interaction-design | `<SPEC_DIR>/interaction-design/docs/context.md` | 否 | 组件清单、Design Tokens 摘要、关键交互约定 | 本 profile 没有交互设计阶段（重构 / Bug 修复）或 `ui=no`：跳过 UI 相关输入，以项目现有界面代码为准，并在 CONFIRM 中注明 |
| interaction-design（样式规范） | `<SPEC_DIR>/interaction-design/design.md` | 否 | Design Tokens 完整定义、视觉风格、组件状态规范 | 同上 |
| KB 底稿 | `<SPEC_DIR>/technical-design/docs/architecture-decisions.md`（暂存区 `docs/` 下由 `kb-sync` 带入的文件） | 否 | 本模块已有的 ADR | 首次建立 |
| 本体切片（只读） | `<SPEC_DIR>/ontology-slices/tech-arch.md`（编排者用 skill `ontology` 生成，存在才读） | 否 | 业务对象所属模块、对象之间的关联、流程的上下游 | 项目没有本体参考层（`ontology-work/views/index.json`）时不生成：跳过本体对照，并在 CONFIRM 中注明 |

**本体切片怎么用**：架构不越过已有边界。模块划分和依赖方向沿用切片里的「所属模块」和对象关联；要新增模块或跨模块依赖时，在 `design.md` 的 `## 系统架构` 写明理由。用到了需求分析没写过的编号时，在 `## 系统架构` 小节末尾写一行 `涉及本体：…`。

> **重要**：若 interaction-design 阶段已完成，技术方案中所有涉及 UI 的产出（包括组件树、任务描述，以及如有生成 demo.html 时）必须严格遵循 interaction-design 阶段定义的 Design Tokens 和视觉规范，不得自行定义新的样式变量或视觉风格。

---

## 输出文件

本阶段只写下列两个文件；`technical-design/` 下的其他文件由 tech-design、tech-tasks 产出。

| 文件 | 类型 | 内容 |
|------|------|------|
| `design.md` | 必需 | `## 技术选型`、`## 系统架构`、`## 风险登记表`、`## 扩展计划`（模板见下方「输出文件规范」） |
| `docs/architecture-decisions.md` | 必需 | 架构决策记录，每条决策以 `ADR-NNN` 编号，用户确认后锁定 |

**暂存区里已有的文件是 KB 底稿，在它上面修改，不要整份重写。** `architecture-decisions.md` 只追加：已有 ADR 一个字都不改，新 ADR 编号顺延；推翻旧决策时写一条新 ADR 并注明 `取代：ADR-NNN`，旧条目原文不动。`kb-sync` 提升时逐条比对，旧条目被改或被删会被拒绝。

---

## 强制执行的 Skills（按序）

> **执行原则**：步骤 1-2 可并行；步骤 3 需用户确认后才能继续；步骤 4-6 可并行；步骤 7-8 可并行；步骤 9 最后执行。

### 第 1 步 — tech-stack-advisor（技术选型）
使用 skill `tech-stack-advisor`
输出：技术选型表格 → 写入 `<SPEC_DIR>/technical-design/design.md` 的 `## 技术选型` 小节（skill 输出的 Summary 表放入「技术栈总览」，Detailed Decisions 放入「详细决策」）

### 第 2 步 — risk-analysis（风险分析）
使用 skill `risk-analysis`
输出：风险登记表（含 🔴/🟡/🟢 评分）→ 写入 `<SPEC_DIR>/technical-design/design.md` 的 `## 风险登记表` 小节（skill 输出的 Risk Register 表与 Risk Detail 放在该小节下）

### 第 3 步 — architecture-confirm（架构确认）⚠️ 需用户确认
使用 skill `architecture-confirm`

**执行顺序**：
1. 先扫描项目文件结构，检测已有架构（前端框架、后端框架、数据库、ORM、部署方式等）
2. 将扫描结果与 `design.md` 中的技术选型草稿合并，生成完整确认清单
3. 逐项与用户确认：已有架构确认是否沿用，待定项目等待用户选择
4. 所有项目确认完毕后锁定架构

**后端技术栈（无预设默认语言）**：

**检测与确认逻辑**：

```
已有项目？
  ├── 是 → 扫描清单文件、lockfile 与已有代码（如 .csproj / go.mod / pyproject.toml / package.json / pom.xml / Cargo.toml）
  │         ├── 能判断技术栈 → 写入确认清单（标注“已有”），请用户确认是否沿用
  │         └── 无法判断 → 使用 skill `tech-stack-advisor` 给出多种选项，写入 CONFIRM，请用户决定
  └── 新项目 → 使用 skill `tech-stack-advisor` 给出多种选项（至少包含两种后端与两种前端候选，例如 .NET / Node.js / Python / Go，React / Vue / 其他），
               **不要预设某种语言**，写入产物并在 CONFIRM 中请用户决定
```

用户确认（或沿用已有）技术栈之后：查看 `.aw/install.json` 与 `.aw/packs/<name>/pack.json`。若已安装 pack 的 `stacks` 与该栈匹配，加载其 `conventions/` 和列出的 skills（例如 dotnet pack 提供 .NET 确认清单，并把 skill `csharp` 当作语言陷阱参考）。未安装匹配 pack 时按通用最佳实践设计，并在 ADR 与 CONFIRM 中注明，可提示 `alonwf pack add <pack>`。

输出：架构决策记录（含项目扫描摘要 + 前后端每项 ADR）→ 写入 `<SPEC_DIR>/technical-design/docs/architecture-decisions.md` 的 `## 项目扫描摘要`、`## 已确认决策` 与 `## 约束条件` 小节（整份格式见下方模板）
**重要**：前端、后端、数据库、部署每一项都必须与用户逐项确认，不得跳过或自行假设。

---

> ⏸️ **确认节点**：步骤 3 完成后，展示架构决策清单，等待用户确认所有选型无误后，才能继续步骤 3.5 和步骤 4-6。

---

### 第 3.5 步 — 前端框架检测（本阶段内的步骤，不是 skill）⚠️ 仅前端项目执行

> **执行条件**：需求中包含前端 UI 开发内容时执行；纯后端/API 项目跳过此步骤。

**检测逻辑**：

```
已有项目？
  ├── 是 → 扫描项目文件结构（package.json 依赖、.tsx / .vue / 其他前端特征、构建配置）
  │         ├── 能判断前端框架 → 写入确认清单（标注“已有”），请用户确认是否沿用
  │         └── 无法判断 → 使用 skill `tech-stack-advisor` 给出多种前端选项，写入 CONFIRM
  └── 新项目 → 使用 skill `tech-stack-advisor` 给出多种前端选项，**不要只提供 React / Vue**，请用户决定
```

用户确认前端框架之后：若已安装的 pack（如 react-item / vue-item）声明了该栈的约定，则加载其 `conventions/` 与列出的 skills（只在该 skill 确实出现在你的可用 skills 列表中时执行）。未安装匹配 pack 时，按该框架的通用最佳实践设计，不要套用某个项目专属的客户端封装或源码路径约定，并在 ADR 与 CONFIRM 中注明。

输出：框架确认记录 → 追加写入 `<SPEC_DIR>/technical-design/docs/architecture-decisions.md` 的 `## 已确认决策` 小节（续用 `ADR-NNN` 编号）

---


## 输出文件规范

### <SPEC_DIR>/technical-design/design.md

```markdown
# Technical Design — Design

## 技术选型

### 技术栈总览
| 层次 | 选型 | 版本 | 来源（已有 / 新增） | 理由摘要 |
|------|------|------|------------------|---------|

### 详细决策

#### 决策 1：{技术选型标题}
- **选择**：{选择了哪个技术/框架}
- **理由**：{依据}
- **备选方案**：{其他技术}
- **权衡**：{接受的取舍}

## 系统架构

### 分层说明
| 层次 | 职责 | 技术 |
|------|------|------|

### 模块划分
| 模块 | 职责 | 关联 US |
|------|------|---------|

## 风险登记表

| ID | 风险 | 类别 | 影响 | 概率 | 评分 | 缓解措施 |
|----|------|------|------|------|------|---------|

### Critical 风险应急预案
- **RISK-001**：{若缓解措施失败，执行的应急方案}

## 扩展计划
| 阶段 | 用户规模 | 架构变化 |
|------|---------|---------|
```

沿用现有技术栈时（重构 / Bug 修复），`## 技术选型` 写“沿用现有技术栈”并只列受影响的层；`## 风险登记表` 至少列一条回归风险；`## 扩展计划` 可写“不变”。Bug 修复类型的门禁不要求 `## 技术选型`，只要求风险登记表里写明「回归风险」（至少一条）。UI/UX 调整类型没有本阶段。

### <SPEC_DIR>/technical-design/docs/architecture-decisions.md

```markdown
# Architecture Decisions Record (ADR)

## 锁定时间
{YYYY-MM-DD HH:mm}

## 项目扫描摘要
| 层次 | 检测结果 | 置信度 |
|------|---------|--------|

## 已确认决策

### ADR-001：{决策项，如后端框架}
- **决策**：{选择了什么}
- **来源**：{已有 / 新增}
- **状态**：✅ 已锁定
- **理由**：{依据}
- **影响**：{对开发的影响}
- **取代**：{被本条取代的旧 ADR 编号，如 ADR-003；没有写“无”}

## 约束条件
- {不可更改的约束}

## 状态
architecture-locked
```

---

## 根本性缺陷检测

发现以下情况时，必须阻断并回退到 requirements-analysis：

| 类型 | 示例 |
|------|------|
| 业务逻辑矛盾 | 两个 US 的 AC 相互冲突 |
| 关键流程缺失 | 核心业务流程没有错误处理路径 |
| 数据一致性不可能 | 业务规则要求两个互斥的数据状态同时存在 |
| 权限模型不可实现 | 权限设计按规格无法实现 |

---

## 返回格式（给编排者，≤20 行，不贴文件正文）

```
STATUS: done | need_user | upstream_defect
FILES: <本次写入/修改的相对路径>
CONFIRM: <需要用户复核的要点，≤5 条>
UPSTREAM: <upstream_defect 时写 "<phase>: <原因>"，否则留空>
```
