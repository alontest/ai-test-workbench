# Component Tree（组件树）— workbench-core

> **文档状态：draft — 2026-11-18 因跨 spec 知识库注入扩展（A101 / A102 / A103 B）变更，待用户重新确认。**

> 阶段：tech-design（步骤 4，`ui=yes`）。依据 `interaction-design/design.md`（2026-11-18 重新确认）、`interaction-design/docs/context.md`、`docs/design-system.md`。
> 技术：React 19 + TypeScript + Vite + React Router + TanStack Query + Radix Primitives + CSS Modules（ADR-002 / ADR-007）。
> 视觉：**只消费 interaction-design 的 Design Tokens，不新增任何颜色/字号/间距/圆角/阴影变量**；token 落在 `web/src/styles/tokens.css`，组件内只用 `var(--…)` 与 CSS Modules。

## 组件层级总览

### Atoms（基础元素）

| 组件名 | 文件路径 | Props | 状态 | 复用 |
|--------|---------|-------|------|------|
| `Button` | `components/ui/Button.tsx` | `variant`、`size`、`loading`、`disabled`、`onClick` | `default/hover/focus/loading` | 全站 |
| `IconButton` | `components/ui/IconButton.tsx` | `label`、`icon`、`onClick`、`disabled` | 同上 | 表格/时间线 |
| `Input` / `Textarea` | `components/ui/Input.tsx` | 原生属性 + `invalid` | `default/focus/invalid/disabled` | 全部表单 |
| `Select` | `components/ui/Select.tsx` | `options`、`value`、`onChange`、`placeholder` | `closed/open/invalid` | 筛选/表单 |
| `Switch` | `components/ui/Switch.tsx` | `checked`、`onChange`、`disabled` | `on/off` | 提供商/模型启停 |
| `Badge` / `StatusPill` | `components/ui/Badge.tsx` | `status`、`label`、`tone?` | — | 全站 |
| `Spinner` / `Skeleton` | `components/ui/Loading.tsx` | `variant`、`rows?` | — | 全站 |
| `Tooltip` | `components/ui/Tooltip.tsx` | `content`、`children` | `hidden/visible` | 参数说明/掩码 |

### Molecules（功能单元）

| 组件名 | 文件路径 | 包含 | Props | 状态 |
|--------|---------|------|-------|------|
| `FormField` | `components/ui/FormField.tsx` | label + Input | `label`、`error?`、`required?`、`children` | — |
| `SecretField` | `features/providers/SecretField.tsx` | FormField + Input | `maskedValue`、`value`、`onChange` | `pristine/dirty` |
| `CharacterCounter` | `features/composer/CharacterCounter.tsx` | 文本 | `value`、`max` | `normal/warning/exceeded` |
| `ConnectionTestBadge` | `features/providers/ConnectionTestBadge.tsx` | Button + Badge | `state`、`result`、`onTest`、`disabled` | 7 态 |
| `AuthBanner` | `features/auth/AuthBanner.tsx` | Badge + 文本 | `tone`、`message`、`countdownSeconds?` | — |
| `EmptyState` / `ErrorState` | `components/ui/Feedback.tsx` | Icon + Button | `title`/`message`、`onRetry?` | `retryable/fatal` |
| `ConfirmDialog` | `components/ui/ConfirmDialog.tsx` | Radix AlertDialog + Button | `open`、`title`、`description`、`onConfirm`、`onCancel` | `default/confirm-loading` |

### Organisms（页面区块）

| 组件名 | 文件路径 | 包含 | 关联 US |
|--------|---------|------|---------|
| `AppShell` / `SidebarNav` / `UserMenu` | `app/*` | Atoms + 路由 | US-001 / US-011 |
| `EntranceGrid` / `EntranceCard` | `features/entrances/*` | Badge + Link | US-001 |
| `ProviderTable` / `ProviderForm` | `features/providers/*` | FormField、SecretField、ConnectionTestBadge | US-003 |
| `ModelTable` / `ModelForm` | `features/models/*` | FormField、Switch | US-004 |
| `ProjectList` / `ProjectForm` | `features/projects/*` | FormField | US-008 |
| `SessionTable` / `SessionFilters` / `CreateSessionDialog` | `features/sessions/*` | Badge、Select | US-009 |
| `SessionHeader` / `SessionTimeline` / `TimelineEvent` | `features/sessions/*` | StatusPill、四类事件卡 | US-009 |
| `TextComposer` / `FileUploader` / `CallPanel` | `features/composer/*`、`features/calls/*` | CharacterCounter、ArtifactCard | US-005~007 |
| `CallFilters` / `CallRecordTable` | `features/calls/*` | Select、Badge | US-010 |

