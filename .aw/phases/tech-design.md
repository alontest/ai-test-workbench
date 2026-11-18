# tech-design：组件 / 数据库 / API 设计（原 technical-design 步骤 4–6）

> **执行契约（AlonWorkflow，优先级高于下文任何“等待用户确认 / 标记 completed”的描述：本阶段做完由编排者停下来请用户确认，你不标记完成）**
>
> - 你是子代理，**不能与用户对话**。下文写“询问/展示/等待用户确认”处：把待确认内容写进产物，并在返回的 `CONFIRM` 字段列出；信息不足以继续时写 `<SPEC_DIR>/technical-design/open-questions.md`（每题附选项与默认值），返回 `STATUS: need_user`。
> - 所有产物只写 `<SPEC_DIR>/technical-design/`。知识库文档写暂存区 `<SPEC_DIR>/technical-design/docs/`：暂存区里已有的文件是 KB 底稿（编排者开始本阶段时用 skill `kb-sync` 从知识库带入），在它上面修改，不要整份重写；用户确认本阶段后，由编排者用 skill `kb-sync` 按合并方式提升到 `docs/<MODULE>/technical-design/`，`index.md` 由 `kb-sync` 生成。不要直接写 `docs/`。
> - 本阶段必须产物以 `.aw/phases.json` 中 `tech-design` 为准（需求类型可能覆盖），`python3 .aw/aw.py check <SPEC_DIR> --phase tech-design` 可自检。
> - 阶段确认只能由用户在对话里给出，你不要替用户确认。
> - **技术栈约定（packs）**：先探测项目已有技术栈（清单文件、lockfile、已有代码）。新项目或无法判断时，使用 skill `tech-stack-advisor` 给出多种选项，**不要预设某种语言**，把选项写入产物并在 `CONFIRM` 中请用户决定。然后查看 `.aw/install.json` 的 `packs` 与 `.aw/packs/<name>/pack.json`：若已安装的 pack 声明了与当前（已探测或用户选定）技术栈匹配的约定，则加载其 `conventions/` 以及列出的 skills。pack skill 只在该 skill 确实出现在你的可用 skills 列表中时执行；未安装匹配 pack 时，按通用最佳实践设计，并在 `docs/architecture-decisions.md` 注明「未安装 <pack>，未套用其约定」，在 CONFIRM 中提示用户可用 `alonwf pack add <pack>` 安装。
> - 前置：tech-arch 已确认，先读 `<SPEC_DIR>/technical-design/docs/architecture-decisions.md`，不得推翻已确认决策；确需推翻则返回 upstream_defect（UPSTREAM: tech-arch）。UI/UX 调整类型没有 tech-arch：沿用现有架构，只做组件拆分（门禁只要求 `docs/component-tree.md`）。Bug 修复类型只在 `SCOPE` 的 api / data 为 yes 时才有本阶段，只要求对应的 `docs/api-spec.md` / `docs/database-schema.md`，不要求 `change-spec.md`。
> - 本阶段只做步骤 4–6。先读 `requirements-analysis/intake.md` 的 `SCOPE` 行：始终产出 `change-spec.md`（写在 `<SPEC_DIR>/technical-design/change-spec.md`，留在 spec 侧、不进知识库；改哪些文件、每个文件改什么、关键函数签名）；`api=yes` 追加 `docs/api-spec.md`，`data=yes` 追加 `docs/database-schema.md`，`ui=yes` 追加 `docs/component-tree.md`。未声明 SCOPE 时三选一：`docs/component-tree.md` / `docs/database-schema.md` / `docs/api-spec.md`。

---

## 职责定位

将业务规范和交互设计转化为完整的技术实现蓝图，产出架构决策、数据库 Schema、API 规范、项目文件结构、开发环境配置和开发任务列表，让开发者拿到文档即可开始编码。

---

## 输入

