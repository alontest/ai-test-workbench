# Component Tree — knowledge-base

> 阶段：tech-design（步骤 4，`ui=yes`）。上游：`interaction-design/docs/context.md`、`interaction-design/design.md`（Design Tokens，370 行起）、`docs/architecture-decisions.md`（ADR-113）。
> **本 spec 不新增任何设计 token、不新增视觉风格**。颜色、字体、间距、圆角、阴影、布局变量全部引用 `interaction-design/design.md` 已定义的 token（`--color-primary`、`--color-background`、`--color-accent`、`--font-family-base`、`--font-family-mono`、`--spacing-4`、`--radius-md`、`--shadow-md`、`--sidebar-width`、`--topbar-height`、`--content-max-width`）。UI 基础件全部复用 core 的 `web/src/components/ui/`（Button / IconButton / Input / Textarea / Select / Badge / StatusPill / Spinner / Skeleton / Tooltip / FormField / ConfirmDialog / EmptyState / ErrorState / Toast），不重做。
> 落地目录：`web/src/features/knowledge/`（core 既有前端根为 `web/src/`，ADR-113 的 `frontend/src/knowledge/` 按此对齐）。全部页面在 core `AuthGate` + `AppShell` 内渲染。

## 组件树

```
AuthGate (core)
└── AppShell (core: 侧边栏 248px / 顶栏 64px / 内容 1280px)
    ├── /knowledge-bases ────────────── KnowledgeBaseListPage
    │   ├── KnowledgeBaseTable
    │   │   ├── KbProjectFilter
    │   │   └── KbDeleteDialog
    │   └── EmptyState (core)
    ├── /knowledge-bases/import ─────── KnowledgeImportPage
    │   ├── KbImportPanel
    │   │   ├── KbFileValidationList
    │   │   └── KbImportReport
    │   └── FormField / Button (core)
    ├── /knowledge-bases/:kbId ──────── KnowledgeBrowsePage
    │   ├── KbBrowseLayout
    │   │   ├── KbProjectFilter
    │   │   ├── KbVersionSelector
    │   │   ├── KbTypeTabs
    │   │   ├── KbSearchBox
    │   │   └── KbEntryList
    │   │       ├── KbFreshnessBadge
    │   │       └── KbDeletedBadge
    │   └── EmptyState / ErrorState (core)
    ├── /knowledge-bases/:kbId/entries/:code ── KnowledgeEntryPage
    │   └── KbEntryDetail
    │       ├── KbFreshnessBadge
    │       ├── KbConflictNotice
    │       └── KbDeletedBadge
    ├── 会话「发起调用」面板（core: CallPanel）
    │   ├── KbInjectPicker
    │   │   ├── KbSearchBox
    │   │   ├── KbTypeTabs
    │   │   ├── KbEntryList
    │   │   └── KbFreshnessBadge / KbConflictNotice
    │   ├── KbCharBudget
    │   └── KbInvalidEntryDialog
    └── /projects 项目上下文页（core，挂载位 data-mount="knowledge-summary"）
        └── ProjectKnowledgeSummary
            └── KbDeletedBadge
```

## 页面组件（4）

| 组件 | 路由 | 职责 | Props | 状态 |
|------|------|------|-------|------|
| `KnowledgeBaseListPage` | `/knowledge-bases` | 项目筛选、列表、导入入口、删除入口；页脚固定说明「只读导入、同名生成新版本、旧版只读」 | 无（读 URL 与 query） | loading / success / empty / error / deleting |
| `KnowledgeImportPage` | `/knowledge-bases/import` | 项目选择 + 多文件上传 + 逐项校验 + 导入报告；有不合规文件时禁用提交 | 无 | idle / selecting / validating / rejected / importing / success / structure-error |
| `KnowledgeBrowsePage` | `/knowledge-bases/:kbId` | 项目/知识库/版本/类型筛选 + 检索 + 条目列表；旧版本顶部提示并提供「查看最新版」 | 无（读 `kbId`、query） | loading / success / empty / error / superseded |
| `KnowledgeEntryPage` | `/knowledge-bases/:kbId/entries/:code` | 条目详情；按 `kbId` + `code` 取条目（旧版本可直接访问） | 无（读路由参数） | loading / success / body-missing / superseded / error |