### Pages

| 页面 | 文件路径 | 路由 | 关联 US |
|------|---------|------|---------|
| `LoginPage` | `features/auth/LoginPage.tsx` | `/login` | US-011 |
| `HomePage` | `features/entrances/HomePage.tsx` | `/` | US-001 |
| `EntrancePage` | `features/entrances/EntrancePage.tsx` | `/entrances/:key` | US-002 |
| `ProvidersPage` | `features/providers/ProvidersPage.tsx` | `/providers` | US-003 |
| `ModelsPage` | `features/models/ModelsPage.tsx` | `/providers/:id/models` | US-004 |
| `ProjectsPage` | `features/projects/ProjectsPage.tsx` | `/projects` | US-008 |
| `SessionsPage` | `features/sessions/SessionsPage.tsx` | `/sessions` | US-009 |
| `SessionDetailPage` | `features/sessions/SessionDetailPage.tsx` | `/sessions/:id` | US-005~007 / US-009 |
| `CallsPage` | `features/calls/CallsPage.tsx` | `/calls` | US-010 |

## 1. 页面与路由树

```text
App
├── LoginPage (/login)                        —— 唯一免认证页面
└── AuthGate                                 —— GET /auth/session；未认证 → /login?next=
    └── AppShell
        ├── SidebarNav / Topbar / UserMenu
        └── <Outlet/>
            ├── HomePage (/)
            │   ├── EntranceGrid → EntranceCard ×6
            │   └── RecentSessionTable
            ├── EntrancePage (/entrances/:key)
            │   └── PlaceholderPanel（planned） | 域功能页（live，壳位预留）
            ├── ProvidersPage (/providers)
            │   ├── ProviderTable
            │   └── ProviderDialog → ProviderForm + SecretField + ConnectionTestBadge
            ├── ModelsPage (/providers/:id/models)
            │   ├── ModelTable
            │   └── ModelDialog → ModelForm
            ├── ProjectsPage (/projects)
            │   ├── ProjectList
            │   └── ProjectDialog → ProjectForm
            ├── SessionsPage (/sessions)
            │   ├── SessionFilters
            │   ├── SessionTable
            │   └── CreateSessionDialog
            ├── SessionDetailPage (/sessions/:id)
            │   ├── SessionHeader → StatusPill
            │   ├── SessionTimeline → TimelineEvent（InputEventCard / CallEventCard / ArtifactEventCard / StatusChangeEvent / KnowledgeInjectionEventCard）
            │   └── SidePanel (Tabs)
            │       ├── TextComposer → CharacterCounter
            │       ├── FileUploader → ArtifactCard
            │       └── CallPanel → CharacterCounter + AdvancedParams
            └── CallsPage (/calls)
                ├── CallFilters
                └── CallRecordTable → CallRecordRow（展开核对）
```

## 2. 组件清单

### 2.1 应用骨架与认证

| 组件 | 职责 | Props | 内部状态 / 状态机 | 依赖 | 关联 |
|------|------|-------|------------------|------|------|
| `App` | 路由、QueryClientProvider、ToastProvider | — | — | React Router、TanStack Query | 全部 |
| `AuthGate` | 启动校验登录态；未认证跳登录并保留 `next`（只接受站内路径） | `children` | `checking / authenticated / redirecting / expired` | `useAuthSession` | US-011 / AC-011-1 |
| `LoginPage` | 单卡片登录；口令掩码；回车提交；锁定倒计时 | `next`（query） | `default / submitting / error / locked / expired / logged-out` | `useLogin`、`AuthBanner`、`PasswordField` | US-011 |
| `PasswordField` | 口令输入（type=password，不提供显示切换） | `value`、`onChange`、`disabled`、`error` | `focused` | `FormField` | AC-011-3 |
| `AuthBanner` | 登录页 banner：错误 / 锁定（`mm:ss`）/ 过期 / 已退出 | `tone`、`message`、`countdownSeconds?` | — | — | AC-011-3/4/5/6 |
| `AppShell` | 侧边栏 248px + 顶栏 64px + 内容区（最大 1280px）；≤768px 抽屉 | `children` | `drawerOpen`（移动端） | `SidebarNav`、`UserMenu` | US-001 |
| `SidebarNav` | 分组导航：工作入口（6）/ 基座管理（项目、提供商、会话、调用记录）；激活态与焦点环 | `items`、`activePath`、`onNavigate` | `hoveredId` | NavLink | AC-001-2 |
| `UserMenu` | 顶栏「管理员 ▾」→ 退出登录（不二次确认） | `onLogout` | `open / logging-out` | Radix DropdownMenu、`useLogout` | US-011 / AC-011-6 |

