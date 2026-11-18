# Interaction Design — Tasks

## 概览

- 总任务数：14 | P0 任务数：12 | 预估工时：2.5 天
- 说明：本阶段任务均为设计产物（线框、组件规格、流程、原型与自验），不含业务代码实现；实现任务在 tech-tasks 阶段拆解。

## 任务列表

### TASK-ID-001：复用 core 设计系统并登记 token
- **描述**：读取 core 的 `design.md` 与 `docs/design-system.md`，确认知识库只引用既有 token；在 `docs/design-system.md` 登记实际使用的 token（颜色 / 字体 / 间距 / 圆角 / 阴影 / 动效 / 布局）与语义映射，声明无新增 token。
- **优先级**：P0
- **复杂度**：XS
- **关联需求**：AC-UX-19、AC-UX-28
- **依赖**：无
- **状态**：done

### TASK-ID-002：知识库列表页线框与组件规格
- **描述**：产出列表页线框、`KnowledgeBaseTable` / `KbProjectFilter` 关键元素与五态（default / loading / success / error / empty），定义旧版本提示、只读说明与导入 / 浏览 / 删除入口行为。
- **优先级**：P0
- **复杂度**：S
- **关联需求**：US-012、US-016、AC-UX-19、AC-UX-26
- **依赖**：TASK-ID-001
- **状态**：done

### TASK-ID-003：导入页线框、校验规则与文案
- **描述**：产出导入页线框、`KbImportPanel` / `KbFileValidationList` / `KbImportReport` 规格；覆盖类型白名单、必须含 `index.json`、20MB / 10MB / 50 个 / 100MB 上限、结构校验、部分条目跳过与整体回滚的全部文案与状态。
- **优先级**：P0
- **复杂度**：M
- **关联需求**：US-012、AC-UX-20、AC-UX-21
- **依赖**：TASK-ID-001
- **状态**：done

### TASK-ID-004：浏览页线框与检索 / 类型分栏规格
- **描述**：产出浏览页线框与 `KbBrowseLayout` / `KbTypeTabs` / `KbSearchBox` / `KbEntryList` 规格；定义项目 / 知识库 / 版本筛选、编号前缀 / 完整编号 / 关键词检索、计数与空态。
- **优先级**：P0
- **复杂度**：M
- **关联需求**：US-013、AC-UX-22
- **依赖**：TASK-ID-001
- **状态**：done

### TASK-ID-005：条目详情页线框与字段降级规格
- **描述**：产出详情页线框与 `KbEntryDetail` 规格；覆盖摘要、正文、字段、表、代码路径、一跳邻居、来源文件、缺失字段「—」、正文缺失与字段全缺的空态。
- **优先级**：P0
- **复杂度**：S
- **关联需求**：US-013、AC-UX-22、AC-UX-23
- **依赖**：TASK-ID-004
- **状态**：done

### TASK-ID-006：会话注入选择器与字符预算规格
- **描述**：产出调用面板内嵌 `KbInjectPicker` / `KbCharBudget` 线框与行为；定义已选条数、注入 / 提示 / 合计 / 200,000 的实时计算，>90% warning、超限 destructive + 禁用「发起调用」、不截断，及选择在会话内保留的边界。
- **优先级**：P0
- **复杂度**：M
- **关联需求**：US-014、AC-UX-24、AC-UX-27
- **依赖**：TASK-ID-001
- **状态**：done

### TASK-ID-007：失效条目阻塞确认对话框规格
- **描述**：产出 `KbInvalidEntryDialog` 线框与状态机：发起前剔除并列出全部失效编号与原因，确认用剩余条目继续并产生记录，取消不发起、不产生记录；定义取消后勾选与提示的保留规则。
- **优先级**：P0
- **复杂度**：S
- **关联需求**：US-014、AC-014-4、AC-UX-25
- **依赖**：TASK-ID-006
- **状态**：done

### TASK-ID-008：新鲜度与版本冲突提示规格
- **描述**：定义 `KbFreshnessBadge` / `KbConflictNotice` / `KbVersionSelector` 的文案、颜色与位置：N 天前 / 可能过期 / 未知 / 版本冲突（列出来源）/ 已被新版本取代（跳转最新版），统一「只提示不阻断」。
- **优先级**：P1
- **复杂度**：S
- **关联需求**：US-015、AC-UX-23
- **依赖**：TASK-ID-004、TASK-ID-005
- **状态**：done

### TASK-ID-009：删除确认与历史标注规格
- **描述**：产出 `KbDeleteDialog` 线框与 `KbDeletedBadge` 规格；列明知识库及其全部版本、条目索引、已存文件、项目关联的级联范围，说明历史会话与调用记录不变；无撤销。
- **优先级**：P1
- **复杂度**：XS
- **关联需求**：US-016、AC-UX-26、AC-UX-27
- **依赖**：TASK-ID-002
- **状态**：done

### TASK-ID-010：项目上下文关联知识库区块规格
- **描述**：产出 `ProjectKnowledgeSummary` 线框与状态（≤3 条、查看全部、空态 CTA、loading、error）；明确 core 页面只加挂载位、不改既有布局，并在 UXAMB-004 记录归属待确认。
- **优先级**：P0
- **复杂度**：S
- **关联需求**：US-012、AC-012-6、AC-UX-19
- **依赖**：TASK-ID-001
- **状态**：done

### TASK-ID-011：用户流程图（US-012 ~ US-016）
- **描述**：为每个 US 产出一张 Mermaid 流程图，含开始 / 结束节点与带标签的决策分支；US-014 体现超限拒绝与失效条目阻塞确认的确认 / 取消两条路径。
- **优先级**：P0
- **复杂度**：S
- **关联需求**：AC-UX-19 及全部 US
- **依赖**：TASK-ID-003、TASK-ID-004、TASK-ID-006、TASK-ID-007、TASK-ID-009
- **状态**：done

### TASK-ID-012：demo.html 单文件原型
- **描述**：实现列表 / 导入 / 浏览 / 详情 / 会话注入五个页面与两个对话框，覆盖五种 UI 状态、明暗主题、字符预算、失效阻塞确认与删除确认；纯 HTML + 内联 CSS + 原生 JS，无外部依赖，token 名与 design.md 一致。
- **优先级**：P0
- **复杂度**：M
- **关联需求**：AC-UX-29、全部 US
- **依赖**：TASK-ID-002 ~ TASK-ID-011
- **状态**：done

### TASK-ID-013：Playwright 双主题自验
- **描述**：用系统 Chrome headless（1440×900）跑 Light / Dark 两轮交互断言，覆盖页面导航、导入校验、检索与详情、预算与超限、失效阻塞确认的确认 / 取消、删除确认、密码不泄露无关项；收集 `console.error` 与页面脚本错误并回填验证记录。
- **优先级**：P0
- **复杂度**：S
- **关联需求**：AC-UX-29、AC-UX-30
- **依赖**：TASK-ID-012
- **状态**：done

### TASK-ID-014：知识库文档暂存与一致性复核
- **描述**：更新 `docs/context.md`、`docs/flowchart.md`、`docs/design-system.md`；复核 5 个 US、24 条 AC 与 AC-UX-19 ~ AC-UX-30 的覆盖，确认无未登记 token、无与 core 冲突的组件命名。
- **优先级**：P0
- **复杂度**：XS
- **关联需求**：全部
- **依赖**：TASK-ID-013
- **状态**：done
