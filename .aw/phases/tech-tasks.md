# tech-tasks：文件结构、环境与开发任务拆解（原 technical-design 步骤 7–9）

> **执行契约（AlonWorkflow，优先级高于下文任何“等待用户确认 / 标记 completed”的描述：本阶段做完由编排者停下来请用户确认，你不标记完成）**
>
> - 你是子代理，**不能与用户对话**。下文写“询问/展示/等待用户确认”处：把待确认内容写进产物，并在返回的 `CONFIRM` 字段列出；信息不足以继续时写 `<SPEC_DIR>/technical-design/open-questions.md`（每题附选项与默认值），返回 `STATUS: need_user`。
> - 所有产物只写 `<SPEC_DIR>/technical-design/`。知识库文档写暂存区 `<SPEC_DIR>/technical-design/docs/`：暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；用户确认本阶段后，由编排者用 skill `kb-sync` 按合并方式提升到 `docs/<MODULE>/technical-design/`，`index.md` 由 `kb-sync` 生成。不要直接写 `docs/`。
> - 本阶段必须产物以 `.aw/phases.json` 中 `tech-tasks` 为准（需求类型可能覆盖），`python3 .aw/aw.py check <SPEC_DIR> --phase tech-tasks` 可自检。
> - 阶段确认只能由用户在对话里给出，你不要替用户确认。
> - **技术栈约定（packs）**：先探测项目已有技术栈（清单文件、lockfile、已有代码）。新项目或无法判断时，使用 skill `tech-stack-advisor` 给出多种选项，**不要预设某种语言**，把选项写入产物并在 `CONFIRM` 中请用户决定。然后查看 `.aw/install.json` 的 `packs` 与 `.aw/packs/<name>/pack.json`：若已安装的 pack 声明了与当前（已探测或用户选定）技术栈匹配的约定，则加载其 `conventions/` 以及列出的 skills。pack skill 只在该 skill 确实出现在你的可用 skills 列表中时执行；未安装匹配 pack 时，按通用最佳实践设计，并在 `docs/architecture-decisions.md` 注明「未安装 <pack>，未套用其约定」，在 CONFIRM 中提示用户可用 `alonwf pack add <pack>` 安装。
> - 前置：本类型走到的 tech-arch、tech-design 已确认（UI/UX 调整没有 tech-arch；Bug 修复默认没有 tech-design，`SCOPE` 的 api / data 为 yes 时才插回）。Bug 修复类型不要求 `docs/file-structure.md`；改哪些文件、每个文件改什么可选写进 `<SPEC_DIR>/technical-design/change-spec.md`（留在 spec 侧，不进知识库）。本阶段只做步骤 7–9 并补齐 technical-design 的 `requirements.md`（含 `AC-TECH`）、`tasks.md`、`docs/context.md`（`docs/index.md` 由 `kb-sync` 生成）。
> - 每个要写测试的任务下方写 `- TC: TC-NNN`（或由 test-verification 的 `tc-map.json` 映射）；不需要测试的任务（纯配置/文档/样式/脚手架）在标题行末尾加 `[no-test]`，理由写在 `[no-test]` 后面或子项 `- 免测理由：…`，并在 CONFIRM 中列出——这是向用户申请的豁免，随用户确认 tech-tasks 生效。`aw check` 会把这些任务连同理由原文列给用户（只展示，不拦截）。
> - `tasks.md` 每个任务用 `- [ ] TASK-TD-NNN：<动作>` 开头，写明具体文件路径、依赖与对应 AC；它是 aw-implementer 的唯一任务来源。

---

## 职责定位

将业务规范和交互设计转化为完整的技术实现蓝图，产出架构决策、数据库 Schema、API 规范、项目文件结构、开发环境配置和开发任务列表，让开发者拿到文档即可开始编码。

---

## 输入