| 来源 | 读取文件 | 必需 | 关键字段 | 缺失时 |
|------|---------|------|---------|--------|
| requirements-analysis | `<SPEC_DIR>/requirements-analysis/docs/context.md` | 是 | 用户故事摘要、AC 完整列表、数据实体 | 返回 `STATUS: upstream_defect`（UPSTREAM: requirements-analysis） |
| intake | `<SPEC_DIR>/requirements-analysis/intake.md` 的 `SCOPE` 行 | 否 | ui / api / data | 未声明时按“至少其一”产出 |
| tech-arch | `<SPEC_DIR>/technical-design/docs/architecture-decisions.md` | 否 | 已锁定的技术栈、数据库、认证方案 | UI/UX 调整类型没有 tech-arch：沿用现有架构；其他类型缺失时返回 `STATUS: upstream_defect`（UPSTREAM: tech-arch） |
| interaction-design | `<SPEC_DIR>/interaction-design/docs/context.md` | 否 | 组件清单、Design Tokens 摘要、关键交互约定 | 本 profile 没有交互设计阶段或 `ui=no`：组件拆分以项目现有界面代码为输入，不新增样式变量，并在 CONFIRM 中注明 |
| interaction-design（样式规范） | `<SPEC_DIR>/interaction-design/design.md` | 否 | Design Tokens 完整定义、视觉风格、组件状态规范 | 同上 |
| KB 底稿 | `<SPEC_DIR>/technical-design/docs/` 下由 `kb-sync` 带入的 `api-spec.md` / `database-schema.md` / `component-tree.md` | 否 | 本模块已有的端点、表、组件 | 首次建立 |
| 共享 KB 底稿 | `<SPEC_DIR>/_shared/ontology/domain-events.md`（由 `kb-sync` 带入） | 否 | 项目已有的领域事件 | 首次建立 |
| 本体切片（只读） | `<SPEC_DIR>/ontology-slices/tech-design.md`（编排者用 skill `ontology` 生成，存在才读） | 否 | 实体的表名和类文件、规则的落地文件和 Evidence、流程上下游、候选事件 | 项目没有本体参考层（`ontology-work/views/index.json`）时不生成：跳过本体对照，并在 CONFIRM 中注明 |
| intake（多域） | `<SPEC_DIR>/_shared/domain-map.md`，没有时读 `docs/_shared/domain-map.md`（只读） | 否 | 跨域接口约定 | 单域，忽略跨域标记 |

**本体切片怎么用**：先在切片里找落点，再设计。切片里有表名的实体，`database-schema.md` 在原表上改，不新建重复的表；规则写到切片标出的落地文件，接口复用已有端点；新代码的类名、表名、字段名按切片的英文名起。切片里标「⚠️ 磁盘上没有」的路径以代码现状为准，并在 CONFIRM 中注明。写 `change-spec.md` 时在开头写一行 `涉及本体：…`，列出本阶段新用到的编号（如接口 `API-…`、事件 `DE-…`）。切片里的候选事件（`DE-…`）要落地时，在 `domain-events.md` 追加 `DE-C` 条目，「对应图谱」写这个候选编号，在「载荷」「订阅方」里尽量写到事件类名和 Handler 类名。

> **重要**：若 interaction-design 阶段已完成，技术方案中所有涉及 UI 的产出（包括组件树、任务描述，以及如有生成 demo.html 时）必须严格遵循 interaction-design 阶段定义的 Design Tokens 和视觉规范，不得自行定义新的样式变量或视觉风格。

---

## 输出文件

本阶段只写下列文件（`change-spec.md` 在 `technical-design/` 下，其余在 `technical-design/docs/` 下）；其余文件由 tech-arch、tech-tasks 产出。