## 嵌入组件（3，由 core 页面引用）

| 组件 | 挂载位置 | 职责 | Props | 状态 |
|------|---------|------|-------|------|
| `KbInjectPicker` | `web/src/features/calls/CallPanel.tsx` | 按编号勾选当前会话项目当前版本条目；只展示徽标与标题，不渲染正文 | `sessionId: string`、`selection: KbEntryRef[]`、`onChange(sel: KbEntryRef[])`、`disabled?: boolean` | default / selected / invalid-entry / deleted-kb / over-limit / read-only |
| `KbCharBudget` | 同上 | 展示「已选 N 条 · 注入 X 字符 · 提示 Y 字符 · 合计 Z / 200,000」；Z>90% warning，超限显示分段与超出量并禁用「发起调用」，注明「不会截断」 | `itemCount: number`、`promptChars: number`、`injectedChars: number`、`limit: number`（来自服务端 preview，缺省 200000） | normal / warning / exceeded / not-truncated |
| `KbInvalidEntryDialog` | 同上 | 阻塞式确认：列出被剔除编号与原因；确认回传 `confirmInvalidCodes`，取消则关闭且不发起调用 | `open: boolean`、`invalidItems: InvalidItem[]`、`onConfirm(codes: KbEntryRef[])`、`onCancel()` | open / confirming / error |

## 业务组件（14）

| 组件 | 职责 | Props 接口 | 关键约束 |
|------|------|-----------|---------|
| `KnowledgeBaseTable` | 知识库表格：名称、项目、最新版本、生成时间、条目数、状态、操作（浏览/删除）；旧版本行内「另有 N 个旧版本（只读）」 | `{items: KnowledgeBaseSummary[]; loading: boolean; onDelete(kbId: string): void; onBrowse(kbId: string): void}` | 生成时间缺失显示「未知」（`--color-*` 中性色，不推测） |
| `KbProjectFilter` | 项目下拉（全部/单个），受 URL query 驱动 | `{value: number | null; onChange(v: number | null): void; projects: {id: number; name: string}[]}` | 复用 core `Select` |
| `KbImportPanel` | 拖拽/多选、规则说明、提交、取消；`accept=".json,.md,.markdown"` | `{projectId: number; onSubmit(files: File[], name?: string): Promise<void>; state: ImportState}` | 有不合规文件禁用提交；不前端解析 `index.json` 结构（结构错误由服务端返回） |
| `KbFileValidationList` | 逐文件校验结果（通过 / 类型 / 大小 / 数量 / 合计） | `{files: FileValidation[]; onRemove(index: number): void}` | 原因文案固定，不回显文件内容 |
| `KbImportReport` | 成功/部分/新版本/失败报告：已导入 N 条、跳过 M 条（行号 + 原因）、未匹配文件、新版本提示 | `{report: ImportReport; versionBumped: boolean; previousVersion?: number}` | 只展示标识、行号、原因码，不展示正文 |
| `KbBrowseLayout` | 浏览页布局：筛选栏 + 类型分栏 + 列表 | `{kbId: string; version: number; superseded: boolean; onSelectVersion(kbId: string): void}` | 默认最新版（AC-013-4） |
| `KbTypeTabs` | 八类分栏（全部/术语/实体/状态/业务规则/流程/接口/领域事件/其他）+ 计数 | `{value: EntryType | null; counts?: CountsByType; onChange(t: EntryType | null): void}` | 计数来自 `countsByType`，与主查询同条件 |
| `KbSearchBox` | 编号前缀 / 完整编号 / 关键词检索，300ms 防抖 | `{value: string; onChange(q: string): void; placeholder?: string}` | `q` ≤100；空态友好 |
| `KbEntryList` | 条目行：编号（mono）+ 标题 + 类型 + 所属知识库与版本 + 徽标 | `{items: EntryListItem[]; selected?: string[]; onToggle?(entryId: string): void; onOpen?(entryId: string): void}` | 编号与代码路径用 `--font-family-mono`；标题按纯文本渲染 |
| `KbEntryDetail` | 详情：摘要（始终）、正文（存在时）、字段/表/代码路径（缺失「—」）、一跳邻居（可跳转）、来源文件、新鲜度 | `{entry: KnowledgeEntryDetail}` | 正文按纯文本渲染，不渲染 HTML/Markdown，无源文件下载 |
| `KbFreshnessBadge` | `fresh` / `stale`（可能过期）/ `unknown`（未知） | `{state: "fresh" | "stale" | "unknown"; at?: string | null}` | 用中性/warning 徽标，不用 destructive；同时用文字 + 颜色 |
| `KbConflictNotice` | 版本冲突：列出知识库名 + 版本 + 生成时间（≤20），注明「只提示，不阻止注入」 | `{conflicts: ConflictSource[]; variant?: "list" | "detail"}` | 只提示不阻断（ADR-116 / AC-015-4） |
| `KbVersionSelector` | 版本下拉；旧版本标「只读」 | `{versions: KbVersion[]; currentKbId: string; onChange(kbId: string): void}` | 默认最新版；旧版本只读 |
| `KbDeletedBadge` | 「知识库已删除」标记 | `{kbName?: string}` | 用于历史记录与已被删除的关联展示；不改写历史数据 |

