# Interaction Design — Requirements

## 交付范围

本 spec 只交付 `repo-integration` 的**增量交互**：在 workbench-core 项目上下文页内增加「仓库绑定」区块，并新增「仓库浏览」页面。core 页面线框、AppShell、Design Tokens 与视觉基调不重做。

### 必须交付

| 交付物 | 验收标准 |
|--------|---------|
| 线框图 | US-017 ~ US-023 每个 US 至少一张页面 / 面板线框图，含 Layout、Key Elements 表与全部 UI 状态 |
| Design Tokens | 覆盖颜色 / 字体 / 间距 / 圆角 / 阴影五类；颜色给出 Light 与 Dark 两套值；旧 token 不改不删，仅追加 3 条新 token |
| 用户流程图 | US-017 ~ US-023 每个 US 一张 Mermaid 用户操作流程图，含开始 / 结束节点与带标签的决策分支 |
| 组件清单 | 新增组件写明用途与状态列表，状态命名沿用 core 的统一集合（default / hover / focus / loading / success / error / empty / disabled / read-only） |
| 交互约定 | 校验文案、四类测试结果、同步 / 限流 / 截断 / 超限 / 非法路径 / 解绑的提示与置灰规则、错误分级、键盘与响应式 |
| demo.html | 单文件、离线可用（无 CDN），覆盖 7 个 US 的增量界面与 default / loading / success / error / empty 五种状态；US > 5 使用侧边栏导航 |
| 继承说明 | 明确哪些线框、token 与组件来自 workbench-core，本 spec 只做增量 |

### Out of Scope

- workbench-core 页面（首页、会话、提供商、调用记录、登录）的重画与改版
- 新配色体系、新字体、新圆角 / 阴影体系；本 spec 只追加 3 条 token
- 技术实现细节（框架、状态管理、HTTP 客户端、加密实现）：属 technical-design
- 供应商接口契约、分页 / 限流响应头的具体读取实现：属 technical-design
- 整库克隆、代码索引、Webhook、定时同步、仓库写操作、OAuth、多用户（需求层已排除）
- 文件内容的持久化与跨域只读接口的接口字段设计

## 覆盖矩阵

| US | 线框图（design.md） | 用户流程图（docs/flowchart.md） | demo.html |
|----|--------------------|--------------------------------|-----------|
| US-017 绑定仓库并保存令牌 | 项目上下文页；仓库绑定表单 | US-017 绑定与保存 | 项目上下文页 →「+ 添加绑定」 |
| US-018 测试连通性 | 仓库绑定表单；连通性测试结果条 | US-018 测试连通性 | 表单「测试连接」与结果条（四类 + 已失效） |
| US-019 手动同步 | 项目上下文页；同步控件与同步记录 | US-019 手动同步 | 绑定行「同步」、上次同步、同步记录 |
| US-020 选择仓库与分支 | 仓库与分支选择器 | US-020 选择仓库与分支 | 仓库浏览页选择器（未同步空态、失效基线） |
| US-021 浏览提交与目录树 | 提交列表与目录树 | US-021 浏览提交与目录树 | 仓库浏览页目录树 / 提交 / 分页 / 截断 |
| US-022 读取单个文件 | 文件查看抽屉 | US-022 读取单个文件 | 目录树点文件 → 抽屉（成功 / 超限 / 二进制 / 非法路径） |
| US-023 令牌失效与解绑 | 令牌失效横幅与更新令牌；解绑确认；已解绑只读态 | US-023 令牌失效与解绑 | 页面横幅、更新令牌、解绑对话框、置灰快照 |

## 验收标准（EARS 格式）

### AC-UX-20
WHEN 交互设计完成 THEN 系统 SHALL 为 US-017 ~ US-023 各提供至少一张线框图，包含布局示意、关键元素表与 default / loading / success / error / empty 状态说明，且线框图 SHALL 标明该界面是对 workbench-core 的增量。

### AC-UX-21
WHEN Design Tokens 完成 THEN 系统 SHALL 覆盖颜色、字体、间距、圆角、阴影五类 token；每个颜色 token SHALL 同时给出 Light 与 Dark 值；旧 token SHALL NOT 被修改或删除，新增 token SHALL 只有 `--color-overlay`、`--spacing-5`、`--repo-drawer-width` 三条。

### AC-UX-22
WHEN 交互设计完成 THEN 系统 SHALL 为 US-017 ~ US-023 各提供一张 Mermaid 用户流程图，包含开始与结束节点，决策分支 SHALL 带标签。

### AC-UX-23
WHEN 组件清单生成 THEN 系统 SHALL 为每个组件写明用途与状态列表，状态名称 SHALL 取自 default / hover / focus / loading / success / error / empty / disabled / read-only 的统一集合，并 SHALL 标注复用自 core 的组件。