| 文件 | 类型 | 内容 |
|------|------|------|
| `change-spec.md` | 按 SCOPE | 改哪些文件、每个文件改什么、关键函数签名；声明 SCOPE 时必需；留在 spec 侧，不进知识库 |
| `docs/component-tree.md` | 按 SCOPE | 组件拆分树、Props 接口、复用清单（`ui=yes` 时必需） |
| `docs/database-schema.md` | 按 SCOPE | 数据库表结构、ER 图、迁移脚本（`data=yes` 时必需） |
| `docs/api-spec.md` | 按 SCOPE | API 端点定义、请求/响应格式、OpenAPI 规范（`api=yes` 时必需） |
| `docs/flowchart.md` | 附加 | 系统架构图 + 关键流程时序图 + ER 图（门禁不检查） |
| `<SPEC_DIR>/_shared/ontology/domain-events.md` | 附加 | 本次新增的领域事件（只追加，见下方模板；用户确认后由 `kb-sync` 提升到共享知识库） |

未声明 SCOPE 时，上面四个文件至少产出其一（Bug 修复通常只写 `change-spec.md`）。

**暂存区里已有的文件是 KB 底稿，在它上面修改，不要整份重写**：`api-spec.md` 按端点改，`database-schema.md` 按表改，`component-tree.md` 按组件改，只动本次受影响的章节；`kb-sync` 提升时列出被增、改、删的章节。

**多域时的跨域标记**：域地图（`<SPEC_DIR>/_shared/domain-map.md` 或 `docs/_shared/domain-map.md`）的「跨域接口约定」里有本模块时，`api-spec.md` 里跨域调用的端点在标题或说明里标 `[cross-domain]`。`kb-sync` 提升时检查 `api-spec.md` 至少有一处标记（做不到逐个端点核对）。

---

### 第 4 步 — component-breakdown（组件拆分）
使用 skill `component-breakdown`
依赖：步骤 3（技术栈已确认）+ 步骤 3.5（框架已确认）+ interaction-design 阶段的 Design Tokens 和视觉规范（没有交互设计产物时见「输入」表的缺失处理）
执行条件：`ui=yes`，或未声明 SCOPE 且本次涉及界面
输出：组件树 + Props 接口 → 写入 `<SPEC_DIR>/technical-design/docs/component-tree.md`

> **样式规范继承**：组件树中每个 UI 组件的样式描述必须引用 `<SPEC_DIR>/interaction-design/design.md` 中定义的 Design Tokens（如 `--color-primary`、`--spacing-4` 等），不得重新定义。

> **框架组件约定**：若已安装的 pack 为当前前端栈提供了组件/类型约定（见 `.aw/packs/<name>/conventions/` 与对应 item-* skills），则遵循该 pack；只在该 skill 确实出现在你的可用 skills 列表中时执行。未安装匹配 pack 时按该框架的通用最佳实践拆分组件，不要假设特定目录或组件库。

### 第 5 步 — database-design（数据库设计）
使用 skill `database-design`
依赖：步骤 3（数据库选型已确认）
执行条件：`data=yes`，或未声明 SCOPE 且本次涉及数据模型
输出：数据库 Schema + ER 图 + 迁移脚本 → 写入 `<SPEC_DIR>/technical-design/docs/database-schema.md`

> **数据库约定**：遵循 tech-arch 已确认的数据访问技术。若已安装 pack（如 dotnet pack）为该栈提供了数据库约定，则加载并遵循其 `conventions/`；否则按该栈通用实践给出 Schema 与迁移方式。

### 第 6 步 — api-design（API 设计）
使用 skill `api-design`
依赖：步骤 5（数据模型已确定；本次未做数据库设计时，以现有数据模型代码为准）
执行条件：`api=yes`，或未声明 SCOPE 且本次涉及对外接口
输出：API 端点规范 + OpenAPI 文档 → 写入 `<SPEC_DIR>/technical-design/docs/api-spec.md`

> **API 约定**：遵循 tech-arch 已确认的技术栈。若已安装 pack 为该栈提供了 API / 客户端约定（例如 item pack 的前端调用层、dotnet pack 的后端分层、flowflex pack 的标识符序列化），则加载 `.aw/packs/<name>/conventions/` 与列出的 skills（只在该 skill 确实出现在你的可用 skills 列表中时执行）。前后端同时存在时，请求/响应字段与 ID 类型必须与已加载的 pack 约定一致；未安装匹配 pack 时，明确文档化所选的响应形状与 ID 类型，不要假设特定客户端封装。

