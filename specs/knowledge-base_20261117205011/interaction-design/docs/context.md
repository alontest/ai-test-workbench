# Interaction Design Context → technical-design

## 模块名称

knowledge-base（知识库：导入 → 浏览 → 会话注入）

## 页面与路由

| 路由 | 页面 | 归属 |
|------|------|------|
| `/knowledge-bases` | 知识库列表（项目筛选、最新版本、旧版本提示、导入入口、删除） | 本 spec |
| `/knowledge-bases/import` | 导入知识库（项目选择、多文件、逐项校验、导入报告） | 本 spec |
| `/knowledge-bases/:kbId` | 知识库浏览（项目 / 知识库 / 版本 / 类型筛选 + 编号与关键词检索） | 本 spec |
| `/knowledge-bases/:kbId/entries/:code` | 条目详情（摘要、正文、字段、表、代码路径、一跳邻居、冲突、新鲜度） | 本 spec |
| `/sessions/:id` | 会话「发起调用」面板内嵌知识库注入选择器、字符预算与失效条目阻塞确认 | 本 spec 组件，core 页面内嵌 |
| `/projects` | 项目上下文页的「关联知识库」区块（≤3 条 + 查看全部） | 本 spec 组件，core 页面挂载位 |

侧边栏「基座管理」新增「知识库」入口；全部路由受 core 的 `AuthGate` 保护，复用 AppShell、用户菜单与登录态。

## 组件清单摘要

| 组件名 | 用途 | 状态列表 |
|--------|------|---------|
| KnowledgeBaseTable | 知识库列表（版本、生成时间、条目数、状态、操作） | loading / success / empty / error / deleting |
| KbProjectFilter | 列表与浏览的项目筛选 | default / active-filter |
| KbImportPanel | 导入页容器：规则 + 文件选择 + 提交 | idle / selecting / validating / rejected / importing / success / structure-error |
| KbFileValidationList | 逐文件校验结果 | pass / reject-type / reject-size / reject-count / reject-total / present |
| KbImportReport | 导入结果与跳过条目 | success / partial / superseded-version / failed |
| KbBrowseLayout | 浏览页筛选、分栏、检索、列表 | loading / success / empty / error / superseded |
| KbTypeTabs | 八类类型分栏 | active / disabled(空) |
| KbSearchBox | 编号前缀 / 完整编号 / 关键词检索 | idle / typed / no-result |
| KbEntryList | 条目列表与状态徽标 | default / hover / focus / empty |
| KbEntryDetail | 条目详情 | default / body-missing / superseded / error / loading |
| KbFreshnessBadge | 新鲜度展示 | fresh / stale(可能过期) / unknown(未知) |
| KbConflictNotice | 版本冲突与来源 | none / conflict / superseded-source |
| KbVersionSelector | 版本切换（最新 / 旧版本只读） | latest / superseded / switching |
| KbInjectPicker | 会话内按编号勾选注入 | default / selected / invalid-entry / deleted-kb / over-limit / read-only |
| KbCharBudget | 已选 / 注入 / 提示 / 合计 / 上限 | normal / warning(>90%) / exceeded / not-truncated |
| KbInvalidEntryDialog | 失效条目阻塞确认（列编号 + 原因） | default / confirm-loading / error |
| KbDeleteDialog | 删除知识库确认（级联范围） | default / confirm-loading / error |
| KbDeletedBadge | 历史记录「知识库已删除」标记 | visible |
| ProjectKnowledgeSummary | 项目上下文关联知识库区块 | default / loading / empty / error / capped |

完整线框、关键元素表与五态说明见 `design.md`「线框图」；逐文件校验文案与字符预算口径见「关键交互约定」。

## Design Tokens 摘要

