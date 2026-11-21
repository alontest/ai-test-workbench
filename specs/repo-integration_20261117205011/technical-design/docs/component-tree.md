# Component Tree — repo-integration

> 阶段：tech-design（步骤 4，`ui=yes`）。上游：`interaction-design/design.md`（组件清单 548~576 行、Design Tokens 461~546 行）、`interaction-design/docs/context.md`（已确认）、`docs/architecture-decisions.md`（ADR-202 / ADR-214）。
> **本 spec 不新增视觉体系**。只使用 interaction-design 已定义的 token（`--color-*`、`--spacing-1..8`、`--radius-*`、`--shadow-*`、`--repo-drawer-width`、`--font-family-mono`）与 core 的 `web/src/components/ui/*`（Button / IconButton / Input / Select / Badge / ConfirmDialog / FormField / Feedback / Loading / Modal / Tooltip）。新增 token 仅 `--color-overlay`、`--spacing-5`、`--repo-drawer-width` 三个，追加在 `web/src/styles/tokens.css`。
> 落地目录：`web/src/features/repos/`（ADR-202 的 `frontend/src/repos/` 按 core 既有前端根对齐）。全部页面在 core `AuthGate` + `AppShell` 内渲染。

## 1. 项目上下文页增量（core `ProjectsPage`）

```
AuthGate (core)
└── AppShell (core: 侧边栏 248px / 顶栏 64px / 内容 1280px)
    └── /projects ───────────────────────── ProjectsPage (core，两栏)
        ├── ProjectList (core)
        ├── ProjectDetail / ProjectForm (core)
        │   └── 仓库地址（自由备注，AMB-030）
        └── RepoBindingPanel                  ← 本 spec 挂载：data-mount="repo-binding-panel"
            ├── TokenInvalidBanner            ← 页面级唯一聚合横幅
            ├── RepoBindingList
            │   ├── RepoBindingRow
            │   │   ├── RepoStatusBadge
            │   │   ├── TokenExpiryHint
            │   │   ├── SyncControl
            │   │   └── SyncRecordTable（折叠）
            │   ├── RevokedBindingRow
            │   │   ├── RepoStatusBadge
            │   │   └── SyncRecordTable（只读）
            │   └── EmptyState (core)
            ├── RepoBindingForm               ← 「+ 添加绑定」就地展开
            │   ├── ProviderSegmented
            │   ├── TokenField
            │   ├── RepoPermissionHint
            │   └── ConnectionTestBadge (core，扩展)
            └── UpdateTokenForm               ← 「更新令牌」
                ├── TokenField
                └── ConnectionTestBadge (core，扩展)
```

### 挂载约定

| 约定 | 值 | 说明 |
|------|----|------|
| 挂载宿主 | `web/src/features/projects/ProjectsPage.tsx` | 沿用 core 的两栏项目页；不新建页面 |
| 挂载位 | `data-mount="repo-binding-panel"` | 与 core 的 `knowledge-summary` 同级；便于 E2E 定位 |
| 数据来源 | `projectId` prop | 从当前项目读取；无项目时渲染空态，不发请求 |
| 布局 | 项目详情表单下方整行纵向区块 | interaction 决策 2；≤1180px 时随项目区块堆叠 |
| 令牌失效横幅 | 由 `RepoBindingPanel` 统一渲染 | 同一页面只出现一条，列出受影响绑定 |

## 2. 独立浏览路由

