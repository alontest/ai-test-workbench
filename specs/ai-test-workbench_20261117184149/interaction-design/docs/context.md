# Interaction Design Context → technical-design

## 模块名称

ai-test-workbench（本 spec 覆盖 `workbench-core` 域）

## 页面与路由

| 路由 | 页面 |
|------|------|
| `/login` | 登录页（唯一无需认证；`next` 保留原目标） |
| `/` | 工作台首页（6 入口 + 最近会话） |
| `/entrances/:key` | 入口页（planned 占位 / live 功能页） |
| `/providers` | AI 提供商配置（含连接测试） |
| `/providers/:id/models` | 模型绑定 |
| `/projects` | 项目上下文 |
| `/sessions` | 会话列表与新建会话 |
| `/sessions/:id` | 会话详情（时间线 + 文本/文件输入 + 发起调用与提示字数 + 状态流转 + 删除） |
| `/calls` | AI 调用记录查询 |

除 `/login` 外的所有路由受 `AuthGate` 保护：未认证页面跳转 `/login?next=<原路径>`，接口返回 401；`next` 只接受站内路径。

## 组件清单摘要

| 组件名 | 用途 | 状态列表 |
|--------|------|---------|
| AuthGate | 路由级登录拦截与原目标回跳 | checking / authenticated / redirecting / expired |
| LoginPage / PasswordField / AuthBanner | 登录表单、口令输入与状态提示 | default / submitting / error / locked / expired / logged-out |
| UserMenu | 顶栏用户区与登出 | default / open / logging-out |
| AppShell / SidebarNav | 侧边栏 + 顶栏 + 内容区，分组导航 | default / collapsed / hover / focus / active |
| EntranceCard / PlaceholderPanel | 首页入口与未交付占位 | default / hover / planned / live / config-missing |
| RecentSessionTable / SessionTable | 最近会话与会话列表 | loading / success / empty / filtered-empty / error |
| ProviderTable / ProviderForm / SecretField | 提供商与掩码密钥 | default / editing / validating / submitting / error / create / edit-unchanged |
| ConnectionTestBadge | 连接测试结果 | idle / testing / success / auth-error / unreachable / timeout |
| ModelTable / ModelForm | 模型绑定与参数校验 | default / validating / duplicate / submitting / error / empty |
| ProjectList / ProjectForm | 项目上下文 CRUD | create / editing / validating / duplicate / error / empty |
| CreateSessionDialog | 新建会话前置校验 | default / missing-project / missing-model / submitting / error |
| SessionHeader / StatusPill | 会话状态与操作 | in-progress / completed / failed / planned / live |
| SessionTimeline / TimelineEvent | 事件时间线 | loading / empty / success / error / read-only / input / call-success / call-failed / artifact |
| TextComposer / CharacterCounter | 文本粘贴与正文/提示字数 | default / counter-warning / counter-exceeded / empty-error / submitting / read-only |
| FileUploader / ArtifactCard | 文件上传与制品预览 | idle / dragging / validating / rejected / uploading / success / renamed / read-only |
| CallPanel | 发起调用与本次参数覆盖（含提示字数预算） | default / advanced-open / counter-warning / counter-exceeded / submitting / success / failed / read-only |
| CallRecordTable / CallFilters | 调用记录查询 | default / loading / empty / error / filtered |
| ConfirmDialog / EmptyState / ErrorState / Toast / Skeleton / FormField | 通用反馈组件 | default / confirm-loading / retryable / fatal / success / error / info |

## Design Tokens 摘要

- 主色：`--color-primary` = `#1E293B` / `#EDEDED`（暗色为反色中性按钮，文字 `#0A0A0B`）；页面底色 `--color-background` = `#F8FAFC` / `#0A0A0B`
- 暗色表面：卡片 `#141416`、弱化表面 `#1C1C1F`、边框 `#2A2A2E`、正文 `#EDEDED`、次要文字 `#A1A1AA`；焦点环 `#22C55E`
- 强调/运行色：`--color-accent` = `#16A34A` / `#22C55E`；危险色 `--color-destructive` = `#DC2626` / `#EF4444`
- 字体：`--font-family-base` = `"IBM Plex Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif`；标题与代码用 `--font-family-heading` / `--font-family-mono` = JetBrains Mono
- 基础间距：`--spacing-4` = `16px`；圆角 `--radius-md` = `8px`；阴影 `--shadow-md` = `0 4px 6px rgba(15, 23, 42, 0.12)` / `0 4px 10px rgba(0, 0, 0, 0.55)`
- 对比度（暗色）：正文/背景 16.90:1、次要文字/背景 7.72:1、on-primary/primary 16.90:1、accent/背景 8.69:1，均 ≥ 4.5:1
- 布局：侧边栏 `248px`，顶栏 `64px`，内容区最大 `1280px`
- 登录页：不新增 token，复用 background / card / border / input / primary / destructive / info / ring；Light 与 Dark 均可用
- 完整 token 表见 `design.md`「Design Tokens」与 `design-system.md`

## 核心设计原则

