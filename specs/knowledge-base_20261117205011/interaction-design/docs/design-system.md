# Design System

> 知识库模块（US-012 ~ US-016）不新增 token，全部沿用 workbench-core 已确认的设计系统（来源：`specs/ai-test-workbench_20261117184149/interaction-design/design.md` 与 `docs/design-system.md`）。本表登记本模块实际引用的 token 与值，供实现与后续模块对照；值与 core 逐字一致，不得在本模块改写。

| Token | 值 | 用途 |
|-------|----|------|
| `--color-primary` | `#1E293B` / `#EDEDED` | 主按钮（导入、提交、发起调用） |
| `--color-on-primary` | `#FFFFFF` / `#0A0A0B` | 主按钮文字 |
| `--color-primary-hover` | `#0F172A` / `#D4D4D8` | 主按钮 hover |
| `--color-secondary` | `#475569` / `#26262B` | 次级按钮、次级表面 |
| `--color-on-secondary` | `#FFFFFF` / `#EDEDED` | 次级按钮文字 |
| `--color-accent` | `#16A34A` / `#22C55E` | 链接、选中强调、焦点 |
| `--color-on-accent` | `#FFFFFF` / `#0A0A0B` | 强调色上的文字 |
| `--color-background` | `#F8FAFC` / `#0A0A0B` | 页面背景 |
| `--color-foreground` | `#0F172A` / `#EDEDED` | 正文文字 |
| `--color-card` | `#FFFFFF` / `#141416` | 卡片、表格、对话框 |
| `--color-card-foreground` | `#0F172A` / `#EDEDED` | 卡片上的文字 |
| `--color-muted` | `#F1F5F9` / `#1C1C1F` | 表头、弱化表面、正文块底 |
| `--color-muted-foreground` | `#475569` / `#A1A1AA` | 次要文字、未知 / 已删除徽标 |
| `--color-border` | `#CBD5E1` / `#2A2A2E` | 边框、分隔线、输入轮廓 |
| `--color-input` | `#FFFFFF` / `#0A0A0B` | 输入框底色 |
| `--color-destructive` | `#DC2626` / `#EF4444` | 删除、校验失败、超限、失效条目 |
| `--color-on-destructive` | `#FFFFFF` / `#0A0A0B` | 危险按钮文字 |
| `--color-success` | `#16A34A` / `#22C55E` | 导入成功、校验通过、已就绪 |
| `--color-warning` | `#B45309` / `#F59E0B` | 版本冲突、可能过期、>90% 预算 |
| `--color-info` | `#0284C7` / `#38BDF8` | 旧版本只读 banner、提示 |
| `--color-ring` | `#1E293B` / `#22C55E` | 焦点环 |
| `--font-family-base` | `"IBM Plex Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif` | 正文、表单、表格 |
| `--font-family-heading` | `"JetBrains Mono", "SFMono-Regular", Menlo, monospace` | 页面标题、知识库名 |
| `--font-family-mono` | `"JetBrains Mono", "SFMono-Regular", Menlo, monospace` | 编号、代码路径、正文预览 |
| `--font-size-xs` | `12px` | 徽标、辅助说明、字符计数 |
| `--font-size-sm` | `13px` | 表格、次要文字 |
| `--font-size-base` | `14px` | 正文、表单控件 |
| `--font-size-md` | `16px` | 卡片标题 |
| `--font-size-lg` | `18px` | 区块标题 |
| `--font-size-xl` | `24px` | 页面标题 |
| `--font-size-2xl` | `32px` | 空态主标题 |
| `--font-weight-normal` | `400` | 正文 |
| `--font-weight-medium` | `500` | 表头、强调 |
| `--font-weight-bold` | `600` | 按钮、标题 |
| `--line-height-tight` | `1.25` | 标题 |
| `--line-height-base` | `1.5` | 正文 |
| `--line-height-relaxed` | `1.7` | 正文块、导入报告 |
| `--spacing-1` | `4px` | 图标与文字间隙 |
| `--spacing-2` | `8px` | 徽标间距、紧凑内边距 |
| `--spacing-3` | `12px` | 控件内边距、行间距 |
| `--spacing-4` | `16px` | 标准内边距、卡片间距 |
| `--spacing-6` | `24px` | 区块间距 |
| `--spacing-8` | `32px` | 大区块间距 |
| `--spacing-12` | `48px` | 页面级留白 |
| `--spacing-16` | `64px` | 空态上方留白 |
| `--radius-sm` | `4px` | 输入框、徽标、按钮 |
| `--radius-md` | `8px` | 卡片、表格容器、下拉 |
| `--radius-lg` | `12px` | 对话框 |
| `--radius-full` | `9999px` | 状态胶囊、预算条 |
| `--shadow-sm` | `0 1px 2px rgba(15, 23, 42, 0.08)` / `0 1px 2px rgba(0, 0, 0, 0.6)` | 输入聚焦、行 hover |
| `--shadow-md` | `0 4px 6px rgba(15, 23, 42, 0.12)` / `0 4px 10px rgba(0, 0, 0, 0.55)` | 卡片、下拉 |
| `--shadow-lg` | `0 10px 15px rgba(15, 23, 42, 0.18)` / `0 16px 32px rgba(0, 0, 0, 0.6)` | 删除 / 失效条目对话框 |
| `--duration-fast` | `120ms` | hover、焦点 |
| `--duration-base` | `180ms` | 状态切换、展开 |
| `--duration-slow` | `240ms` | 对话框进出 |
| `--easing-standard` | `cubic-bezier(0.2, 0, 0, 1)` | 默认缓动 |
| `--sidebar-width` | `248px` | 桌面侧边栏 |
| `--topbar-height` | `64px` | 顶栏高度 |
| `--content-max-width` | `1280px` | 内容区最大宽度 |

## 修订记录：知识库模块（2026-11-18）

- **新增 token：无。** 知识库页面全部复用上表值，Dark 仍为近黑中性（背景 `#0A0A0B`、卡片 `#141416`、弱化表面 `#1C1C1F`、边框 `#2A2A2E`、正文 `#EDEDED`、次要字 `#A1A1AA`），强调绿 `#22C55E` 只用于运行 / 成功 / 焦点。
- **语义映射（组合既有 token，不新增变量）**：

| 语义 | 复用 token |
|------|-----------|
| 已就绪 / 导入通过 | `--color-success` |
| 版本冲突 / 可能过期 / 预算 >90% | `--color-warning` |
| 未知 / 正文缺失 / 知识库已删除 | `--color-muted-foreground` + `--color-border` |
| 校验失败 / 超限 / 删除 / 失效条目 | `--color-destructive` |
| 旧版本只读 banner | `--color-info` |
| 类型标记、编号、代码路径 | `--font-family-mono` + `--color-muted` |

- **对比度复核（沿用 core 实测值）**：Light 正文/背景 17.06:1；Dark 正文/背景 16.90:1、正文/卡片 15.72:1、次要文字/背景 7.72:1、on-primary/primary 16.90:1、accent/背景 8.69:1、warning/背景 9.21:1、info/背景 9.24:1、destructive/背景 5.26:1；正文与背景 ≥ 4.5:1 满足。
- **来源**：`specs/knowledge-base_20261117205011/interaction-design/design.md`「Design Tokens」。