```
AppShell (core)
└── /projects/:projectId/repos/:bindingId ── RepoBrowsePage
    ├── RepoBrowseHeader
    │   ├── RepoBreadcrumb（返回项目上下文）
    │   ├── RepoStatusBadge
    │   └── TokenExpiryHint
    ├── TokenInvalidBanner (token_invalid)
    ├── RevokedNotice (revoked)
    ├── RepoBaselineStrip            ← 「上次同步基线 … 仅作对照」
    ├── RepoPicker                   ← 实时、检索、默认绑定仓库
    ├── BranchPicker                 ← 实时、分页、默认分支
    ├── RefreshButton
    ├── RepoTree
    │   ├── TreeNode × n
    │   │   ├── TreeCaret
    │   │   └── TreeNodeMeta（type / size）
    │   ├── TreeMoreLink             ← hasMore
    │   └── TreeTruncatedNote        ← truncated
    ├── CommitList
    │   ├── CommitRow × n
    │   └── CommitPager
    ├── FileViewerDrawer             ← 480px；≤768px 100%
    │   ├── FileHeader（path / ref / size / fetchedAt）
    │   ├── FileContent（<pre>，纯文本）
    │   ├── FileErrorState（too-large / binary / not-utf8 / invalid-path / network）
    │   └── FileFooterHint（不写制品与 AiCallRecord）
    └── UnbindDialog                 ← 仅从项目页「解绑」打开时可复用；浏览页不直接解绑
```

## 3. 页面组件（2）

| 组件 | 路由 / 宿主 | 职责 | Props | 状态 |
|------|------------|------|-------|------|
| `RepoBrowsePage` | `/projects/:projectId/repos/:bindingId` | 浏览页容器：选择器、目录树、提交、文件抽屉、失效/解绑只读态 | 无（读路由参数） | loading / success / unsynced / token-invalid / revoked / error |
| `RepoBindingPanel` | `ProjectsPage` 的 `data-mount="repo-binding-panel"` | 项目页增量区块：说明、绑定列表、表单、聚合横幅 | `{projectId: number, projects?: never}` | default / loading / empty / error / adding / updating-token |

## 4. 业务组件（24）