- 全部沿用 workbench-core，**本 spec 无新增 token**：主色 `--color-primary` = `#1E293B` / `#EDEDED`；页面底色 `--color-background` = `#F8FAFC` / `#0A0A0B`；卡片 `#FFFFFF` / `#141416`；边框 `#CBD5E1` / `#2A2A2E`。
- 强调色 `--color-accent` = `#16A34A` / `#22C55E`；语义色：success、warning（版本冲突 / 可能过期 / >90% 预算）、info（旧版本只读）、destructive（校验失败 / 超限 / 失效条目 / 删除）。
- 字体：正文 `--font-family-base` = `"IBM Plex Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif`；标题 `--font-family-heading`、编号与正文预览 `--font-family-mono` = `"JetBrains Mono", "SFMono-Regular", Menlo, monospace`。
- 基础间距 `--spacing-4` = `16px`；圆角 `--radius-md` = `8px`；阴影 `--shadow-md` = `0 4px 6px rgba(15, 23, 42, 0.12)` / `0 4px 10px rgba(0, 0, 0, 0.55)`；布局 `--sidebar-width` 248px、`--topbar-height` 64px、`--content-max-width` 1280px。
- 对比度：Light 正文/背景 17.06:1，Dark 16.90:1；次要文字 Dark 7.72:1；均 ≥ 4.5:1。完整表见 `design.md`「Design Tokens」。

## 关键交互约定

- 导入：仅 `.json` / `.md` / `.markdown` 且必须含 `index.json`；`index.json` ≤20MB、其他单文件 ≤10MB、单次 ≤50 个、单库合计 ≤100MB；逐文件给出通过 / 具体原因，存在不合规项禁用提交；服务端结构不合法或没有可导入条目则不建库并整体回滚；同名导入生成新版本、旧版本只读。
- 浏览：默认最新版本；项目 / 知识库 / 版本 / 类型筛选；检索支持编号前缀、完整编号与关键词（标题 / 摘要 / 正文）；无匹配是空态不是错误；详情缺失字段显示「—」，正文缺失展示摘要并标「正文缺失」，不推测、不渲染 HTML。
- 新鲜度与冲突：>30 天「可能过期」、缺字段「未知」、同编号摘要不同「版本冲突（列来源）」、旧版本「已被新版本取代（可跳最新版）」；全部只提示不阻断；不克隆仓库、不解析代码。
- 字符预算：200,000 字符由 core 单点定义；显示「已选 N 条 · 注入 X 字符 · 提示 Y 字符 · 合计 Z / 200,000」；Z > 90% warning，Z > 200,000 显示分段字数与超出量、禁用「发起调用」、不截断。X 的统计口径待 UXAMB-001 确认（默认按完整注入块计）。
- 失效条目：发起外部请求前剔除已删除 / 已被取代 / 不存在的条目，弹出阻塞确认并列出全部编号与原因；确认后用剩余有效条目发起并产生 AiCallRecord，取消则不发起、不产生记录；不静默降级。
- 留痕与脱敏：时间线与调用记录展示知识库名、版本、编号列表、字符数，不展示正文；知识库已删除时编号旁标「知识库已删除」；正文 / 摘要 / 字段值不进入日志与错误响应。
- 删除：只从列表行发起；确认框列明知识库及其全部版本、条目索引、已存文件、项目关联，说明历史记录不变；无撤销、无自动过期。
- 反馈与无障碍：列表具备 loading / empty / error；异步按钮内联 loading；对话框 Esc 关闭并归还焦点；可见焦点环、状态同时用文字与颜色；≤768px 侧边栏抽屉、按钮 ≥44×44px。

## 待确认

- UXAMB-001 注入字符预算口径（仅正文 vs 完整注入块）
- UXAMB-002 失效确认取消后的勾选 / 提示保留规则
- UXAMB-003 会话打开期间同名新版本导入时的选择器刷新策略
- UXAMB-004 项目上下文「关联知识库」区块的挂载归属（core 页面是否允许加挂载位）
- 以上四条已写入 `design.md`「交互歧义假设」与 `open-questions.md`，确认前线框与 demo 按「设计建议」实现。

## 状态

pending（2026-11-18 生成；等待用户确认本阶段。确认后由 kb-sync 提升到知识库，届时视为 confirmed）