入口清晰 / 输入明确 / 流程固定 / 输出统一 / 风险可控 / 人工可复核。落地口径：入口带用途与状态；输入声明必填与边界并就近校验；固定「项目 → 会话 → 输入 → 调用 → 记录」路径；调用结果与制品各用统一结构；确认、掩码、超限拒绝与失败留痕；输入事件可展开全文、调用记录可展开核对、状态变更进入时间线。完整映射见 `design.md`「核心设计原则」。

## 关键交互约定

- 登录：`/login` 是唯一入口；未认证页面跳登录页并保留原目标（`next` 仅接受站内路径），接口 401；登录成功回跳原页面。口令始终掩码、回车提交、不提供记住我 / 显示口令 / 注册 / 找回。错误统一「口令错误，请重试。」；同一来源连续失败 5 次锁定 5 分钟并显示 `mm:ss` 倒计时，成功登录清零。
- 会话过期：空闲 8 小时后下一次请求 401 → 静默跳登录页并提示「会话已过期，请重新登录」；同一页面生命周期内未提交草稿（文本、调用提示、各配置表单）在内存中保留，重新登录后回原页面恢复并提示；刷新或关闭标签页即丢失；已落库数据不受影响。
- 登出：顶栏「管理员 ▾」→「退出登录」，立即登出、不二次确认，丢弃未提交草稿，回登录页并提示「已退出登录。」。
- 入口命名：首个入口为「用例库」（key `case-library`，路由 `/entrances/case-library`），生成能力在入口内部（用例列表 / 详情 / 生成按钮），不再以「生成测试用例」作为独立入口名；其余五个入口不变（依据 answers.md：「原型还需要补充一下 生成测试用例 其实可以直接叫用例库（生成功能在里边）」）。
- 入口：6 个入口常驻首页，状态由配置 `planned` / `live` 驱动；planned 占位页不创建会话、不调用模型，本期 6 个入口均为 planned；基座工作在侧边栏「基座管理」（UXAMB-003 A）。
- 会话创建：项目与启用模型为硬前置；缺失时禁用「创建」并给配置引导；创建时选定模型、创建后不可更换，换模型需新建会话（UXAMB-001 / 004 A）；创建后状态为「进行中」并置顶列表。
- 会话详情：左时间线、右三个 Tab（文本粘贴 / 上传 / 发起调用）；调用面板为基座验证面板，调用结果与调用失败均落到时间线，失败展示重试次数且不含密钥原文。
- 状态流转：进行中 → 已完成（用户二次确认）或失败（系统未捕获异常）；用户不能手动标记失败，结束后输入与调用面板只读，不提供重新打开（UXAMB-005 A）。
- 删除：会话删除必须二次确认并列出级联范围（事件、`sessions/<sessionId>/` 制品、调用记录），无撤销、无自动过期清理（UXAMB-005 A）。
- 校验：文本正文上限 200,000 字符，实时计数、>90% 警告、超限拒绝不截断（UXAMB-007 A）；调用提示同用 200,000 字符上限，实时计数、>90% 警告、超限禁用「发起调用」且不截断（AC-UX-19）。文件选择后立即前端三查，白名单 `.txt .md .markdown .log .json .yaml .yml .csv .sql`、单文件 ≤10MB、单次 ≤10 个，不合规标红可移除、同名自动改名并提示（UXAMB-008 A）。
- 调用记录：项目/会话级联筛选 + 时间范围，默认近 7 天；无匹配显示空态与清除筛选，不报错（UXAMB-009 A）。
- 参数覆盖：调用面板「高级参数」仅本次生效，不改变模型默认参数（UXAMB-010 A）。
- 人工可复核：输入事件可展开全文；成功调用展示统一结果块；调用记录成功/失败行都可展开核对；标记完成写入「状态变更 · 已完成」时间线事件。
- 密钥：界面只展示掩码 `sk-****abcd`；编辑时留空表示不修改；连接测试用表单当前值、不落库、修改后结果失效；任何错误与提示摘要不含密钥原文（UXAMB-006 A）。
- 反馈：每个列表/时间线具备 loading / empty / error 三态；异步操作按钮内联 loading；破坏性操作用 ConfirmDialog；登录页错误 / 锁定 / 过期 / 登出统一用 banner，锁定倒计时每秒刷新。
- 可访问性：可见焦点环、Esc 关闭对话框并归还焦点、图标按钮带 aria-label、尊重 `prefers-reduced-motion`；≤768px 侧边栏转为抽屉。

## 状态

pending（2026-11-17 收窄：知识库已整体迁出到 `specs/knowledge-base_20261117205011`，本 spec 只保留 workbench-core 的 US-001 ~ US-011。已从页面、路由、组件、流程图与 demo 中移除知识库列表 / 导入 / 浏览 / 详情 / 注入 / 删除；会话「发起调用」面板保留提示输入的 200,000 字符实时计数（AC-UX-19）。知识库的线框要点、组件行为与 UXAMB 口径已原文落到 `specs/knowledge-base_20261117205011/_handoff/from-interaction-design.md`。用 Playwright（系统 Chrome headless，1440×900，Light / Dark 各一遍）复验剩余交互，结果见 `design.md`「收窄后交互验证记录」。UXAMB-001 ~ UXAMB-010 仍为已确认。等待用户确认本阶段，确认后由 kb-sync 提升，届时视为 confirmed）