### AC-UX-24
WHEN 页面渲染 THEN 系统 SHALL 复用 workbench-core 的侧边栏（248px）、顶栏（64px）、内容区（1280px）与 Light / Dark 两套 token，SHALL NOT 引入新的配色体系、字体或组件视觉；仓库绑定 SHALL 作为项目详情表单下方的纵向区块（≤1180px 依次堆叠），SHALL NOT 在 core 两栏之外再切第三栏。

### AC-UX-25
WHEN 绑定列表展示 THEN 系统 SHALL 显示每个绑定的提供商、仓库全名（mono）、状态徽标（未验证 / 已连接 / 令牌失效 / 已解绑）、令牌掩码、默认分支与上次测试 / 上次同步；令牌 SHALL 只以掩码出现，界面 SHALL NOT 出现完整令牌或供应商原始响应。

### AC-UX-26
WHEN 用户点击「测试连接」 THEN 系统 SHALL 复用 core 的 `ConnectionTestBadge` 在表单内就地展示「成功 / 鉴权失败 / 网络失败 / 权限不足」之一及测试时间与可读原因，四类结果 SHALL 使用不同徽标语义与不同下一步文案；测试 SHALL 不弹 Toast、不落库；表单任一字段变更后徽标 SHALL 转灰并标「已失效（时间 · 结果）」。

### AC-UX-27
WHEN 用户点击「同步」 THEN 同一绑定的按钮 SHALL 变为「同步中…」并禁用，SHALL NOT 产生第二次请求；成功后 SHALL 展示上次同步时间、耗时、结果与基线；失败时 SHALL 保留上次成功时间与基线并展示失败分类；供应商限流 SHALL 在同步记录中显示可重试时间，SHALL NOT 自动重试。

### AC-UX-28
WHEN 浏览页展示仓库 / 分支 / 提交 / 目录树 THEN 系统 SHALL 标注「实时读取」，并 SHALL 把同步结果单独展示为「上次同步基线 `<ref> @ <sha> · <时间> · 仅作对照」；令牌失效时 SHALL 明确标注当前展示的是上次同步基线及其时间。

### AC-UX-29
WHEN 元数据未同步、列表为空或无提交 THEN 系统 SHALL 展示带引导的空态（如「还没有可浏览的元数据」+「去同步」、「没有提交」、「还没有绑定仓库」），SHALL NOT 返回空白页或错误页。

### AC-UX-30
WHEN 用户浏览目录树 THEN 系统 SHALL 逐级展开目录并在每级展示名称、类型与文件大小；供应商分页未给全时 SHALL 显示「还有更多（n 条未加载）」与加载入口；供应商标记截断时 SHALL 显示「目录树不完整，请逐级浏览」，SHALL NOT 把不完整结果当作完整结果。

### AC-UX-31
WHEN 用户打开单个文件 THEN 系统 SHALL 在右侧抽屉展示路径、ref、大小、读取时间与内容；文件超过 1 MiB 时 SHALL 展示实际大小与上限 1,048,576 字节并拒绝，SHALL NOT 截断；二进制 / 非 UTF-8 时 SHALL 拒绝预览；路径含 `..` 或绝对路径时 SHALL 在请求前拒绝并说明未产生读取记录。

### AC-UX-32
WHEN 任一绑定被识别为「令牌失效」 THEN 项目上下文页 SHALL 只显示一条聚合横幅并提供「重新填写令牌」「查看基线快照」，相关入口 SHALL NOT 重复弹错；用户更新令牌且测试成功后 SHALL 展示恢复「已连接」，bindingId、元数据与历史记录不变。

### AC-UX-33
WHEN 用户点击「解绑」 THEN 系统 SHALL 弹出二次确认并逐条列出后果（删除令牌、不再请求、快照只读、目录树与读文件置灰、历史不变、生成新 bindingId）；确认后绑定行 SHALL 置灰保留，令牌显示「—」，目录树行与文件入口 SHALL `aria-disabled` 且不可发起请求。

### AC-UX-34
WHEN 用户仅使用键盘或屏幕阅读器 THEN 系统 SHALL 提供可见焦点环、Tab 顺序、Enter / Space 激活、Esc 关闭抽屉与对话框并归还焦点、图标按钮 `aria-label`；状态 SHALL 同时用文本表达，不只靠颜色；视口 1440px 下 SHALL 无横向滚动，≤768px 时侧边栏转抽屉、文件抽屉全宽。

### AC-UX-35
WHEN demo.html 交付 THEN 系统 SHALL 为单文件、无外部依赖，覆盖 7 个 US 的增量界面与五种 UI 状态，并 SHALL 支持 Light / Dark 切换；Dark 与 Light SHALL 各通过一次 1440×900 的 Playwright 检查，控制台错误数为 0。