### 2.2 首页与入口

| 组件 | 职责 | Props | 状态 | 依赖 | 关联 |
|------|------|-------|------|------|------|
| `HomePage` | 并行取入口与最近 10 条会话 | — | 由 query 派生 | `useEntrances`、`useSessions({limit:10})` | AC-001-1/3 |
| `EntranceGrid` | 6 卡片网格，配置驱动 | `entrances` | — | `EntranceCard` | AC-001-1 |
| `EntranceCard` | 名称、一句用途、所属域、`planned/live` 徽标；整卡链接；Enter 激活 | `entrance` | `hover / focus` | React Router Link、`StatusPill` | AC-001-2 / AC-002-1 |
| `RecentSessionTable` | 最近会话，按更新时间倒序；空态 | `sessions`、`loading`、`error`、`onRetry` | `loading / success / empty / error` | `SessionTable`（紧凑模式） | AC-001-3 |
| `EntrancePage` | 按 `key` 查配置；planned → 占位；live → 预留功能挂载点 | `key` | `planned / live / config-missing` | `useEntrances` | AC-002-1/2/3 |
| `PlaceholderPanel` | 说明所属域与状态、返回首页；不创建会话、不请求模型 | `entrance` | — | Link | AC-002-1/2 |

### 2.3 提供商与模型

| 组件 | 职责 | Props | 状态 | 依赖 | 关联 |
|------|------|-------|------|------|------|
| `ProvidersPage` | 列表 + 新建/编辑对话框 + 连接测试入口 | — | — | `useProviders`、mutations | US-003 |
| `ProviderTable` | 名称、协议、baseURL、掩码密钥、启用开关、操作 | `providers`、`onEdit`、`onToggle`、`onTest` | `loading / success / empty / error` | 表格、`StatusPill` | AC-003-1/4 |
| `ProviderDialog` | Radix Dialog 容器；Esc 关闭并归还焦点 | `open`、`provider?`、`onClose` | `create / edit` | Radix Dialog | US-003 |
| `ProviderForm` | 名称、协议下拉、baseURL、密钥、启用；逐字段错误 | `initialValue`、`mode`、`onSubmit` | `default / editing / validating / submitting / error / create / edit-unchanged` | `SecretField`、`FormField` | AC-003-1/2 |
| `SecretField` | 掩码展示（`sk-****abcd`）；编辑留空 = 不修改；密码输入 | `maskedValue`、`value`、`onChange`、`placeholder` | `pristine / dirty` | `FormField` | UXAMB-006 |
| `ConnectionTestBadge` | 测试按钮与结果徽标；改动表单后结果失效 | `state`、`result`、`onTest`、`disabled` | `idle / testing / success / auth-error / unreachable / timeout / credential-unavailable` | `useConnectionTest` | AC-003-3 |
| `ModelsPage` | 当前提供商下的模型列表与新建/编辑 | `providerId` | — | `useProvider`、`useModels` | US-004 |
| `ModelTable` | 模型名、显示名、默认参数、启用开关 | `models`、`onEdit`、`onToggle` | `loading / success / empty / error` | 表格 | AC-004-1 |
| `ModelForm` | 模型名、显示名、temperature（0–2）、max_tokens（正整数） | `providerId`、`initialValue?` | `default / validating / duplicate / submitting / error` | `FormField` | AC-004-1/2 |

### 2.4 项目

