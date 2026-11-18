# Interaction Design Context → technical-design

## 模块名称

repo-integration（workbench-core 的增量；本 spec 只交付仓库集成）

## 页面与路由

| 路由 | 页面 | 覆盖 US | 与 core 的关系 |
|------|------|---------|---------------|
| `/projects` | 项目上下文 | US-017 / US-018 / US-019 / US-020 / US-023 | core 页面扩展：保留「左项目列表 / 右项目详情」两栏（仓库地址降级为自由备注），详情表单下方新增整行纵向「仓库绑定」区块 |
| `/projects/:projectId/repos/:bindingId` | 仓库浏览 | US-020 / US-021 / US-022 / US-023 | 新增页面：选择器 + 目录树 + 提交 + 文件抽屉；解绑后同路由进入只读快照态 |

侧边栏「基座管理」新增「仓库浏览」；登录态沿用 core `AuthGate`，不新建账号体系。

## 组件清单摘要

| 组件名 | 用途 | 状态列表 |
|--------|------|---------|
| RepoBindingPanel | 项目上下文页「仓库绑定」区块容器 | default / loading / empty / error / success |
| RepoBindingList / RepoBindingRow | 绑定列表与单行（提供商、仓库、掩码、测试、同步、基线） | default / loading / empty / error；connected / unverified / token-invalid / revoked / syncing |
| RepoStatusBadge | 绑定状态徽标 | unverified / connected / token-invalid / revoked / syncing |
| RepoBindingForm | 新增绑定 / 更新令牌 | create / update-token / validating / testing / submitting / error / success |
| ProviderSegmented / TokenField | 提供商切换、掩码令牌输入 | yunxiao / github；create / update-empty / update-filled / invalid |
| ConnectionTestBadge（复用 core） | 四类连通性结果与「已失效」，扩展 `permission-denied` / `stale` | idle / testing / success / auth-error / unreachable / timeout / permission-denied / stale |
| SyncControl / SyncRecordTable | 同步按钮、上次同步摘要、同步记录 | idle / syncing / success / error / never-synced；collapsed / expanded / empty |
| TokenExpiryHint / TokenInvalidBanner | 过期提示、页面级失效聚合提示 | none / normal / expiring / expired；hidden / visible / recovering |
| RepoPicker / BranchPicker | 仓库与分支选择器（实时、检索、默认项） | default / loading / empty / error / disabled |
| CommitList / CommitRow | 提交列表与单条提交 | default / loading / success / empty / error |
| RepoTree / TreeNode | 目录树逐级展开、还有更多、截断提示 | default / loading / expanded / truncated / disabled / error |
| FileViewerDrawer | 文件内容抽屉与拒绝态 | loading / success / too-large / binary / invalid-path / network-error / empty |
| UnbindDialog / RevokedBindingRow | 解绑确认、已解绑只读行 | default / confirm-loading / error；revoked / loading-snapshot / empty-snapshot |
| ProjectInfoCard | core 项目资料 + 仓库地址自由备注 | default / saving-remark / error |

复用 core 的 `StatusPill` / `EmptyState` / `ErrorState` / `Skeleton` / `Toast` / `ConfirmDialog` / `FormField` / `AppShell`，不重定义视觉。

## Design Tokens 摘要

- 全部沿用 workbench-core，Light / Dark 两套值不变；本 spec 只新增 3 条：
  - `--color-overlay`：`rgba(15,23,42,0.45)` / `rgba(0,0,0,0.65)`（抽屉与对话框遮罩，非文本）
  - `--spacing-5`：`20px`（目录树单级缩进）
  - `--repo-drawer-width`：`480px`（文件抽屉；≤768px 时 100%）