| 来源 | 读取文件 | 必需 | 关键字段 | 缺失时 |
|------|---------|------|---------|--------|
| requirements-analysis | `<SPEC_DIR>/requirements-analysis/docs/context.md` | 是 | 用户故事摘要、AC 完整列表、数据实体 | 返回 `STATUS: upstream_defect`（UPSTREAM: requirements-analysis） |
| tech-arch | `<SPEC_DIR>/technical-design/design.md`、`docs/architecture-decisions.md` | 否 | 技术选型、风险、已锁定决策 | UI/UX 调整类型没有 tech-arch：沿用现有架构；其他类型缺失时返回 `STATUS: upstream_defect`（UPSTREAM: tech-arch） |
| tech-design | `<SPEC_DIR>/technical-design/change-spec.md`，以及 `<SPEC_DIR>/technical-design/docs/` 下的 `component-tree.md` / `database-schema.md` / `api-spec.md` | 至少其一 | 改动文件、组件、数据模型、端点 | 只读存在的文件；Bug 修复类型没有 tech-design 时跳过本行；其他类型全部缺失时返回 `STATUS: upstream_defect`（UPSTREAM: tech-design） |
| interaction-design | `<SPEC_DIR>/interaction-design/design.md` | 否 | Design Tokens（UI 任务引用） | 本 profile 没有交互设计阶段或 `ui=no`：UI 任务引用项目现有样式，不新增变量 |
| KB 底稿 | `<SPEC_DIR>/technical-design/docs/` 下由 `kb-sync` 带入的 `file-structure.md` / `context.md` / `dev-setup.md` / `flowchart.md` | 否 | 本模块已有的目录结构与技术摘要 | 首次建立 |
| 本体切片（只读） | `<SPEC_DIR>/ontology-slices/tech-tasks.md`（编排者用 skill `ontology` 生成，存在才读） | 否 | 实体和规则的代码文件、表名 | 项目没有本体参考层（`ontology-work/views/index.json`）时不生成：跳过本体对照，并在 CONFIRM 中注明 |
| intake（多域） | `<SPEC_DIR>/_shared/domain-map.md`，没有时读 `docs/_shared/domain-map.md`（只读） | 否 | 本模块依赖的其他域接口 | 单域，不写跨域依赖 |

**本体切片怎么用**：拆任务时把「改哪个文件」写准。任务步骤里的文件路径以切片里的代码文件为准；任务改到实体或规则时，在该任务下加一个子条目 `- **涉及本体**：ENT-…、BR-…`（不要改复选框行的格式），写代码的人会拿它去对编码包里的 `ontology.md`。

> **重要**：若 interaction-design 阶段已完成，技术方案中所有涉及 UI 的产出（包括组件树、任务描述，以及如有生成 demo.html 时）必须严格遵循 interaction-design 阶段定义的 Design Tokens 和视觉规范，不得自行定义新的样式变量或视觉风格。

---

## 输出文件

本阶段写下列文件；`design.md` 与 `docs/architecture-decisions.md` 由 tech-arch 产出，设计文档由 tech-design 产出。

| 文件 | 类型 | 内容 |
|------|------|------|
| `requirements.md` | 必需 | 技术方案范围、约束条件、验收标准（含 `AC-TECH`） |
| `tasks.md` | 必需 | 开发任务列表（`- [ ] TASK-TD-NNN：` 复选框行，按创建顺序排列，含具体操作步骤） |
| `docs/file-structure.md` | 必需 | 项目目录结构、文件职责、创建顺序（Bug 修复类型不要求） |
| `change-spec.md` | 附加 | 仅 Bug 修复且没有 tech-design 时可选：改哪些文件、每个文件改什么；写在 `<SPEC_DIR>/technical-design/change-spec.md`，留在 spec 侧，不进知识库 |
| `docs/dev-setup.md` | 附加 | 开发环境配置、依赖清单、本地启动步骤（新项目或依赖有变化时写；门禁不检查） |
| `docs/context.md` | 必需 | 精简摘要，供 test-verification 读取 |
| `index.md` | `kb-sync` 生成 | 文件清单、合并方式、来源 spec；由 `kb-sync` 生成到知识库，不要写 |

**暂存区里已有的文件是 KB 底稿，在它上面修改，不要整份重写**：`file-structure.md` 按目录改，`flowchart.md` 按章节改，`context.md` 与 `dev-setup.md` 整份更新为最新。

---

### 第 7 步 — file-structure-generator（文件结构生成）
使用 skill `file-structure-generator`
依赖：步骤 4、5、6（只读其中已产出的文件，见「输入」表）
输出：项目目录结构 + 文件职责 + 创建顺序 → 写入 `<SPEC_DIR>/technical-design/docs/file-structure.md`

