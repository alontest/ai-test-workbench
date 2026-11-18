# Interaction Design — Requirements

## 交付范围

### 必须交付
| 交付物 | 验收标准 |
|--------|---------|
| 线框图 | 每个 US（US-001 ~ US-011）至少对应一个页面线框图，含关键元素表与全部 UI 状态 |
| Design Tokens | 覆盖颜色 / 字体 / 间距 / 圆角 / 阴影五类；颜色同时给出 Light 与 Dark 两套值 |
| 用户流程图 | 每个 US 对应一张 Mermaid 用户操作流程图 |
| 组件清单 | 每个组件列出职责、关键 props/输入与状态列表 |
| 交互约定 | 表单校验文案、空态/加载/错误态、破坏性操作确认、键盘与可访问性约定 |
| demo.html | 单文件、离线可用，覆盖全部 11 个 US 页面与 default / loading / success / error / empty 五种状态 |
| 登录闸门 | 未认证访问任一路由都落到登录页并保留原目标；登录、错误、锁定、会话过期、登出均有可交互演示 |

### Out of Scope
- 技术实现细节（框架、状态管理、构建方式）：属于 technical-design 职责
- 后端 API 设计与进程内接口签名：属于 technical-design 职责
- 其余 4 个业务域（test-case / diagnosis / regression-list / test-report）的页面与交互
- 流式输出的交互（本期同步返回 + 等待态）
- 多用户账号、注册、口令找回、角色权限与多租户界面（本期为单用户口令登录，US-011）
- 登录事件审计页面（是否需要审计存储由 tech-arch 决定；界面不虚构审计记录）

## 覆盖矩阵

| US | 页面线框图 | 用户流程图 | demo 页面 |
|----|-----------|-----------|-----------|
| US-001 | 工作台首页 | US-001 首页进入六类入口 | `#home` |
| US-002 | 入口占位页 | US-002 进入未交付入口 | `#entrance` |
| US-003 | AI 提供商配置页 | US-003 配置提供商并连接测试 | `#providers` |
| US-004 | 模型绑定页 | US-004 绑定模型 | `#models` |
| US-005 | 会话详情页（发起调用 + 调用结果） | US-005 统一调用与记录 | `#session` |
| US-006 | 会话详情页（文本粘贴区） | US-006 粘贴文本输入 | `#session` |
| US-007 | 会话详情页（文件上传区 + 制品卡片） | US-007 上传文件输入 | `#session` |
| US-008 | 项目上下文页 | US-008 维护项目上下文 | `#projects` |
| US-009 | 会话列表 + 新建会话对话框 + 会话详情 | US-009 创建会话与回看 | `#sessions` / `#session` |
| US-010 | AI 调用记录页 | US-010 查询调用记录 | `#calls` |
| US-011 | 登录页 + 顶栏用户区 / 登出 | US-011 登录、会话过期与登出 | demo 登录闸门（未登录先显示登录页） |

入口命名（2026-11-17）：六个入口之一原「生成测试用例」更名为「用例库」，key 为 `case-library`，路由 `/entrances/case-library`；用例生成能力放在该入口内部（用例列表 / 详情 / 生成按钮），不再作为独立入口名。其余五个入口名称不变。依据：answers.md：「原型还需要补充一下 生成测试用例 其实可以直接叫用例库（生成功能在里边）」。

## 验收标准（EARS 格式）

### AC-UX-1
WHEN 交互设计完成 THEN 系统 SHALL 为 US-001 ~ US-011 提供页面线框图，包含布局示意图、关键元素表与 default / loading / success / error / empty 五类状态说明。

### AC-UX-2
WHEN Design Tokens 定义完成 THEN 系统 SHALL 提供颜色、字体、间距、圆角、阴影五类 token，且每个颜色 token SHALL 同时给出 Light 与 Dark 值。

### AC-UX-3
WHEN 交互设计完成 THEN 系统 SHALL 为 US-001 ~ US-011 各提供一张 Mermaid 用户流程图，流程图包含开始与结束节点，决策分支带标签。