| 组件 | 职责 | Props 接口 | 关键约束 |
|------|------|-----------|---------|
| `RepoBindingList` | 绑定列表（含四种状态行与折叠同步记录） | `{bindings: RepoBindingSummary[]; loading: boolean; onTest(id): void; onSync(id): void; onBrowse(id): void; onUpdateToken(id): void; onUnbind(id): void; onRebind(id): void}` | 已解绑行排末尾；空态文案「还没有绑定仓库」 |
| `RepoBindingRow` | 单个绑定：提供商、仓库全名（mono）、状态、掩码、测试/同步/基线、操作 | `{binding: RepoBindingSummary; busy?: "testing" \| "syncing"}` | 令牌只显示 `tokenMasked`；「从未同步」不显示空白 |
| `RepoStatusBadge` | 绑定状态徽标 | `{status: "unverified" \| "connected" \| "token_invalid" \| "revoked" \| "syncing"}` | 文字 + 颜色；映射 `StatusPill` 语义色 |
| `RepoBindingForm` | 新增绑定（云效/GitHub） | `{projectId: number; open: boolean; onClose(): void; onSaved(binding): void}` | 保存前可测试且不落库；任一字段变更置 `stale` |
| `ProviderSegmented` | 提供商切换 | `{value; onChange(v): void; disabled?: boolean}` | GitHub 时 API 域名只读固定 |
| `TokenField` | 访问令牌输入 | `{value: string; onChange(v: string): void; mode: "create" \| "update"; masked?: string}` | 始终 `type="password"`；更新时留空 = 不修改；不回显完整令牌 |
| `RepoPermissionHint` | 只读最小权限说明 | 无 | 固定文案：Contents/Metadata 只读、不克隆、不建索引、不写操作 |
| `ConnectionTestBadge`（core 扩展） | 测试结果徽标 + 原因 + 下一步 | 沿用 core props，`state` 增加 `permission-denied` / `stale` | 四类结果不互相归类；不弹 Toast |
| `TokenExpiryHint` | 过期时间与「即将过期」 | `{expiresAt: string \| null}` | 无数据不显示、不推测；<7 天 warning |
| `TokenInvalidBanner` | 页面级令牌失效聚合提示 | `{bindings: RepoBindingSummary[]; onRefill(id?): void; onViewBaseline(id): void}` | 页面唯一；同一绑定只提示一次 |
| `SyncControl` | 同步按钮 + 上次同步摘要 | `{binding; syncing: boolean; onSync(): void}` | 同步中禁用并显示「同步中…」；不自动重试 |
| `SyncRecordTable` | 最近同步记录（可折叠） | `{bindingId: string; open: boolean; onToggle(): void}` | 失败行说明「保留上次成功基线与时间」；限流行给 `retryAfterAt` |
| `UpdateTokenForm` | 更新令牌 | `{binding; open; onClose(); onSaved(binding)}` | 只替换令牌与掩码；bindingId/元数据/历史不变 |
| `RevokedBindingRow` | 已解绑行（置灰、只读快照、重新绑定） | `{binding; onViewSnapshot(id): void; onRebind(id): void}` | 令牌显示「—」；不显示同步/更新令牌/解绑 |
| `RepoPicker` | 仓库选择器（实时、检索、默认绑定仓库） | `{bindingId; value: string \| null; onChange(repoId): void; disabled?: boolean}` | 300ms 防抖；未同步显示「去同步」空态 |
| `BranchPicker` | 分支选择器（实时、分页、默认分支） | `{bindingId; repoId; value: string \| null; onChange(branch): void; disabled?: boolean}` | 默认分支标「（默认）」；切换后提交与目录树重载 |
| `RepoBaselineStrip` | 上次同步基线 | `{lastSyncSuccessAt: string \| null; baseline?: {ref, sha, fetchedAt}; revoked?: boolean}` | 明确「仅作对照与失效时的 last-known」；与实时数据视觉分开 |
| `CommitList` | 提交列表 | `{items: CommitSummary[]; loading; hasMore; onLoadMore(): void}` | sha 短号 mono；倒序；空态「没有提交」 |
| `CommitRow` | 单条提交 | `{commit: CommitSummary; onClick?(): void}` | 作者/时间次要色；行可聚焦 |
| `RepoTree` | 目录树容器 | `{bindingId; repoId; ref; path; entries; truncated; hasMore; loading; onLoadMore(); onOpenFile(path); disabled?: boolean}` | `truncated` 与 `hasMore` 分别渲染；已解绑所有树行 `aria-disabled` |
| `TreeNode` | 目录 / 文件行 | `{entry: TreeEntry; depth: number; expanded: boolean; loading?: boolean; disabled?: boolean; onToggle(); onOpen()}` | 缩进 `20px × depth`（`--spacing-5`）；`DIR`/`FILE` 文本标签，不用 emoji |
| `TreeTruncatedNote` | 「目录树不完整」提示 | `{visible: boolean}` | 固定文案；`role="note"` |
| `FileViewerDrawer` | 文件查看抽屉 | `{open: boolean; target: {repoId, ref, path} \| null; onClose(): void}` | 480px / ≤768px 全宽；Esc 关闭并还焦；内容纯文本 |
| `UnbindDialog` | 解绑二次确认（五条后果） | `{open; binding; onConfirm(): Promise<void>; onCancel(): void}` | 复用 core `ConfirmDialog`；确认中禁用按钮 |
| `RepoEmptyUnsynced` | 未同步空态与「去同步」 | `{variant: "browse" \| "commits" \| "tree"; onSync(): void}` | 不返回错误页（AC-020-3） |

## 5. Hooks 与查询 key

