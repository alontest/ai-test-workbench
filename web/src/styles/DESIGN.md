# 视觉与页面布局规范 — AI 测试工作台

> 本文是前端 15 个页面视觉重构与布局统一的**唯一设计蓝图**。
> Token 数值真源为 [design-system.md](file:///Users/alon/Developer/OpenSource/ai-test-workbench/docs/ai-test-workbench/interaction-design/design-system.md) 与 [tokens.css](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/styles/tokens.css)。本文规定：**设计方法论分工、官方吉祥物定稿、双主题与层级纪律、全局骨架与垂直节奏、五套页面布局母版、测试红线，以及 15 个页面的逐页落位清单**。

---

## 一、设计方法论：`archive2` (Aurora) × `frontend-design` 分工融合

我们不做「二选一」，而是按两者的基因长处明确职责边界：

| 维度 | 采用来源 | 具体吸收内容 | 明确剔除 / 不照搬的部分 |
|---|---|---|---|
| **骨架与交互纪律** | `/Users/alon/Developer/OpenSource/archive2`（Aurora Design System v2） | 1. **页面四段垂直节奏**：标题区（低密度呼吸）→ 工具栏（中密度吸顶控制）→ 内容区（高密度数据）→ 底部区（分页/说明）<br>2. **`PageHeader` 恒定可见铁律**：加载/错误/空态下 `PageHeader` 必须保持渲染，骨架屏/Spinner 仅替换内容区，消除切页闪烁<br>3. **1px 边框分层纪律**：依靠边框与表面色差建立层级；仅在同容器内部用分隔线，跨模块只用间距<br>4. **按页面类型分级限宽**：工作台/表格撑满 `1280px`，看板网格 `1120px`，详情阅读 `880px`，向导表单 `720px`<br>5. **微观反馈链**：按钮按压 `scale(0.98)` `var(--duration-fast)` (`120ms`)、可点击卡片 `-1px` 上浮 + 边框提亮、侧栏当前项左侧 `3px` 竖条指示 | 不照搬 `archive2` 的 Tailwind 类名体系（本项目保持 CSS Modules + CSS 变量）；不照搬其「禁止 `text-xl` 以上大字号、禁止内联 SVG」的纯中性后台清规 |
| **领域性格与反模板审美** | `frontend-design` Skill | 1. **扎根真实领域**：视觉围绕「测试工程师的夜巡探案台」（读需求、抓 Bug、翻日志、审 SQL、守回归）展开，不做通用 SaaS 模板<br>2. **胆量集中一处**：把视觉记忆点集中在「鸮鸮」六态角色陪伴、等宽工程骨骼（标题/编号/SHA/耗时）与测试印章式状态标识（`PASS` / `FAIL` / `PLANNED`），其余容器保持安静克制<br>3. **结构即信息**：左侧语义色条（失败红边、超限琥珀边、命中翡翠边）直接编码业务状态，拒绝无信息量的卡片套娃（SaaS-card kit）与全大写装饰 eyebrow<br>4. **文案即导航**：空态与报错不卖萌、不道歉，直接陈述系统事实并给出下一步动作按钮 | 不使用散乱的各区块独立入场动画；不改动已验证通过的 WCAG 对比度 Token |

---

## 二、这个产品是什么 & 视觉性格

单用户自托管的测试工作台。使用者是测试工程师，每天在它面前连续工作数小时：读需求、写用例、复现缺陷、翻日志、核对 SQL、出回归清单、交测试报告。

### 视觉性格：三句话

1. **精密，不花哨。** 编号（`R-001`）、提交哈希（`f059a784`）、字符预算（`182,400 / 200,000`）、时间戳与耗时是第一公民，全部以等宽字体对齐，一眼可扫读。
2. **有秩序与位置感。** 用户在「项目 → 会话 → 知识库 → 仓库 → 调用审计」多域间高频跳转，任何时刻（包括 Loading 期间）都清楚「我在哪、当前绑定了什么上下文、下一步点哪里」。
3. **有伙伴感（人味）。** 测试排查是漫长的脑力活，夜巡猫头鹰探长「鸮鸮」常驻在侧栏品牌位、登录舞台、首页导语、调用面板与空态里，随系统真实状态拉下护目镜扫描、炸毛告警或举起 `PASS ✓` 盾牌。

---

## 三、官方吉祥物定稿：夜巡猫头鹰探长「鸮鸮 (Inspector Hoot)」

### 1. 角色设定与造型记忆点

- **角色标识**：`variant="owl"`（[Mascot.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/components/mascot/Mascot.tsx) 唯一官方角色，已移除废弃原型代码）。
- **领域隐喻**：测试工程师就是代码夜巡人——黑暗里眼神最毒、能看穿全链路、专门抓藏在暗处的害虫（Bug）。
- **核心造型**：深岩灰立体羽翼 + 胸前翡翠探长领结徽章 + 随情绪竖立/炸开的耳羽簇 + **平时架在额头上的双筒战术测试护目镜**。

### 2. 响应式细节分层（Adaptive LOD）

- **`size <= 36`（24px / 28px / 32px 侧栏品牌位、内联徽章位）**：自动切换为**高对比头像剪影态**（只保留耳羽轮廓、战术护目镜与双高光大眼睛，砍掉细碎肢体），小尺寸下依然锐利不糊。
- **`size > 36`（40px ~ 200px 登录舞台、首页导语、调用面板、空状态）**：展开为**完整角色态**，具备立体羽翼、表情眼神、翅膀动作与状态专属道具。

### 3. 六态行为与业务事实映射

| 状态 | 视觉姿态与道具 | 触发的系统事实 | 页面出现位置 |
|---|---|---|---|
| `idle` | 护目镜架在额头，双高光大眼，6s 平稳呼吸悬浮 | 系统空闲待命 | 侧栏品牌位、首页导语、默认空态 |
| `watching` | 耳羽高竖，右翅托腮思考，视线锁定前方，头顶冒出感应波 | 表单/提示词正在输入、待发起调用或连接测试 | 登录页输入口令时、会话调用面板已填提示词待发送时 |
| `analyzing` | **一把将战术护目镜拉下戴在眼上**，镜片开启翡翠绿 HUD 十字准星双向旋转，身旁浮现代码扫描流 | 模型调用进行中、仓库元数据同步中、知识库导入解析中 | 会话「发起调用」执行态、仓库同步态 |
| `warning` | 浑身炸毛张翅，瞳孔收缩变琥珀色，头顶亮起三角形故障信标 | 字符超 90% 预算、令牌失效（`token_invalid`）、限流或校验报错 | 登录锁定/报错、会话字数告警、仓库令牌失效横幅 |
| `success` | 笑成弯弯月牙眼（`^ ^`），右翅高举翠绿 `PASS ✓` 印章盾牌与星芒 | 调用完成、连接测试通过、知识库导入成功、会话标记完成 | 导入完成报告头、已完成会话头 |
| `sleeping` | 收翅缩成圆毛球，温柔闭眼（`︶ ︶`），头顶飘起 `Z z z` | 会话已过期（`reason=expired`）、仓库绑定已解绑只读（`revoked`）、未启用占位入口 | 登录过期提示、已解绑仓库快照页、`planned` 入口占位页 |

---

## 四、全局外壳与空间纪律（AppShell & Vertical Rhythm）

### 1. 全局外壳（AppShell）职责解耦

解决「顶栏 `pageTitle` 与页面内 `<h1>` 双重标题重复打架」的问题：

```
┌──────────────────┬──────────────────────────────────────────────────────────┐
│  Sidebar (248px) │  Topbar (var(--topbar-height) = 64px, sticky)            │
│  fixed / 独立滚  │  [面包屑: 基座管理 / 项目]                        [退出] │
│                  ├──────────────────────────────────────────────────────────┤
│  [鸮鸮 28px品牌] │  Main Content (max-width: 1280px, padding: 24px 32px)    │
│                  │                                                          │
│  ▸ 工作台        │  ① PageHeader (H1 + 一句话用途描述 + 右侧唯一主操作)      │
│    首页          │  ──────────────────────────────────────────────────────  │
│    分析会话      │  ② Toolbar / Context Strip (搜索 / 筛选 / 状态基线条)    │
│                  │  ──────────────────────────────────────────────────────  │
│  ▸ 六大入口      │  ③ Primary Content (表格 / 双栏工作台 / 卡片网格)        │
│    用例库 ...    │                                                          │
│                  │  ④ Footer (游标加载更多 / 计数 / 只读边界说明)            │
│  ▸ 基座管理      │                                                          │
│    项目上下文... │                                                          │
└──────────────────┴──────────────────────────────────────────────────────────┘
```

- **侧边栏（Sidebar `var(--sidebar-width)` = `248px`）**：
  - 顶部品牌区：鸮鸮 `28px` 头像剪影徽标 + `AI Test Workbench` + 副标 `LOCAL INSPECTOR`。
  - 导航分组：`工作台`、`六大入口（均在规划中）`、`基座管理`。
  - **Active 态**：背景 `--color-muted` + **左侧 `3px` 翡翠绿竖条（`--color-accent`）** + 字重 `500` + 配套线性图标（18×18）。
- **顶栏（Topbar `var(--topbar-height)` = `64px`）**：
  - **不再重复渲染页面 H1 标题**！左侧显示**位置面包屑**（如 `基座管理 / AI 提供商 / 模型绑定`）；
  - 右侧只保留「退出」按钮（**不设无数据源的全局实时状态弹窗或假按钮**；鸮鸮留在侧栏品牌位与具体业务页）。
  - 吸顶工具栏统一引用 `top: var(--topbar-height)`，**严禁在 CSS 中写死像素值**。

### 2. 页面垂直四段节奏（Visual Rhythm）

除 `/login` 外，所有页面严格遵循四段垂直节奏：

| 段位 | 组件 / 结构 | 信息密度 | 留白与间距规则 | 核心铁律 |
|---|---|---|---|---|
| **① 标题区 (`PageHeader`)** | `backLink`（可选）+ `H1 标题` + `description` + `badge`（可选）+ `actions`（右上主按钮） | 低密度 | 底部固定留白 `padding-bottom: 16px`；标题 `var(--font-size-xl)` (`24px`) `--font-family-heading`，描述 `var(--font-size-base)` `--color-muted-foreground` | **Loading / Error / Empty 期间必须始终可见**！严禁在 `isPending` 时整页早期返回 `<Spinner />` 导致页面标题消失跳动 |
| **② 工具栏 / 状态条 (`Toolbar`)** | 搜索框（左）+ 筛选器（中）+ 统计计数/次要动作（右）；或前置检查条/告警横幅 | 中密度 | 与标题区间距 `0`（紧接标题区），与内容区间距 `16px`；长列表页滚动时 `sticky; top: var(--topbar-height); z-index: 10` | 筛选被激活时必须提供显式的「清除筛选」按钮；主创建按钮放 `PageHeader.actions`，不塞进筛选栏 |
| **③ 内容区 (`Content`)** | 数据表格、Bento 卡片网格、主从双栏或聚焦表单 | 高密度 | 内部间距 `12px` ~ `16px` | 加载态在此区域内渲染骨架屏或区块级 `<Spinner />`，不破坏外层框架 |
| **④ 底部区 (`Footer`)** | 游标分页「加载更多」、审计留痕说明、只读安全边界提示 | 低密度 | 顶部间距 `16px` ~ `24px`，文字 `12px` `--color-muted-foreground` | 无分页且无边界说明时完全不渲染，不留空盒子 |

### 3. 内容区宽度分级（Width Tiers）

不同页面类型严禁一刀切使用同一宽度：

| 宽度等级 | 最大宽度 | 适用页面类型 | 原因 |
|---|---|---|---|
| **Tier XL（全宽工作台）** | `var(--content-max-width)` (`1280px`) | `/sessions/:id`、`/projects`、`/projects/:projectId/repos/:bindingId`、`/calls`、`/sessions`、`/providers`、`/providers/:id/models`、`/knowledge-bases`、`/knowledge-bases/:kbId` | 双栏工作台与多列数据表需要充足横向空间展示哈希、路径与时间戳 |
| **Tier LG（看板网格）** | `1120px` | `/`（首页）、`/repos`（仓库浏览索引） | 双列/三列卡片在 `1120px` 内扫读最舒适，卡片不会因过宽而空旷 |
| **Tier MD（沉浸阅读）** | `880px` | `/knowledge-bases/:kbId/entries/:code`、`/entrances/:key` | 保证正文与代码块单行不超过 75~80 字符的最佳阅读行宽 |
| **Tier SM（聚焦向导）** | `720px` | `/knowledge-bases/import` | 单列导入向导与文件校验列表，过宽会导致左右视线跨度过大 |
| **Tier Auth（登录舞台）** | `920px`（双栏） | `/login` | 左侧 460px「鸮鸮」夜巡探案舞台 + 右侧 420px 高对比口令卡片 |

### 4. 双主题（Light / Dark）、表面与层级纪律

- **双主题 Token 铁律**：[tokens.css](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/styles/tokens.css) 完整支持 Dark 与 Light 双主题（跟随系统 `prefers-color-scheme` 与 `[data-theme]`）。**所有页面容器、卡片、表头、文字、边框、遮罩、滚动条底色必须全部引用 CSS Token**，严禁在页面 CSS 或内联样式中写死暗色 hex（如 `#0a0a0b`、`#141416`、`rgba(255,255,255,...)`）。若需半透明强调底色，使用 `color-mix(in srgb, var(--color-accent) 12%, transparent)` 等基于 Token 的派生写法。
- **三层表面结构**（亮/暗主题均由同一套变量自动映射）：
  - 底层画布 `--color-background`
  - 一级容器 `--color-card` + `1px solid var(--color-border)`
  - 弱化/表头/代码块 `--color-muted`
- **禁止卡片套娃**：任何页面最多允许「页面画布 → 一级卡片容器 → 内部弱化块（`--color-muted`）」两层嵌套，严禁三层以上带边框卡片套卡片。
- **语义左边框（Status Spine）**：用 `3px` 左边框颜色编码行或卡片的业务状态：
  - 翡翠绿 `--color-accent`：进行中会话、已启用入口、当前选中项目、成功调用
  - 琥珀色 `--color-warning`：字数超 90% 警告、令牌失效（`token_invalid`）、历史被替代版本（`superseded`）
  - 危险红 `--color-destructive`：调用失败记录、校验不合规文件行、锁定倒计时
- **分隔线规则**：只在**同一容器内部**的不同区域之间画 `1px solid var(--color-border)`；两个独立容器之间只用 `gap: 16px` 或 `24px` 留白。
- **全站 `z-index` 层级契约**（禁止野路子随便写 `999`）：

| 层级 | `z-index` | 元素 |
|---|---|---|
| 吸顶工具栏 / 粘性面板 | `10` | 列表筛选吸顶条、知识库 Tab 吸顶栏 |
| 顶栏 | `20` | `AppShell` `.topbar` |
| 移动端侧栏遮罩与抽屉 | `25` / `26` | 窄屏展开态 `AppShell` `.sidebar` |
| 代码查看抽屉 | `30` | `FileViewerDrawer` `.drawerOverlay`（宽度统一 `var(--repo-drawer-width)`） |
| 模态弹窗 | `40` / `41` | `Dialog` `.overlay` (`40`) 与 `.content` (`41`) |

---

## 五、五套标准页面布局母版（5 Layout Archetypes）

全站 15 个页面统一收敛为以下 5 套布局母版，禁止出现第 6 种野路子布局：

### 母版 A：双栏品牌认证舞台（Auth Split Stage）
> **适用页面**：`1. /login`（响应式 `< 860px` 自动折叠为单卡，顶部露出 72px「鸮鸮」）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────┐  ┌────────────────────────────────┐  │
│  │  Left: 夜巡探长舞台 (Token面)  │  │  Right: 登录认证卡片 (420px)    │  │
│  │                               │  │                                │  │
│  │       [鸮鸮 140px 互动]        │  │  [AW] AI Test Workbench        │  │
│  │   (输入口令时切 watching 态，   │  │  登录工作台                     │  │
│  │    报错/锁定时切 warning 态)   │  │  输入部署时设置的管理员口令...  │  │
│  │                               │  │                                │  │
│  │  ┌─ 探案台能力胶囊 ─────────┐ │  │  [AuthBanner: 过期/登出/锁定]   │  │
│  │  │ • 200k 字符预算与知识注入 │ │  │  管理员口令 [••••••••••••]      │  │
│  │  │ • 云效 / GitHub 只读浏览  │ │  │  [           登 录           ] │  │
│  │  │ • 全链路调用留痕与审计    │ │  │  单用户自托管 · 口令由部署维护  │  │
│  │  └──────────────────────────┘ │  └────────────────────────────────┘  │
│  └───────────────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 母版 B：指挥台看板（Command Deck）
> **适用页面**：`2. /`（工作台首页）、`14. /repos`（仓库浏览索引页）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ① Hero / PageHeader                                                    │
│  开始一次分析                                      [鸮鸮 56px + 状态条] │
│  选项目 → 给输入 → 发起调用，三步拿到 AI 结果。      ● 前置检查通过...   │
├─────────────────────────────────────────────────────────────────────────┤
│  ② 六大入口矩阵 (2×3 Grid, 卡片带专属线性图标 + 域标签 + 状态胶囊)      │
│  ┌─────────────────────────────────┐ ┌────────────────────────────────┐ │
│  │ [图标] 用例库            规划中 │ │ [图标] 分析 bug          规划中 │ │
│  │ 管理与生成测试用例...           │ │ 结合堆栈、复现步骤定位根因...   │ │
│  │ test-case · 测试用例域          │ │ diagnosis · 缺陷与诊断域        │ │
│  └─────────────────────────────────┘ └────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│  ③ 最近分析会话 (Section Header + 紧凑表格 + 空态「鸮鸮」引导)          │
│  最近会话                                                   查看全部 →  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ #ID   标题 / 入口       所属项目     模型         状态    更新时间  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 母版 C：过滤表格与审计流（Filter-Table & Audit List）
> **适用页面**：`4. /sessions`、`7. /providers`、`8. /providers/:id/models`、`9. /calls`、`10. /knowledge-bases`、`12. /knowledge-bases/:kbId`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ① PageHeader（恒定可见，Loading 时不卸载！）                            │
│  [← 返回上级(可选)]                                                     │
│  页面主标题 (24px heading)                            [+ 主操作按钮]     │
│  一句话说明页面用途与边界（如：项目级只读资产，导入后可按编号注入）      │
├─────────────────────────────────────────────────────────────────────────┤
│  ② Filter & Status Toolbar (卡片化或吸顶条，左右对齐)                    │
│  [搜索/项目筛选] [状态/类型 Tab 或下拉] [时间范围]   [清除筛选] 共 N 条 │
├─────────────────────────────────────────────────────────────────────────┤
│  ③ Table Card Container (border-radius: 8px, 1px border, 表头 muted)   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 列头 (12px medium muted)                                    操作列 │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ 主标识 (font-medium) │ 等宽编号/哈希 (mono) │ 状态胶囊 │ [操作按钮]│ │
│  │ └─ (可选展开详情行：调用记录输入/输出/注入编号核对抽屉或内联折叠)   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│  ④ Footer: [加载更多]  或  只读/安全边界说明文字                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 母版 D：非对称双栏工作台（Asymmetric Split Workbench）
> **适用页面**：`5. /sessions/:id`（会话详情）、`6. /projects`（项目与仓库绑定）、`15. /projects/:projectId/repos/:bindingId`（仓库实时浏览 + 代码抽屉）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ① Workbench Header / Context Strip                                     │
│  [← 返回] 会话 #42 · 支付回调超时排查    [进行中] [项目: jialeshop]      │
│           绑定模型: deepseek-chat        [标记完成] [删除会话]          │
├───────────────────────────────────────────┬─────────────────────────────┤
│  ② Left Primary Pane                      │  ③ Right Sticky Pane        │
│  • /sessions/:id → 事件时间线流 (60%)      │  • /sessions/:id → (40%)    │
│    (输入文本 / 上传制品 / 知识注入 /       │    [文本粘贴│文件上传│调用] │
│     AI 调用结果与耗时，左侧带状态色条)     │    Radix Tabs.Content 切换  │
│  • /projects → 左侧紧凑项目卡片列表        │    + 200k 字符预算进度条    │
│    (360px 窄栏卡片行，选中带左绿边)        │    + 「鸮鸮」40px 状态联动  │
│  • /repos/:bindingId → 左侧实时目录树      │  • /projects →              │
│    (文件夹/文件图标 + 逐级展开)           │    右侧当前项目仓库绑定工作区│
│                                           │  • /repos/:bindingId →      │
│                                           │    右侧实时提交历史流        │
│                                           │    (文件抽屉走 --repo-drawer-width)│
└───────────────────────────────────────────┴─────────────────────────────┘
```

### 母版 E：聚焦阅读与向导单栏（Focused Reader / Wizard）
> **适用页面**：`3. /entrances/:key`（6 入口占位/工作页，880px）、`11. /knowledge-bases/import`（导入向导，720px）、`13. /knowledge-bases/:kbId/entries/:code`（知识条目详情，880px）

```
        ┌─────────────────────────────────────────────────────────┐
        │  ① PageHeader (居中限宽容器 720px / 880px，内容左对齐)   │
        │  ← 返回上级列表                                         │
        │  标题 / 条目编号 [R-001]                   [类型/状态签] │
        │  副标题或元数据条（所属知识库 · 版本 v2 · 源文件: ...）  │
        ├─────────────────────────────────────────────────────────┤
        │  ② Focused Card Body                                    │
        │  • 导入向导：步骤 1 选项目与名称 → 步骤 2 拖拽文件与     │
        │    前端三查实时清单 → 提交后切换为「鸮鸮 success」报告卡 │
        │  • 条目详情：结构化元数据网格 + 高可读性 Markdown/代码区 │
        │  • 入口占位：「鸮鸮 sleeping」+ 所属域路线图卡           │
        │    + 引导前往「分析会话」或「基座管理」的快捷链接        │
        └─────────────────────────────────────────────────────────┘
```

---

## 六、既有前端单测红线（改造严禁触发）

以下断言来自现有 26 份 Vitest 测试，重构文案与结构时必须硬遵守：

1. **登录页 [LoginPage.test.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/auth/LoginPage.test.tsx)**：页面内严禁出现匹配 `/项目/` 的链接，严禁出现「`项目上下文`」文字。左侧舞台的能力胶囊文案必须避开这些词。
2. **入口占位页 [EntrancePage.test.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/entrances/EntrancePage.test.tsx)**：页面内严禁出现匹配 `/提交|发起调用|创建会话/` 的 `<button>`。快捷跳板必须用 `<Link to="/sessions">` 等导航链接，且文案避开「创建会话」（如用「前往分析会话」）。
3. **首页 [HomePage.test.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/entrances/HomePage.test.tsx)**：匹配 6 个入口名（用例库 / 分析 bug / 排查日志 / 分析 SQL / 生成回归清单 / 生成测试报告）的链接数量必须**严格等于 6**。Hero 区与最近会话区不得新增撞名链接。
4. **通用契约**：保留现有所有 `aria-label`、`role`、`data-testid`、`data-mount` 与按钮语义（如 `ProjectList` 的「仓库绑定 / 已选择」与「编辑」按钮）。

---

## 七、15 个页面逐页改造清单与批次划分

在不破坏现有 **104 个 Vitest 前端测试**的前提下，按以下 4 个批次串行推进：

### 批次 UI-0：公共布局原语、层级表与外壳升级（地基）
1. **`PageHeader` 原语**（新建 `web/src/components/ui/PageHeader.tsx` + 样式）：统一封装 `backLink`、`title` (`<h1>`)、`description`、`badge`、`actions`，消灭各页面手写 `<header style={{ display: "flex" }}>`。
2. **`z-index` 层级收口**：在 `ui.module.css`（Dialog `.overlay: 40` / `.content: 41`）、`AppShell.module.css`（`.topbar: 20`、移动端侧栏 `25/26`）与 `browse.module.css`（`.drawerOverlay: 30`）落实层级表；按钮按压统一 `scale(0.98)` `var(--duration-fast)`。
3. **`AppShell` 升级**（[AppShell.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/app/AppShell.tsx)）：侧栏加入「鸮鸮」`28px` 品牌徽章、导航项线性图标与左侧 `3px` 激活绿条；顶栏保持 `var(--topbar-height)` (`64px`)，左侧位置面包屑 + 右侧退出，不再与页面 H1 重复；全部颜色严格走 Token 兼容 Light/Dark。
4. **通用表格与工具栏样式收口**：统一表头 `--color-muted`、等宽编号列、行 hover 态与卡片容器圆角边框。
5. **补齐外壳单测**：新建 `web/src/app/AppShell.test.tsx`，覆盖路由面包屑、侧栏当前项高亮与退出交互。

### 批次 UI-1：门面与核心高频 4 页（第一眼质感 + 修真 Bug）
| # | 路由 | 页面文件 | 采用母版 | 核心改造要点 |
|---|---|---|---|---|
| 1 | `/login` | [LoginPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/auth/LoginPage.tsx) | **母版 A（双栏舞台）** | 升级为左「鸮鸮 140px 夜巡探案台 + 3 张能力徽章卡（避开『项目上下文』）」、右登录表单的双栏舞台；输入口令时「鸮鸮」切 `watching`，报错/锁定时切 `warning`，过期态切 `sleeping`；全走 Token 兼容双主题 |
| 2 | `/` | [HomePage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/entrances/HomePage.tsx) | **母版 B（指挥台看板）** | 顶部导语区合入「鸮鸮 56px」与前置检查胶囊；6 张入口卡配齐专属 24×24 图标（用例库/Bug/日志/SQL/回归/报告）；最近会话表空态与行质感升级；严格保持 6 入口链接唯一 |
| 3 | `/entrances/:key` | [EntrancePage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/entrances/EntrancePage.tsx) | **母版 E（880px 聚焦卡）** | `PlaceholderPanel` 加入「鸮鸮 `sleeping`」探长简报卡、所属业务域标签与 `<Link>` 快捷跳板（「前往分析会话」「管理 AI 提供商」），不渲染任何触发按钮 |
| 4 | `/sessions/:id` | [SessionDetailPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/sessions/SessionDetailPage.tsx) | **母版 D（双栏工作台）** | **修复真 Bug**：为 3 个 Radix `<Tabs.Trigger>` 补齐 `<Tabs.Content forceMount>`（切 Tab 隐藏非激活面板但保留草稿）并新增 Tab 切换单测；强化会话头信息密度；左时间线事件按类型加 `3px` 语义左边框；右粘性操控台集成「鸮鸮 40px」（随输入/调用中/超限失败变态）与字符预算进度条 |

### 批次 UI-2：分析会话列表与基座管理 5 页（去除内联简陋样式）
| # | 路由 | 页面文件 | 采用母版 | 核心改造要点 |
|---|---|---|---|---|
| 5 | `/sessions` | [SessionsPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/sessions/SessionsPage.tsx) | **母版 C（过滤表格）** | 替换内联 `<header style>` 为 `PageHeader`；筛选栏卡片化并与表格对齐；Loading 时保留 `PageHeader` 与筛选栏 |
| 6 | `/projects` | [ProjectsPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/projects/ProjectsPage.tsx) | **母版 D（主从双栏）** | 顶部保留 `ProjectKnowledgeSummary` 知识库统计带；下方改为「左项目列表（360px 窄栏，**将 `ProjectList` 从 4 列宽表改为紧凑卡片/列表行防横向溢出**，选中带左绿边，保留『仓库绑定/已选择』和『编辑』按钮语义）+ 右当前项目仓库绑定工作区 (`RepoBindingPanel`)」 |
| 7 | `/providers` | [ProvidersPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/providers/ProvidersPage.tsx) | **母版 C（过滤表格）** | `PageHeader` 补齐「凭证只写不回显、连接测试不落库」说明；Loading 时保留 `PageHeader`；表格掩码密钥与连接测试徽标对齐美化 |
| 8 | `/providers/:id/models` | [ModelsPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/models/ModelsPage.tsx) | **母版 C（过滤表格）** | `PageHeader` 集成 `← 返回提供商` 面包屑与当前提供商上下文胶囊；模型参数（Temperature / MaxTokens）用等宽胶囊展示 |
| 9 | `/calls` | [CallsPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/calls/CallsPage.tsx) | **母版 C（审计表格）** | 补齐 `PageHeader` 说明；4 维级联筛选栏（项目/会话/状态/时间）规整为紧凑网格；调用记录行左边框区分成功（绿）/失败（红），展开详情区用等宽面板呈现提示词与注入编号 |

### 批次 UI-3：知识库 4 页与仓库浏览 2 页（资产与代码阅读体验）
| # | 路由 | 页面文件 | 采用母版 | 核心改造要点 |
|---|---|---|---|---|
| 10 | `/knowledge-bases` | [KnowledgeBaseListPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/knowledge/pages/KnowledgeBaseListPage.tsx) | **母版 C（过滤表格）** | 统一接入 `PageHeader`；版本徽标（`v1` / `current`）与条目统计等宽对齐；底部只读说明改为带图标的静态提示条 |
| 11 | `/knowledge-bases/import` | [KnowledgeImportPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/knowledge/pages/KnowledgeImportPage.tsx) | **母版 E（720px 向导）** | 收敛至 `720px` 聚焦向导容器；项目选择与导入面板合入分步卡片；导入成功报告区由「鸮鸮 `success`」领衔展示版本跃迁与条目统计 |
| 12 | `/knowledge-bases/:kbId` | [KnowledgeBrowsePage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/knowledge/pages/KnowledgeBrowsePage.tsx) | **母版 C（吸顶浏览）** | 搜索框 + 6 类知识条目计数 Tab 栏支持 `sticky; top: var(--topbar-height); z-index: 10`；`superseded` 历史版本告警条采用琥珀色左边框；Loading 时保留页头 |
| 13 | `/knowledge-bases/:kbId/entries/:code` | [KnowledgeEntryPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/knowledge/pages/KnowledgeEntryPage.tsx) | **母版 E（880px 阅读）** | 收敛至 `880px` 最佳阅读宽度；条目编号（如 `BL-001`）以大号等宽徽章置顶，正文区采用代码级排版 |
| 14 | `/repos` | [RepoBrowseIndexPage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/repos/pages/RepoBrowseIndexPage.tsx) | **母版 B（项目仓库网格）** | 统一 `PageHeader`；每个项目的绑定仓库改为带 GitHub / 云效原始品牌图标、默认分支胶囊与状态点的可点击行卡片 |
| 15 | `/projects/:projectId/repos/:bindingId` | [RepoBrowsePage.tsx](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/features/repos/pages/RepoBrowsePage.tsx) | **母版 D（双栏代码台）** | 顶栏展示厂商图标 + 仓库名 + 同步基线状态；选择器栏紧凑化；左目录树与右提交流固定高度内滚；`FileViewerDrawer` 宽度严格走 `var(--repo-drawer-width)` 并强化行号与代码阅读质感 |

---

## 八、字体、图标与动效硬约束（速查）

- **字体分工**（离线自托管环境不引入外部 CDN，按 [tokens.css](file:///Users/alon/Developer/OpenSource/ai-test-workbench/web/src/styles/tokens.css) 系统回退栈渲染）：
  - 正文、表单、说明：`--font-family-base`（优先本地 `IBM Plex Sans`，回退 `PingFang SC` / `Microsoft YaHei` / `system-ui`）
  - 页面标题、入口名、编号、SHA、耗时、字符计数、代码块：`--font-family-heading` / `--font-family-mono`（优先本地 `JetBrains Mono`，回退 `SFMono-Regular` / `Menlo` / `monospace`）
- **图标规格**：24×24 网格，`1.75` 描边，圆头圆角，`currentColor`；GitHub 与云效使用品牌原始形态，严禁用文字或 Emoji 冒充图标。
- **动效边界**：
  - 交互反馈 `var(--duration-fast)` (`120ms`)（hover 边框提亮、按钮 `:active` `scale(0.98)`）
  - 面板/抽屉展开 `var(--duration-base)` (`180ms`) `var(--easing-standard)` (`cubic-bezier(0.2, 0, 0, 1)`)
  - 吉祥物自身循环（呼吸 `6s`、HUD 准星旋转 `2.4s`、告警脉冲 `1.8s`）
  - `prefers-reduced-motion: reduce` 下全部归零。