| 组件 | 职责 | Props | 状态 | 依赖 | 关联 |
|------|------|-------|------|------|------|
| `ProjectsPage` | 项目列表 + 新建/编辑 | — | — | `useProjects` | US-008 |
| `ProjectList` | 名称、仓库地址、技术栈、更新时间；空态 | `projects`、`onEdit` | `loading / success / empty / error` | 表格 | AC-008-2 |
| `ProjectForm` | 项目名（唯一）、仓库地址、技术栈、需求来源、备注 | `initialValue?`、`mode` | `create / editing / validating / duplicate / error` | `FormField` | AC-008-1/2 |

### 2.5 会话与输入

| 组件 | 职责 | Props | 状态 | 依赖 | 关联 |
|------|------|-------|------|------|------|
| `SessionsPage` | 列表、筛选、新建入口 | — | — | `useSessions` | US-009 |
| `SessionFilters` | 项目、状态下拉 | `value`、`onChange`、`projects` | `default` | Select | AC-009-2 |
| `SessionTable` | 标题、项目、入口、模型、状态、更新时间；行链接详情 | `sessions`、`compact?` | `loading / success / empty / filtered-empty / error` | `StatusPill`、Link | AC-009-2 |
| `CreateSessionDialog` | 项目 + 启用模型 + 标题 + 入口；缺项目/缺模型时禁用并给配置引导 | `open`、`defaultProjectId?` | `default / missing-project / missing-model / submitting / error` | `useProjects`、`useEnabledModels` | AC-008-3 / AC-009-1 |
| `SessionHeader` | 标题、项目、模型、状态、标记完成、删除 | `session`、`onComplete`、`onDelete` | `in-progress / completed / failed` | `StatusPill`、`ConfirmDialog` | AC-009-4/5 |
| `StatusPill` | 状态徽标（进行中/已完成/失败/planned/live） | `status`、`size?` | — | token 色 | AC-002 / AC-009 |
| `SessionTimeline` | 事件升序渲染；loading / empty / error；只读态 | `sessionId`、`readOnly` | `loading / empty / success / error / read-only` | `useEvents`（infinite） | AC-009-3 |
| `TimelineEvent` | 按 `type` 分发到五类卡片；显示时间与操作 | `event` | — | 五类事件卡 | AC-009-3 / ADR-042 |
| `InputEventCard` | 标题、字数、折叠摘要、展开全文 | `payload`（`title/text/charCount`） | `collapsed / expanded` | — | AC-006-1 / AC-009-3 |
| `CallEventCard` | 模型、耗时、状态、提示摘要；失败显示重试与错误 | `payload` | `collapsed / expanded` | `StatusPill` | AC-005-4 / AC-010-2 |
| `ArtifactEventCard` | 文件名、大小、预览/下载按钮 | `payload`、`artifactId` | `default` | `useArtifactContent` | AC-007-1 |
| `StatusChangeEvent` | from → to、actor、时间、原因 | `payload` | — | — | ADR-012 |
| `KnowledgeInjectionEventCard` | 知识库名/版本、编号列表、分段字数；`kbDeleted=true` 时标「知识库已删除」；不展示正文 | `payload`（`items/promptChars/injectedChars/totalChars/excludedCodes`） | `collapsed / expanded` | Badge | A101 / ADR-042 |
| `TextComposer` | 标题 + 正文提交；实时计数；>90% 警告；超限禁用提交 | `sessionId`、`maxChars=200000`、`readOnly` | `default / counter-warning / counter-exceeded / empty-error / submitting / read-only` | `CharacterCounter`、`useAppendText` | AC-006-1/2/3 |
| `CharacterCounter` | `当前 / 上限`；>90% 警告色；超限危险色 | `value`、`max` | `normal / warning / exceeded` | token 色 | UXAMB-007 / AC-UX-19 |
| `FileUploader` | 拖拽/选择；前端三查（类型/大小/数量）；逐文件标红可移除；提交 | `sessionId`、`accept`、`maxFiles=10`、`maxFileSize=10MB`、`readOnly` | `idle / dragging / validating / rejected / uploading / success / renamed / read-only` | `ArtifactCard`、`useUploadArtifacts` | AC-007-1/2/3 |
| `ArtifactCard` | 文件名（改名后）、大小、预览/下载；预览按纯文本转义 | `artifact` | `default / previewing / error` | `useArtifactContent` | ADR-013 |
| `SidePanel` | Radix Tabs：文本 / 上传 / 发起调用；终态只读 | `session`、`readOnly` | `activeTab` | Radix Tabs | UX 会话详情 |
| `CallPanel` | 提示输入 + 字数 + 高级参数（temperature/max_tokens）；调用中禁用重复提交；调用 `POST /sessions/{id}/ai/complete`（core 面板不带 `knowledgeRefs`，知识库页面由 knowledge-base spec 传） | `session`、`readOnly`、`knowledgeRefs?` | `default / advanced-open / counter-warning / counter-exceeded / submitting / success / failed / read-only` | `useCreateCall`、`CharacterCounter` | US-005 / AC-004-3 / ADR-042 |
| `AdvancedParams` | 本次 temperature / max_tokens 覆盖；不写回模型默认 | `value`、`onChange` | `collapsed / open / invalid` | `FormField` | UXAMB-010 |