| Hook | 端点 | 查询 key | 失效时机 |
|------|------|---------|---------|
| `useRepoBindings(projectId)` | GET `/projects/{id}/repo-bindings` | `["repo","bindings",projectId]` | 创建/更新令牌/测试/同步/解绑后失效 |
| `useRepoBinding(bindingId)` | GET `/repo-bindings/{id}` | `["repo","binding",bindingId]` | 同上 |
| `useCreateRepoBinding(projectId)` | POST | — | 失效 `["repo","bindings",projectId]` |
| `useUpdateRepoToken(bindingId)` | PATCH `/token` | — | 失效绑定与详情 |
| `useTestRepoConnection()` | POST `/test-connection`（含未保存） | — | 已保存测试成功失效绑定；未保存仅本地状态 |
| `useSyncRepo(bindingId)` | POST `/sync` | — | 失效绑定、同步记录、baseline |
| `useSyncRecords(bindingId, cursor)` | GET `/sync-records` | `["repo","sync-records",bindingId,cursor]` | 同步后失效 |
| `useUnbindRepo(projectId)` | POST `/unbind` | — | 失效绑定列表与 baseline |
| `useRepositories(bindingId, search, cursor)` | GET `/repositories` | `["repo","repositories",bindingId,{search,cursor}]` | 用户点「刷新」 |
| `useBranches(bindingId, repoId, search, cursor)` | GET `/branches` | 同上 | 同上 |
| `useCommits(bindingId, repoId, ref, cursor)` | GET `/commits` | 同上 | ref 切换 / 刷新 |
| `useRepoTree(bindingId, repoId, ref, path, cursor)` | GET `/tree` | 同上 | 展开 / 加载下一页 |
| `useRepoFile(bindingId, repoId, ref, path)` | GET `/file` | `["repo","file",bindingId,repoId,ref,path]` | 抽屉打开时按需；`staleTime=0`，不持久化 |
| `useRepoBaseline(bindingId)` | GET `/baseline` | `["repo","baseline",bindingId]` | 同步/解绑后失效 |

- 服务端状态全部走 TanStack Query；不新增全局状态库。
- 未保存测试结果只存在表单局部 state，字段变更置 `stale`；不写 localStorage / sessionStorage。
- 文件内容只在内存与 React Query 缓存中存在，组件卸载可丢弃；不持久化。

## 6. 状态与视觉映射

| 业务状态 | 组件态 | 颜色 / 文案 |
|---------|-------|------------|
| 未验证 | `unverified` | muted + border；「未验证」 |
| 已连接 | `connected` | `--color-success`；「已连接」 |
| 令牌失效 | `token_invalid` | `--color-destructive`；页面横幅「令牌失效或权限不足，请重新填写」 |
| 已解绑 | `revoked` | 整行降低透明度；「已解绑」 |
| 同步中 | `syncing` | `--color-info`；按钮「同步中…」 |
| 即将过期 | `expiring` | `--color-warning`；「即将过期 · n 天」 |
| 权限不足 | `permission-denied` | `--color-warning`；与令牌失效区分 |
| 限流 | `rate-limited` | `--color-warning`；附 `retryAfterAt`（若有） |
| 目录树不完整 | `truncated` | `--color-warning`；「目录树不完整，请逐级浏览」 |
| 还有更多 | `hasMore` | `--color-info`；「还有更多（n 条未加载）· 加载下一页」 |

## 7. 无障碍与响应式

- 全部交互元素可见焦点环（core `--color-ring`）；状态同时用文字与颜色，不只靠颜色。
- 目录树行使用 `button`，Enter / Space 展开或打开文件；已解绑时 `aria-disabled="true"` 且点击不发起请求。
- 文件抽屉：打开后焦点进入抽屉，Esc 关闭并还焦触发文件行；遮罩点击关闭；`role="dialog"` + `aria-modal="true"`。
- 解绑对话框：打开时焦点落在「取消」；模态期间背景不可聚焦；复用 core `ConfirmDialog`。
- 尊重 `prefers-reduced-motion`：抽屉与对话框过渡关闭。
- 响应式：≤1180px 项目页与浏览页单列；≤768px 侧边栏转抽屉、文件抽屉 100% 宽、选择器单列；1440px 无横向滚动。
- 错误分级：字段级 `FormField` → 区块级 `ErrorState` + 重试 → 页面级 `Banner` → 成功 `Toast`；模态仅解绑确认。

## 8. 复用清单

- 复用（不重做）：`AuthGate`、`AppShell`、`components/ui/*`、`lib/api/client.ts`、`lib/api/errors.ts`、`lib/api/keys.ts`、`styles/tokens.css`、`QueryClient`、`Toast`、`ConnectionTestBadge`（增量扩展）。
- 新增（本 spec）：2 个页面级组件（其中 1 个为挂载面板）+ 24 个业务组件 + 14 个 hooks + 类型与 API 封装。
- 不新增：design token（除已确认 3 个）、第三方 UI 库、Markdown/HTML 渲染器、前端持久化。