### 第 8 步 — dev-environment-setup（开发环境配置）
使用 skill `dev-environment-setup`
依赖：步骤 3（技术选型已锁定）；没有 `database-schema.md` 时跳过数据库相关配置
执行条件：新项目或依赖有变化；否则不写本文件，并在 CONFIRM 中注明跳过
输出：环境配置清单 + 依赖包 + 启动步骤 → 写入 `<SPEC_DIR>/technical-design/docs/dev-setup.md`

### 第 9 步 — task-breakdown（任务拆解）
使用 skill `task-breakdown`
依赖：步骤 7（文件结构）、步骤 8（环境配置）
输出：完整开发任务列表 → 写入 `<SPEC_DIR>/technical-design/tasks.md` 的 `## 任务分组` 小节（必须用 `- [ ] TASK-TD-NNN：` 复选框行，skill 示例里的标题格式不会被 `aw check` 解析）

### 第 10 步 — agile-estimation（工时估算）
使用 skill `agile-estimation`
依赖：步骤 9（任务拆解）
输出：在已有 `- [ ] TASK-TD-NNN：` 任务下以子条目写入估算（工时、性质标签、不确定性），**不得改动复选框行格式**；汇总写入 `tasks.md` 的 `## 估点摘要` 小节。独立使用本 skill 时的完整报告模板见该 skill 的 `references/report-template.md`。

---

## 各步骤产出汇总

| 步骤 | Skill | 产出文件 | 位置 |
|------|-------|---------|------|
| 1 | tech-stack-advisor | `design.md` | specs |
| 2 | risk-analysis | `design.md` | specs |
| 3 | architecture-confirm | `architecture-decisions.md` | docs |
| 3.5 | —（阶段内步骤：前端框架检测，不是 skill） | `architecture-decisions.md`（追加框架确认记录） | docs |
| 4 | component-breakdown | `component-tree.md` | docs |
| 5 | database-design | `database-schema.md` | docs |
| 6 | api-design | `api-spec.md` | docs |
| 7 | file-structure-generator | `file-structure.md` | docs |
| 8 | dev-environment-setup | `dev-setup.md` | docs |
| 9 | task-breakdown | `tasks.md` | specs |
| 10 | agile-estimation | `tasks.md`（任务子条目 + 估点摘要） | specs |

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

## 执行规范

```
步骤 1-2：并行执行 tech-stack-advisor + risk-analysis
步骤 3：执行 architecture-confirm，展示决策清单，等待用户逐项确认
         ├── 已有项目 → 扫描清单文件、lockfile 与已有代码，确认是否沿用已有技术栈
         ├── 新项目或无法判断 → 使用 skill `tech-stack-advisor` 给出多种选项，不要预设某种语言，写入 CONFIRM
         ├── 用户确认技术栈后 → 若已安装 pack 匹配该栈，加载 `.aw/packs/<name>/conventions/` 与列出的 skills
         ├── 用户有疑问 → 提供备选方案对比，重新确认
         └── 用户确认所有决策 → 锁定架构，继续步骤 3.5

步骤 3.5：前端框架检测（仅前端项目执行）
         ├── 已有项目 → 扫描文件结构识别已有前端框架
         ├── 新项目 → 使用 skill `tech-stack-advisor` 给出多种前端选项，请用户决定
         ├── 已安装的 item / 前端 pack 与所选框架匹配 → 加载其约定与 skills
         └── 纯后端项目 → 跳过此步骤，直接进入步骤 4-6

步骤 4-6：并行执行 component-breakdown + database-design + api-design
         ├── component-breakdown 必须读取 interaction-design/design.md 中的 Design Tokens
         ├── 已安装 pack 为当前栈提供了组件 / API / 数据约定时，遵循 `.aw/packs/<name>/conventions/`
         └── 所有 UI 组件样式描述必须引用已定义的 CSS 变量，不得重新定义
步骤 6 完成后：展示组件树、数据库 Schema、API 端点总览
         ├── 用户发现遗漏 → 补充后重新确认
         └── 用户确认完整 → 继续步骤 7-8

步骤 7-8：并行执行 file-structure-generator + dev-environment-setup
步骤 9：执行 task-breakdown（依赖 7+8 的输出）

demo.html 生成规则（条件性，非必须）：
  ├── 若任务中包含需要生成 demo.html 的要求
  └── 则必须严格遵循 <SPEC_DIR>/interaction-design/docs/demo.html 和
      <SPEC_DIR>/interaction-design/design.md 中定义的 Design Tokens、
      视觉风格和组件状态规范，CSS 变量名保持一致，不得另起炉灶

最终：生成所有输出文件，标记阶段为 completed
```

