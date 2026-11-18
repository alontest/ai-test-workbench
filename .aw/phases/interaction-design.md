# interaction-design：交互设计与视觉规范

> **执行契约（AlonWorkflow，优先级高于下文任何“等待用户确认 / 标记 completed”的描述：本阶段做完由编排者停下来请用户确认，你不标记完成）**
>
> - 你是子代理，**不能与用户对话**。下文写“询问/展示/等待用户确认”处：把待确认内容写进产物，并在返回的 `CONFIRM` 字段列出；信息不足以继续时写 `<SPEC_DIR>/interaction-design/open-questions.md`（每题附选项与默认值），返回 `STATUS: need_user`。
> - 所有产物只写 `<SPEC_DIR>/interaction-design/`。知识库文档写暂存区 `<SPEC_DIR>/interaction-design/docs/`：暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；用户确认本阶段后，由编排者用 skill `kb-sync` 按合并方式提升到 `docs/<MODULE>/interaction-design/`，`index.md` 由 `kb-sync` 生成。不要直接写 `docs/`。
> - 本阶段必须产物以 `.aw/phases.json` 中 `interaction-design` 为准（需求类型可能覆盖），`python3 .aw/aw.py check <SPEC_DIR> --phase interaction-design` 可自检。
> - 阶段确认只能由用户在对话里给出，你不要替用户确认。

---

# interaction-design：交互设计与视觉规范

## 职责定位

将业务规范转化为可视化交互设计方案，产出线框图、用户流程图、Design Tokens 和组件清单，为开发提供明确的界面实现参考。

---

## 输入

| 来源 | 读取文件 | 必需 | 关键字段 | 缺失时 |
|------|---------|------|---------|--------|
| requirements-analysis | `<SPEC_DIR>/requirements-analysis/docs/context.md` | 是 | 用户故事摘要、AC 完整列表、功能范围、商业目标 | 返回 `STATUS: upstream_defect`（UPSTREAM: requirements-analysis） |
| interaction-design（已有设计系统） | `<SPEC_DIR>/interaction-design/docs/context.md`、`design.md` | 否 | 已有 Design Tokens | 视为全新模块，执行第 1 步 |
| 本体切片（只读） | `<SPEC_DIR>/ontology-slices/interaction-design.md`（编排者用 skill `ontology` 生成，存在才读） | 否 | 实体的状态、状态流转、流程的触发条件 | 项目没有本体参考层（`ontology-work/views/index.json`）时不生成：跳过本体对照，并在 CONFIRM 中注明 |

**本体切片怎么用**：界面上的状态名、按钮文案要和业务状态对得上。页面和组件的状态用切片里的状态中文名，组件清单的「状态列表」写状态编号（如 `ST-…`）；切片里没有的状态先在 UXAMB 里问清楚，不要自己起名。用到了需求分析没写过的编号时，在 `design.md` 的 `## 组件清单` 小节末尾写一行 `涉及本体：…`。

---

## 输出文件

### specs 输出（可执行规格）

写入 `<SPEC_DIR>/interaction-design/`：

| 文件　　　　　　　| 内容　　　　　　　　　　　　　　　|
| -------------------| -----------------------------------|
| `requirements.md` | 交互设计需求、覆盖范围、验收标准　|
| `design.md`　　　 | 有界面：线框图 + Design Tokens + 组件架构；intake 声明 `ui=no` 时改为「输出契约」（命令、输出、退出码、错误文案），不画线框图、不定义视觉 token |
| `tasks.md`　　　　| 交互设计阶段任务列表　　　　　　　|

### docs 输出（知识库文档）

写入 `<SPEC_DIR>/interaction-design/docs/`。暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；没有底稿时首次新建。用户确认本阶段后，由编排者用 skill `kb-sync` 按下表的合并方式提升到知识库：

| 文件　　　　　 | 类型 | 内容　　　　　　　　　　　　　　　　　　　　 |
| ----------------| ------| ----------------------------------------------|
| `context.md`　 | 必需 | 精简摘要，供 technical-design 读取　　　　　 |
| `flowchart.md` | 附加 | 每个关键页面的用户操作流程图（门禁不检查） |
| `demo.html`　　| 附加 | 可交互 HTML 原型，覆盖所有 US 页面和 UI 状态（门禁不检查） |
| `design-system.md` | 附加 | 设计系统登记：每个 token 一行，只追加（旧 token 不能改或删，`kb-sync` 提升时逐条比对；门禁不检查是否存在） |
| `index.md` | `kb-sync` 生成 | 文件清单、合并方式、来源 spec；由 `kb-sync` 生成到知识库，不要写 |

合并方式：`context.md` 覆盖为最新；`design-system.md` 只追加；`flowchart.md` 按章节改（按页面）；`demo.html` 覆盖为最新。