### AC-UX-4
WHEN 组件清单生成 THEN 系统 SHALL 为每个组件写明用途与状态列表，状态列表 SHALL 使用统一命名（default / hover / focus / loading / success / error / empty / disabled / read-only）。

### AC-UX-5
WHEN 用户提交任一表单 THEN 系统 SHALL 在对应字段旁给出阻止性错误文案，文案 SHALL 说明原因与修正方式，不只在页面顶部汇总错误。

### AC-UX-6
WHEN demo.html 交付 THEN 系统 SHALL 以单文件、无外部依赖的形式提供全部 11 个 US 页面，并可在页面内切换五种 UI 状态。

### AC-UX-7
WHEN 用户仅使用键盘 THEN 系统 SHALL 支持 Tab 焦点顺序、可见焦点环、Enter/Space 激活按钮、Esc 关闭对话框，且焦点不会困在隐藏区域。

### AC-UX-8
WHEN 视口宽度为 375 / 768 / 1024 / 1440 px THEN 系统 SHALL 不出现横向滚动，侧边栏在 ≤768px 收起为抽屉。

### AC-UX-9
WHEN 异步操作进行中或失败或无数据 THEN 系统 SHALL 分别展示加载骨架、可重试的错误态与带 CTA 的空态，不展示空白页面。

### AC-UX-10
WHEN 用户执行删除会话等破坏性操作 THEN 系统 SHALL 先弹出确认对话框，列明将被级联删除的内容，确认后才执行且不提供撤销。

### AC-UX-11
WHEN 会话处于「已完成」或「失败」状态 THEN 系统 SHALL 将输入区与调用面板置为只读并展示「会话已结束」提示，不提供重新打开入口。

### AC-UX-12
WHEN 页面展示密钥 THEN 系统 SHALL 只展示掩码（如 `sk-****abcd`），编辑时密钥字段留空表示不修改，任何界面均不出现完整密钥。

### AC-UX-13
WHEN 未登录或登录会话失效的用户访问任一工作台页面 THEN 系统 SHALL 跳转登录页并在登录成功后回到原目标页面；访问受保护接口 SHALL 返回 401，且登录页与受保护页面 SHALL NOT 渲染侧边栏或任何业务数据。

### AC-UX-14
WHEN 用户在登录页提交管理员口令，THEN 系统 SHALL 提供 default / submitting / error / locked 四种可区分状态：错误只显示统一文案「口令错误，请重试。」；同一来源连续失败 5 次后显示锁定提示与 `mm:ss` 剩余时间，并禁用口令输入与登录按钮；成功登录后失败计数清零。

### AC-UX-15
WHEN 登录会话空闲超过 8 小时后下一次请求被判定未登录 THEN 系统 SHALL 静默跳转登录页并提示「会话已过期，请重新登录」；同一页面生命周期内已填写但未提交的内容 SHALL 在重新登录后恢复并提示，刷新或关闭标签页后草稿不再保留（仅存内存）。

### AC-UX-16
WHEN 用户从顶栏用户区点击「退出登录」 THEN 系统 SHALL 立即登出并回到登录页，SHALL NOT 要求二次确认；显式登出 SHALL 丢弃未提交草稿。

### AC-UX-17
WHEN 登录页在 Light 或 Dark 主题下展示 THEN 系统 SHALL 复用工作台 Design Tokens，正文与背景对比度 ≥ 4.5:1；口令字段 SHALL 始终掩码，并支持回车提交与键盘焦点顺序。

### AC-UX-18
WHEN 首页、侧边栏与入口占位页展示测试用例入口 THEN 系统 SHALL 使用名称「用例库」与路由 `/entrances/case-library`，SHALL NOT 再以「生成测试用例」作为独立入口名；用例生成能力 SHALL 在用例库内部（列表 / 详情 / 生成按钮）呈现，其余五个入口名称不变。

### AC-UX-19
WHEN 用户在会话「发起调用」面板输入提示 THEN 系统 SHALL 实时显示 `已输入 n / 200,000 字符`，超过 90% 时 SHALL 使用警告色，超过 200,000 字符时 SHALL 报错并禁用「发起调用」，SHALL NOT 静默截断。