---

## 输出文件规范

### <SPEC_DIR>/technical-design/requirements.md

```markdown
# Technical Design — Requirements

## 交付范围

### 必须交付
| 交付物 | 验收标准 |
|--------|---------|
| 架构设计 | 包含前端/API/服务/数据库四层划分 |
| 架构决策记录 | 每项选型含理由、备选方案、权衡说明，用户已确认 |
| 组件树 | 覆盖所有 US 页面，含 Props 接口定义 |
| 数据库 Schema | 所有表结构、索引、外键、迁移脚本 |
| API 规范 | 所有端点的请求/响应格式、错误码 |
| 文件结构 | 完整目录树，每个文件标注职责和创建顺序 |
| 开发环境配置 | 从零到本地运行的完整步骤 |
| 风险登记表 | 每个架构组件至少一条风险，Critical 风险含应急预案 |
| 任务列表 | 所有 US 分解为复杂度 ≤ M 的开发任务，含具体操作步骤 |

### Out of Scope
- 具体代码实现：属于开发阶段职责
- 测试用例编写：属于 test-verification 职责

## 验收标准（EARS 格式）

### AC-TECH-1
WHEN 架构确认完成 THEN 系统 SHALL 生成用户已确认的架构决策记录，状态为 architecture-locked

### AC-TECH-2
WHEN 数据库设计完成 THEN 系统 SHALL 为每张表提供字段类型、约束、索引和外键定义

### AC-TECH-3
WHEN API 设计完成 THEN 系统 SHALL 为每个端点提供请求/响应 Schema 和错误码列表

### AC-TECH-4
WHEN 文件结构生成完成 THEN 系统 SHALL 提供按依赖顺序排列的文件创建清单

### AC-TECH-5
WHEN 任务拆解完成 THEN 系统 SHALL 确保所有任务含具体操作步骤，复杂度不超过 M（2-3天）

### AC-TECH-6
WHEN 风险分析完成 THEN 系统 SHALL 为每个 🔴 Critical 风险提供应急预案
```

`design.md` 的模板见 tech-arch 阶段；本阶段不改写它（风险摘要从中读取）。

### <SPEC_DIR>/technical-design/tasks.md