---

## 强制执行的 Skills（按序）

> **执行前检测**：在执行任何 Skill 之前，先检查 `<SPEC_DIR>/interaction-design/docs/context.md` 是否已存在。
>
> ```
> 已有 interaction-design/context.md？
>   ├── 是（功能新增 / 重构 / UI调整）
>   │     → 读取已有 context.md 和 <SPEC_DIR>/interaction-design/design.md 中的 Design Tokens
>   │     → 跳过步骤 1（ui-ux-pro-max），直接复用已有设计系统
>   │     → 步骤 2（wireframe-generator）仍需执行，但线框图必须沿用已有 Design Tokens
>   │     → 步骤 3（design-token-spec）仅补充新增 token，不重新生成整套
>   └── 否（全新模块）→ 执行全部 4 个步骤
> ```

**第 1 步 — ui-ux-pro-max**（仅全新模块执行）
使用 skill `ui-ux-pro-max`（`<skill-dir>` 指该 skill 的目录，即其 SKILL.md 所在目录）
执行：`python3 <skill-dir>/scripts/search.py "{product_type} {style_keywords}" --design-system -f markdown -p "{project-name}"`
- 已知技术栈时补一次栈规范查询：`python3 <skill-dir>/scripts/search.py "<关键词>" --stack <stack>`（22 个栈，见 skill 的 Step 4）
- 不要加 `--persist`：设计系统以 `<SPEC_DIR>/interaction-design/design.md` 为准
- 降级：没有 Python 或脚本报错时，直接查阅 `<skill-dir>/data/` 下的 CSV（styles、colors、typography、products、ui-reasoning 等），并在 design.md 中注明“未经检索脚本排序”
输出：完整设计系统 → 写入 `<SPEC_DIR>/interaction-design/design.md` 的 `## 设计系统` 小节，作为 design-token-spec 的数据来源

**第 2 步 — wireframe-generator**
使用 skill `wireframe-generator`
输出：页面线框图 → 写入 `<SPEC_DIR>/interaction-design/design.md` 的 `## 线框图` 小节（skill 的每个 Wireframe 块放在该小节下）
> 已有设计系统时：线框图中所有样式描述必须引用已有 Design Tokens，不得引入新变量

**第 3 步 — design-token-spec**
使用 skill `design-token-spec`
输出：Design Tokens 表格 → 写入 `<SPEC_DIR>/interaction-design/design.md` 的 `## Design Tokens` 小节
> 已有设计系统时：仅补充本次新增的 token，在已有 token 表格末尾追加，不重新生成整套

**第 4 步 — flowchart-generator**
使用 skill `flowchart-generator`
输出：用户流程图 → 写入 `<SPEC_DIR>/interaction-design/docs/flowchart.md`

---

## 交互歧义识别（UXAMB）

以下情况标记为 UXAMB：操作路径不明确、状态转换未定义、错误反馈缺失、空状态未设计、加载状态缺失、权限边界模糊。

标注格式：
```
### UXAMB-{编号}
- 关联用户故事：US-{编号}
- 歧义描述：{具体哪个交互环节不明确}
- 设计建议：{UX 给出的交互方案}
- 状态：待确认 / 已确认 / 已忽略
- 依据：answers.md：「{用户原话}」（已确认 / 已忽略时必填）
```

只有用户在 `<SPEC_DIR>/interaction-design/answers.md` 里回答过，才能把状态改成「已确认」或「已忽略」，并在「依据」里引用用户原话；还没回答的写进 open-questions.md 返回 need_user。`aw check` 会拦下仍是「待确认」的条目；编排者请用户确认本阶段时，把每条 UXAMB 的状态和引用的原话列给用户当场核对。

---

## 执行规范

1. 执行全部 4 个 Skill（按顺序）
2. 展示 UXAMB 列表，等待用户确认所有交互歧义（未回答的写进 open-questions.md 返回 need_user；回答进 answers.md 后再标状态并引用原话）
3. 将确认后的定义更新到线框图和交互说明
4. 用户确认后，生成所有输出文件，标记阶段为 `completed`

覆盖要求：每个 US 至少对应一个页面线框图和一张用户流程图。

---

## 输出文件规范

### <SPEC_DIR>/interaction-design/requirements.md

```markdown
# Interaction Design — Requirements

## 交付范围

### 必须交付
| 交付物 | 验收标准 |
|--------|---------|
| 线框图 | 每个 US 对应至少一个页面线框图 |
| Design Tokens | 覆盖颜色/字体/间距/圆角/阴影五类 |
| 用户流程图 | 每个 US 对应一张 Mermaid 流程图 |
| demo.html | 单文件，覆盖所有 US 页面和 UI 状态 |

### Out of Scope
- 技术实现细节：属于 technical-design 职责
- 后端 API 设计：属于 technical-design 职责

## 验收标准（EARS 格式）

### AC-UX-1
WHEN 交互设计完成 THEN 系统 SHALL 为每个 US 生成页面线框图，含关键元素表格和所有 UI 状态

### AC-UX-2
WHEN Design Tokens 生成完成 THEN 系统 SHALL 提供 Light 和 Dark 两套颜色值
```