### 2.6 调用记录与通用组件

| 组件 | 职责 | Props | 状态 | 依赖 | 关联 |
|------|------|-------|------|------|------|
| `CallsPage` | 筛选 + 列表 + 展开核对 | — | — | `useCalls` | US-010 |
| `CallFilters` | 项目 → 会话级联、状态、时间范围（默认近 7 天）、清除筛选 | `value`、`onChange`、`projects` | `default / filtered` | Select、日期输入 | AC-010-1/3 / UXAMB-009 |
| `CallRecordTable` | 模型、状态、耗时、重试、时间；按时间倒序；空态 | `calls`、`loading`、`error` | `loading / success / empty / filtered-empty / error` | `CallRecordRow` | AC-010-1/3 |
| `CallRecordRow` | 行展开：提示摘要、错误信息、结果全文（成功）、知识库注入快照（`knowledgeInjection`，含 `kbDeleted` 标记） | `call` | `collapsed / expanded` | Badge | AC-010-2 / ADR-042 |
| `ConfirmDialog` | 破坏性操作二次确认；展示级联范围；确认中 loading | `open`、`title`、`description`、`confirmLabel`、`onConfirm`、`onCancel`、`danger?` | `default / confirm-loading` | Radix AlertDialog | AC-009-5 |
| `EmptyState` | 空态图标/文案/可选操作 | `title`、`description`、`action?` | — | — | 各列表 |
| `ErrorState` | 错误文案 + 重试 | `message`、`onRetry?`、`retryable?` | `retryable / fatal` | — | 各列表 |
| `Toast` | 成功/失败/信息提示；不承载表单字段错误 | `tone`、`message` | `visible / dismissed` | Radix Toast | 全局 |
| `Skeleton` | 列表/时间线加载占位；尊重 `prefers-reduced-motion` | `variant`、`rows?` | — | — | 各三态 |
| `FormField` | label、必填标记、错误文本、`aria-describedby`、错误 `aria-invalid` | `label`、`error?`、`required?`、`children` | — | — | 所有表单 |
| `Modal` / `Dialog`（Radix 包装） | 焦点陷阱、Esc 关闭、归还焦点、`aria-modal` | `open`、`onOpenChange`、`title` | — | Radix Dialog | 各对话框 |

## 3. 数据获取与缓存（TanStack Query）

| Query key | 端点 | 失效时机 |
|-----------|------|---------|
| `['auth','session']` | `GET /auth/session` | 登录、登出、401 |
| `['entrances']` | `GET /entrances` | 静态长缓存（`staleTime: Infinity`） |
| `['projects', filters]` | `GET /projects` | 项目创建/编辑 |
| `['providers']` | `GET /providers` | 提供商创建/编辑/启停 |
| `['providers', id, 'models']` | `GET /providers/{id}/models` | 模型创建/编辑 |
| `['models', filters]` | `GET /models` | 模型创建/编辑、提供商启停；新建会话对话框选择启用模型 |
| `['sessions', filters]` | `GET /sessions` | 会话创建/结束/删除、事件追加、调用/上传完成 |
| `['sessions', id]` | `GET /sessions/{id}` | 同上 |
| `['sessions', id, 'events']` | `GET /sessions/{id}/events`（infinite） | 追加文本/上传/调用/状态变更 |
| `['artifacts', id]` | `GET /artifacts/{id}` | 会话删除 |
| `['calls', filters]` | `GET /calls` | 调用完成、会话删除 |