## 对话框（2）

| 组件 | 职责 | Props | 约束 |
|------|------|-------|------|
| `KbDeleteDialog` | 二次确认删除；列明级联范围（知识库及全部版本、条目索引、已存文件、项目关联），说明历史记录不变 | `{open: boolean; kb: KnowledgeBaseSummary; affectedVersions: number; entryCount: number; fileCount: number; onConfirm(): Promise<void>; onCancel(): void}` | 复用 core `ConfirmDialog`（Radix AlertDialog）；无撤销；删除中禁用按钮 |
| `KbInvalidEntryDialog` | 见上方嵌入组件 | — | 阻塞式：未确认不得发起调用 |

## 状态与数据流

- 服务端状态全部走 TanStack Query（`hooks/`），不在组件内自行维护缓存；**预览字符数以服务端 `preview` 为准**，前端只做即时本地镜像（同一模板、`[...text].length`）以降低延迟。
- 选择器不自动刷新（UXAMB-003）：勾选后发起前统一以 `/ai/complete` 的 409 结果为准；失效项取消勾选并标「不可用」，其余勾选保留（UXAMB-002）。
- 查询 key：`["kb", "list", {projectId, cursor}]`、`["kb", kbId, "detail"]`、`["kb", kbId, "versions"]`、`["kb", "entries", {projectId, kbId, type, q, cursor}]`、`["kb", entryId]`、`["kb", sessionId, "candidates", {q, type, cursor}]`、`["kb", sessionId, "preview", {refsKey, prompt}]`。
- 变更后失效：导入成功失效 `["kb"]` 前缀；删除成功失效 `["kb"]`；勾选变化不请求候选列表（只请求 preview，防抖 250ms）。

## 无障碍与响应式

- 全部交互元素可见焦点环（core token）；状态同时用文字与颜色（不只靠颜色）；按钮 ≥44×44px。
- ≤768px 时侧边栏走 core 的抽屉行为；表格在窄屏改为卡片列表（复用既有断点，不新增断点变量）。
- 输入框带 label；对话框焦点陷阱与回退由 core `ConfirmDialog` 提供；错误摘要用 `role="alert"`。

## 复用清单

- 复用（不重做）：`AuthGate`、`AppShell`、`components/ui/*`、`lib/api/client.ts`、`lib/api/errors.ts`、`lib/api/keys.ts`、`styles/tokens.css`、`styles/global.css`、`QueryClient`、`Toast`。
- 新增（本 spec）：上述 4 个页面 + 17 个组件 + 7 个 hooks + 类型与 API 封装。
- 不新增：任何 design token、任何第三方 UI 库、任何 Markdown/HTML 渲染器。