### <SPEC_DIR>/interaction-design/design.md

```markdown
# Interaction Design — Design

## 设计决策

### 决策 1：{设计风格选型}
- **选择**：{选择了哪种设计风格}
- **理由**：{依据}
- **备选方案**：{其他考虑}
- **权衡**：{接受的取舍}

## 设计系统
{ui-ux-pro-max 的设计系统摘要：风格、配色、字体、效果；复用已有设计系统时写“沿用”并注明来源}

## 线框图

### {页面名称}（US-{NNN}）

**Purpose**: {一句话描述页面功能}

**Layout**:
```
+------------------------------------------+
| [Logo]                    [Nav links]     |
+------------------------------------------+
|  [_________________________]  ← input    |
|  [    Submit Button    ]                  |
+------------------------------------------+
```

**Key Elements**:
| Element | Type | Behavior |
|---------|------|----------|

**States**: default / loading / success / error / empty

## Design Tokens

### Colors
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-primary` | {值} | {值} | 按钮、链接 |

### Typography / Spacing / Radius / Shadow
（同上格式）

## 组件清单
| 组件名 | 用途 | 状态列表 |
|--------|------|---------|
```

### <SPEC_DIR>/interaction-design/tasks.md

```markdown
# Interaction Design — Tasks

## 概览
- 总任务数：{N} | P0 任务数：{N} | 预估工时：{N} 天

## 任务列表

### TASK-ID-001：{任务名称}
- **描述**：{足够详细}
- **优先级**：P0 / P1 / P2
- **复杂度**：XS / S / M
- **关联需求**：{US/AC 编号}
- **依赖**：无 / TASK-ID-{N}
- **状态**：pending
```

> 任务 ID 前缀改为 `TASK-ID-`（Interaction Design）

### <SPEC_DIR>/interaction-design/docs/context.md

```markdown
# Interaction Design Context → technical-design

## 模块名称
<MODULE>

## 组件清单摘要
| 组件名 | 用途 | 状态列表 |
|--------|------|---------|

## Design Tokens 摘要
- 主色：{--color-primary 值}
- 字体：{--font-family-base 值}
- 基础间距：{--spacing-4 值}

## 关键交互约定
- {功能模块}：{核心交互约定，1-2句}

## 状态
confirmed
```

### <SPEC_DIR>/interaction-design/docs/design-system.md（附加，只追加）

```markdown
# Design System

| Token | 值 | 用途 |
|-------|----|------|
| `--color-primary` | {值} | {用途} |
```

每个 token 一行，行首是 `|` 加反引号包住的 token 名（同上例）。已有 token 的行一个字都不能改，也不能删；新 token 追加在表格末尾。

### <SPEC_DIR>/interaction-design/docs/demo.html（附加）

单文件、离线可用、覆盖所有 US 页面和 UI 状态。

技术约束：
- 纯 HTML + 内联 CSS + 原生 JS，不引用任何外部 CDN
- CSS 变量名与 `<SPEC_DIR>/interaction-design/design.md` 中的 token 名称一致
- US ≤ 5 用 Tab 导航，> 5 用侧边栏导航
- 每个页面实现：default / loading / success / error / empty 五种状态

---

## 完整性校验

| 文件 | 位置 | 缺失时 |
|------|------|--------|
| `requirements.md` | specs | 校验失败，阶段保持 `in_progress` |
| `design.md` | specs | 校验失败，阶段保持 `in_progress` |
| `tasks.md` | specs | 校验失败，阶段保持 `in_progress` |
| `context.md` | docs | 校验失败，阶段保持 `in_progress` |
| `index.md` | docs | `kb-sync` 生成（不要写） |
| `flowchart.md` | docs | 附加，门禁不检查；未生成时在 CONFIRM 中注明 |
| `demo.html` | docs | 附加，门禁不检查；未生成时在 CONFIRM 中注明 |
| `design-system.md` | docs | 附加，门禁不检查；有新 token 时追加 |

所有必需文件均为 `generated` → 校验通过，标记 interaction-design 为 `completed`。

---

## 返回格式（给编排者，≤20 行，不贴文件正文）

```
STATUS: done | need_user | upstream_defect
FILES: <本次写入/修改的相对路径>
CONFIRM: <需要用户复核的要点，≤5 条>
UPSTREAM: <upstream_defect 时写 "<phase>: <原因>"，否则留空>
```