- 统一 `ApiError` 类型：`{code, message, details, requestId}`；`code === 'unauthorized'` 由全局拦截器处理，其余由页面按 `code` 分支。
- 失败重试：GET 默认 1 次（401/403/404 不重试）；调用与上传不自动重试（避免重复副作用）。
- 乐观更新仅限「启用开关」；其余写完 `invalidateQueries`。

## 4. 样式与可访问性约定

- token 来源：`interaction-design/design.md`「Design Tokens」与 `docs/design-system.md`；`tokens.css` 只做变量声明，不做二次语义命名。
- 暗色优先：默认 `prefers-color-scheme` + 显式 `data-theme`；两套取值均已验证对比度 ≥4.5:1。
- 焦点：所有交互元素可见焦点环（`--color-ring`）；Radix 负责对话框焦点陷阱与 Esc 归还。
- 图标按钮带 `aria-label`；状态徽标除颜色外带文字；倒计时用 `aria-live="polite"`。
- ≤768px：侧边栏转抽屉；时间线与侧面板改为上下堆叠。
- 不引入带主题的组件库；不新增设计 token（若实现需要新 token，回到 interaction-design 阶段，不在本阶段自造）。

## Props 接口定义

```ts
type Status = 'in_progress' | 'completed' | 'failed' | 'planned' | 'live';

interface StatusPillProps {
  status: Status;
  size?: 'sm' | 'md';
}

interface FormFieldProps {
  label: string;
  error?: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}

interface SecretFieldProps {
  maskedValue?: string;          // 编辑态显示 sk-****abcd
  value: string;                 // 新建/修改时的明文，只在内存
  onChange: (next: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

interface CharacterCounterProps {
  value: number;
  max: number;                   // 默认 200000
}

type ConnectionTestState =
  | 'idle' | 'testing' | 'success'
  | 'auth-error' | 'unreachable' | 'timeout' | 'credential-unavailable';

interface ConnectionTestBadgeProps {
  state: ConnectionTestState;
  result?: { ok: boolean; latencyMs: number; modelCount?: number; errorCode?: string };
  onTest: () => void;
  disabled?: boolean;
}

interface EntranceCardProps {
  entrance: { key: string; name: string; description: string; domain: string; status: 'planned' | 'live' };
}

interface SessionTableProps {
  sessions: SessionSummary[];
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  compact?: boolean;             // 首页最近 10 条
}

interface TextComposerProps {
  sessionId: number;
  maxChars?: number;             // 默认 200000
  readOnly: boolean;
  onSubmitted: () => void;
}

interface FileUploaderProps {
  sessionId: number;
  accept: string[];              // 白名单扩展名
  maxFiles?: number;             // 默认 10
  maxFileSize?: number;          // 默认 10MB
  readOnly: boolean;
  onUploaded: () => void;
}

interface CallPanelProps {
  session: SessionDetail;
  readOnly: boolean;
  maxChars?: number;
  onCompleted: () => void;
}

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}
```

## 可复用组件清单

| 组件 | 复用场景 | 注意事项 |
|------|---------|---------|
| `StatusPill` | 会话状态、入口 planned/live、调用状态 | 颜色之外必须有文字，满足非颜色可辨 |
| `FormField` | 所有表单 | 错误态设置 `aria-invalid` 与 `aria-describedby` |
| `CharacterCounter` | 文本粘贴、调用提示 | 同一上限常量（200,000）由常量模块导出，不在组件内写死 |
| `ConfirmDialog` | 删除会话、标记完成 | 删除时 `description` 必须列出级联范围 |
| `EmptyState` / `ErrorState` | 所有列表与时间线 | 空态与错误态不混用；错误态提供重试 |
| `ConnectionTestBadge` | 提供商新建/编辑 | 表单字段变更后结果失效（回到 `idle`） |
| `Skeleton` | 列表/时间线加载 | 尊重 `prefers-reduced-motion` |
| `ArtifactCard` | 时间线、上传结果 | 只读；预览按纯文本转义，禁止 `dangerouslySetInnerHTML` |