```markdown
# Technical Design — Tasks（开发任务列表）

## 概览
- 总任务数：{N} | P0 任务数：{N} | 预估工时：{N} 天

## 任务分组

### 第一组：环境搭建（无依赖，最先执行）

- [ ] TASK-TD-001：初始化项目与开发环境
  - **描述**：按照 <SPEC_DIR>/technical-design/docs/dev-setup.md 的步骤初始化项目
  - **具体操作**：
    1. 安装 Node.js（推荐使用 nvm：`nvm install 20`）
    2. 安装包管理器：`npm install -g pnpm`
    3. 初始化项目：`{init command}`
    4. 安装依赖：`pnpm install`
    5. 复制 `.env.example` 为 `.env` 并填入实际值
    6. 启动数据库：`docker-compose up -d`
  - **优先级**：P0
  - **复杂度**：XS（<4h）
  - **依赖**：无
  - **涉及本体**：{这个任务改到的实体 / 规则编号；没有就省略本行}
  - **状态**：pending

### 第二组：数据层（依赖第一组）

- [ ] TASK-TD-002：创建数据库 Schema 与迁移
  - **描述**：按照 <SPEC_DIR>/technical-design/docs/database-schema.md 创建所有表结构
  - **具体操作**：
    1. 编写迁移文件（参考 database-schema.md）
    2. 执行迁移：`{migrate command}`
    3. 验证表结构已正确创建
  - **优先级**：P0
  - **复杂度**：S（<1d）
  - **依赖**：TASK-TD-001
  - **状态**：pending

### 第三组：API 层（依赖第二组）

- [ ] TASK-TD-00N：实现 {端点名} API
  - **描述**：按照 <SPEC_DIR>/technical-design/docs/api-spec.md 实现 {HTTP方法} {路径}
  - **涉及文件**：
    - 新建：`{具体文件路径，按 file-structure.md 与已确认技术栈}`
  - **具体操作**：
    1. 按 file-structure.md 创建上述文件
    2. 按已确认架构实现分层（若已安装 pack 提供了分层约定则遵循）
    3. 响应格式遵循 api-spec.md（若 pack 提供了包装结构或 ID 序列化约定则一并遵循）
    4. 实现标准错误响应（参考 api-spec.md）
  - **优先级**：P0 / P1
  - **复杂度**：S / M
  - **依赖**：TASK-TD-002
  - **状态**：pending

### 第四组：UI 层（依赖第三组）

- [ ] TASK-TD-00N：实现 {组件名} 组件
  - **描述**：按照 <SPEC_DIR>/technical-design/docs/component-tree.md 实现 {组件名}
  - **涉及文件**：
    - 新建：`{具体文件路径，按 file-structure.md 与已确认前端框架}`
  - **具体操作**：
    1. 按 file-structure.md 创建上述文件
    2. 定义 Props / 输入（参考 component-tree.md；ID 类型与 api-spec.md 及已加载 pack 约定一致）
    3. 实现所有状态：default / loading / success / error / empty
    4. 应用 Design Tokens（使用 `<SPEC_DIR>/interaction-design/design.md` 中定义的 CSS 变量）
    5. 连接 API（参考 api-spec.md 前端调用示例；若已安装 item pack 则遵循其客户端约定）
  - **优先级**：P0 / P1
  - **复杂度**：XS / S / M
  - **依赖**：TASK-TD-00N（对应 API 任务）
  - **状态**：pending

## 估点摘要
- 总工时：{N} 人天 | 按性质标签分布：{…} | 风险与前置依赖：{…}
```

> 任务 ID 前缀：`TASK-TD-`（Technical Design）

### <SPEC_DIR>/technical-design/docs/context.md

```markdown
# Technical Design Context → test-verification

## 模块名称
<MODULE>

## 归档路径
docs/<MODULE>/
<SPEC_DIR>/

## 技术栈摘要
| 层次 | 技术 | 版本 |
|------|------|------|

## 数据库摘要
| 表名 | 主要字段 | 关联 US |
|------|---------|---------|

## API 端点摘要
| 方法 | 路径 | 描述 | 关联 US |
|------|------|------|---------|

## 核心模块
| 模块 | 职责 | 关联 US |
|------|------|---------|

## 任务列表摘要
| Task ID | 名称 | 优先级 | 复杂度 | 关联 US |
|---------|------|--------|--------|---------|

## 风险摘要
| Risk ID | 描述 | 评分 | 关键缓解措施 |
|---------|------|------|------------|

## 关键技术约定（供 test-verification 测试设计参考）
- {约定描述}

## 跨域依赖
<!-- 多域且域地图的「跨域接口约定」里有本模块时必需（编排者核对本小节存在）；单域时删掉本小节 -->
| 依赖的域 | 接口 | 方向（调用 / 被调用 / 事件） | 说明 |
|---------|------|---------------------------|------|

## 状态
confirmed
```

---

## 完整性校验

| 文件 | 位置 | 缺失时 |
|------|------|--------|
| `requirements.md` | specs | 校验失败，阶段保持 `in_progress` |
| `tasks.md` | specs | 校验失败，阶段保持 `in_progress` |
| `file-structure.md` | docs | 校验失败，阶段保持 `in_progress`（Bug 修复类型不要求） |
| `context.md` | docs | 校验失败，阶段保持 `in_progress` |
| `index.md` | docs | `kb-sync` 生成（不要写） |
| `dev-setup.md` | docs | 附加，门禁不检查；未生成时在 CONFIRM 中注明 |
| `flowchart.md` | docs | 附加，门禁不检查；未生成时在 CONFIRM 中注明 |

所有必需文件均为 `generated` → 校验通过，标记 technical-design 为 `completed`。

---

## 返回格式（给编排者，≤20 行，不贴文件正文）

```
STATUS: done | need_user | upstream_defect
FILES: <本次写入/修改的相对路径>
CONFIRM: <需要用户复核的要点，≤5 条>
UPSTREAM: <upstream_defect 时写 "<phase>: <原因>"，否则留空>
```