- 主色 `--color-primary` = `#1E293B` / `#EDEDED`；字体 `--font-family-base` = `"IBM Plex Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif`；基础间距 `--spacing-4` = `16px`。
- 状态色：已连接 / 成功 = `--color-success`；令牌失效 / 鉴权失败 / 超限 = `--color-destructive`；即将过期 / 权限不足 / 限流 / 截断 = `--color-warning`；同步中 = `--color-info`；未验证 / 已解绑 = `--color-muted-foreground` + `--color-border`。
- 完整清单见 `design.md`「Design Tokens」与 `docs/design-system.md`。

## 关键交互约定

- **单一事实来源**：绑定列表为准；core「仓库地址」为自由备注，固定 hint「人工备注，实际拉取以下方「仓库绑定」为准」（AMB-030）。
- **测试连接**：保存前可用表单当前值测试，不落库、不写日志；四类结果（成功 / 鉴权失败 / 网络失败 / 权限不足）不互相误归类；复用 core 的 `ConnectionTestBadge`；任一字段变更后徽标转灰并标「已失效（时间 · 结果）」（AMB-028）。
- **同步**：手动触发，同一绑定禁止并发（按钮「同步中…」+ 禁用）；成功更新上次同步时间 / 耗时 / 基线；失败保留上次成功元数据与时间；限流展示可重试时间，不自动重试、不轮询。
- **新鲜度**：仓库 / 分支 / 提交列表与目录树实时读取（供应商分页）；同步快照只作「对照过哪个提交」的基线与令牌失效时的 last-known，界面单独展示并标注时间（AMB-026 / AMB-027）。
- **浏览**：选择器默认绑定仓库与默认分支；未同步为空态 +「去同步」，不返回错误页；目录树逐级展开，分页未给全显示「还有更多」，供应商 `truncated` 显示「目录树不完整，请逐级浏览」。
- **读文件**：右侧 480px 抽屉；展示路径 / ref / 大小 / 读取时间 / 内容；> 1 MiB（1,048,576 字节）拒绝并显示大小与上限；二进制 / 非 UTF-8 拒绝预览；路径含 `..`、绝对路径或非法 ref 在请求前拒绝且不产生读取记录；内容不写会话制品与 AiCallRecord。
- **令牌**：始终掩码（如 `ghp_****abcd`）；编辑留空表示不修改；更新令牌只替换令牌与掩码；失效时全页只出现一条聚合横幅，不重复弹错；测试成功并保存后恢复「已连接」。
- **解绑**：二次确认并列出五条后果；确认后令牌「—」、不再请求；绑定行置灰保留，快照只读；目录树 / 读文件 / 同步 / 更新令牌 / 解绑入口置灰（`aria-disabled`，不发起请求）；重新绑定生成新 bindingId。
- **错误分级**：字段级（就近）、区块级（ErrorState + 重试）、页面级（Banner）、全局 Toast 仅用于成功、模态仅用于解绑确认。
- **可访问性**：可见焦点环、Tab 顺序、Enter / Space 激活、Esc 关闭抽屉与对话框并归还焦点、图标按钮 `aria-label`、状态不只靠颜色、尊重 `prefers-reduced-motion`；1440px 无横向滚动，≤768px 侧边栏转抽屉、文件抽屉全宽。

## 待技术方案承接

- 供应商适配器的四类错误映射（401 / 403 → 令牌失效；超时 / DNS / 拒绝 → 网络失败；403 且令牌有效 → 权限不足；429 / `X-RateLimit-Remaining: 0` → 限流）。
- 分页响应头（云效 `x-total` / `x-page`、GitHub `Link` 与 `X-RateLimit-*`）与目录树 `truncated` 的读取。
- 同步互斥、快照保留策略、文件读取记录的字段与审计边界。
- 令牌加密沿用 core AMB-005，仓库令牌独立密钥环境变量 `AW_REPO_TOKEN_KEY`（AMB-029）。

## 状态

pending-confirmation（待用户确认交互设计阶段；UXAMB-011 ~ UXAMB-015 见 `open-questions.md`，确认后由 `kb-sync` 提升为 confirmed）