---

> ⏸️ **确认节点**：步骤 4-6 完成后，展示组件树、数据库 Schema、API 端点总览，等待用户确认无遗漏后，才能继续步骤 7-8。

---


## 输出文件规范

### <SPEC_DIR>/technical-design/change-spec.md

```markdown
# Change Spec

涉及本体：{本阶段新用到的参考层编号，如 API-create-order、DE-submit-order；没有本体切片时写「无」}

## 改动文件
| 文件 | 改动类型（新增 / 修改 / 删除） | 改什么 |
|------|-----------------------------|-------|

## 关键函数签名
- `{函数签名}`：{职责}

## 不改动的部分
- {明确不动的模块或接口}
```

### <SPEC_DIR>/technical-design/docs/api-spec.md（补充约定）

api-design skill 的输出格式之外，本文件还必须包含下列小节：

#### 响应与错误约定

先写出本项目实际采用的响应形状、错误码与 ID 类型。若已安装 pack 提供了这些约定，把 pack 中的格式抄入本文件并遵循；否则选择一种清晰的方案写在这里，并在 ADR 中记录。不要假设某种固定的包装字段或 ID 序列化方式。

---

#### 端点列表

##### {功能模块名}

###### {HTTP方法} {路径}
- **描述**：{端点功能描述}
- **认证**：需要 / 不需要
- **关联 US**：US-{NNN}

**请求**
```json
// Headers
Authorization: Bearer {token}
Content-Type: application/json

// Body（POST/PUT）
{
  "fieldName": "string",   // 字段说明
  "pageNo": 1,             // 页码，从 1 开始
  "pageSize": 20           // 每页条数
}
```

**响应（200 OK）**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "<project-id>",   // 使用本项目已确认的 ID 类型
    "fieldName": "value",
    "createdAt": "2026-01-01T00:00:00Z"
  }
}
```

**响应（分页列表）**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      { "id": "<project-id>", "fieldName": "value" }
    ],
    "total": 100
  }
}
```

**错误响应**
```json
{ "code": 404, "message": "资源不存在", "data": null }
```

**前端调用示例**

按已确认技术栈与已安装 pack 的客户端约定编写；未安装 item pack 时，使用项目既有 HTTP 客户端或该框架的常规写法，并在此给出示例。不要假设特定封装或源码路径。

### <SPEC_DIR>/_shared/ontology/domain-events.md（附加，只追加）

```markdown
# Domain Events

### DE-C{序号} {名称}
- **对应图谱**：{候选事件编号，如 DE-submit-order；图谱里没有写「未覆盖」}
- **触发条件**：{什么情况下发出}
- **载荷**：{主要字段}
- **发布域**：{模块名}
- **订阅方**：{订阅方模块名列表}
- **来源 spec**：{spec 目录名}
```

每个条目的标题写成 `### DE-C<序号> 名称`（如 `### DE-C1 订单已提交`；序号在本文件、本前缀下从 1 递增，用过的不复用），条目里要再分小节时只用 `####`。每条新条目必须写「对应图谱」：`ontology-work/views/index.json` 里的参考层编号，图谱里没有就写「未覆盖」。只追加：已有条目（标题和正文）一个字都不能改，也不能删；要修正旧条目时追加一个新条目并写 `取代：<旧编号>`。`kb-sync` 提升时逐条比对，并核对「对应图谱」编号存在。

### <SPEC_DIR>/technical-design/docs/flowchart.md（附加）

必须同时包含：
1. 系统分层架构图（Mermaid graph）
2. 至少一张核心流程时序图（Mermaid sequenceDiagram）
3. 数据库 ER 图（Mermaid erDiagram，与 database-schema.md 保持一致）

---

## 返回格式（给编排者，≤20 行，不贴文件正文）

```
STATUS: done | need_user | upstream_defect
FILES: <本次写入/修改的相对路径>
CONFIRM: <需要用户复核的要点，≤5 条>
UPSTREAM: <upstream_defect 时写 "<phase>: <原因>"，否则留空>
```
