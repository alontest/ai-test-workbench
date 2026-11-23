# Design System

| Token | 值 | 用途 |
|-------|----|------|
| `--color-primary` | `#1E293B` / `#EDEDED` | 主按钮、选中态底色 |
| `--color-on-primary` | `#FFFFFF` / `#0A0A0B` | 主色上的文字 |
| `--color-primary-hover` | `#0F172A` / `#D4D4D8` | 主按钮 hover |
| `--color-secondary` | `#475569` / `#26262B` | 次级按钮、次级表面 |
| `--color-on-secondary` | `#FFFFFF` / `#EDEDED` | 次级色上的文字 |
| `--color-accent` | `#16A34A` / `#22C55E` | 运行/成功强调、链接悬停 |
| `--color-on-accent` | `#FFFFFF` / `#0A0A0B` | 强调色上的文字 |
| `--color-background` | `#F8FAFC` / `#0A0A0B` | 页面背景 |
| `--color-foreground` | `#0F172A` / `#EDEDED` | 正文文字 |
| `--color-card` | `#FFFFFF` / `#141416` | 卡片、面板、表格底 |
| `--color-card-foreground` | `#0F172A` / `#EDEDED` | 卡片上的文字 |
| `--color-muted` | `#F1F5F9` / `#1C1C1F` | 弱化表面、表头、代码块底 |
| `--color-muted-foreground` | `#475569` / `#A1A1AA` | 次要文字、占位符 |
| `--color-border` | `#CBD5E1` / `#2A2A2E` | 边框、分隔线 |
| `--color-input` | `#FFFFFF` / `#0A0A0B` | 输入框底色 |
| `--color-destructive` | `#DC2626` / `#EF4444` | 删除、失败 |
| `--color-on-destructive` | `#FFFFFF` / `#0A0A0B` | 危险色上的文字 |
| `--color-success` | `#16A34A` / `#22C55E` | 成功徽标、已完成 |
| `--color-warning` | `#B45309` / `#F59E0B` | 接近上限、警告 |
| `--color-info` | `#0284C7` / `#38BDF8` | 进行中徽标、提示 |
| `--color-ring` | `#1E293B` / `#22C55E` | 焦点环 |
| `--font-family-base` | `"IBM Plex Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif` | 正文、表单、表格 |
| `--font-family-heading` | `"JetBrains Mono", "SFMono-Regular", Menlo, monospace` | 页面标题、入口名 |
| `--font-family-mono` | `"JetBrains Mono", "SFMono-Regular", Menlo, monospace` | ID、模型名、日志与制品预览 |
| `--font-size-xs` | `12px` | 徽标、辅助说明、字数计数 |
| `--font-size-sm` | `13px` | 表格、次要文字 |
| `--font-size-base` | `14px` | 正文、表单控件 |
| `--font-size-md` | `16px` | 卡片标题 |
| `--font-size-lg` | `18px` | 区块标题 |
| `--font-size-xl` | `24px` | 页面标题 |
| `--font-size-2xl` | `32px` | 首页主标题 |
| `--font-weight-normal` | `400` | 正文 |
| `--font-weight-medium` | `500` | 强调、表格表头 |
| `--font-weight-bold` | `600` | 按钮、标题 |
| `--line-height-tight` | `1.25` | 标题 |
| `--line-height-base` | `1.5` | 正文 |
| `--line-height-relaxed` | `1.7` | 日志与长文本预览 |
| `--spacing-1` | `4px` | 图标与文字间隙 |
| `--spacing-2` | `8px` | 紧凑内边距、徽标间距 |
| `--spacing-3` | `12px` | 控件内边距 |
| `--spacing-4` | `16px` | 标准内边距、卡片间距 |
| `--spacing-6` | `24px` | 区块间距 |
| `--spacing-8` | `32px` | 大区块间距 |
| `--spacing-12` | `48px` | 页面级留白 |
| `--spacing-16` | `64px` | 首页主标题上方留白 |
| `--radius-sm` | `4px` | 输入框、徽标、标签 |
| `--radius-md` | `8px` | 卡片、下拉、表格容器 |
| `--radius-lg` | `12px` | 对话框、抽屉 |
| `--radius-full` | `9999px` | 状态胶囊 |
| `--shadow-sm` | `0 1px 2px rgba(15, 23, 42, 0.08)` / `0 1px 2px rgba(0, 0, 0, 0.6)` | 轻抬升（输入聚焦） |
| `--shadow-md` | `0 4px 6px rgba(15, 23, 42, 0.12)` / `0 4px 10px rgba(0, 0, 0, 0.55)` | 卡片、下拉 |
| `--shadow-lg` | `0 10px 15px rgba(15, 23, 42, 0.18)` / `0 16px 32px rgba(0, 0, 0, 0.6)` | 对话框、抽屉 |
| `--duration-fast` | `120ms` | hover、焦点 |
| `--duration-base` | `180ms` | 展开/收起、状态切换 |
| `--duration-slow` | `240ms` | 对话框进出 |
| `--easing-standard` | `cubic-bezier(0.2, 0, 0, 1)` | 默认缓动 |
| `--sidebar-width` | `248px` | 桌面侧边栏 |
| `--topbar-height` | `64px` | 顶栏高度 |
| `--content-max-width` | `1280px` | 内容区最大宽度 |

## 修订记录：暗色主题改为近黑中性（2026-11-17）

依据 answers.md：「全部 A，但是你现在的暗色色调我不满意」「暗色基调：近黑中性（背景 #0A0A0B、卡片 #141416、弱化 #1C1C1F、边框 #2A2A2E、正文 #EDEDED、次要字 #A1A1AA）」「强调色：保持绿色 #22C55E」。

本表 Dark 列已由 slate 色调（`#0F172A` / `#1B2336` / `#272F42` / `#475569` / `#F8FAFC`）更新为近黑中性；Light 列未改。重推的 Dark 值：

| Token | 旧 Dark | 新 Dark | 推导说明 |
|-------|---------|---------|----------|
| `--color-primary` | `#1E293B` | `#EDEDED` | 近黑底上深色主按钮不可见，改为反色中性主按钮，`--color-on-primary` 同步为 `#0A0A0B` |
| `--color-primary-hover` | `#334155` | `#D4D4D8` | 反色按钮的 hover 略微压暗，保持 13.39:1 |
| `--color-secondary` | `#334155` | `#26262B` | 中性次级表面，落在卡片与边框之间 |
| `--color-ring` | `#F8FAFC` | `#22C55E` | 焦点环改用强调绿，与反色主按钮区分，对背景 8.69:1 |
| `--color-input` | `#0F172A` | `#0A0A0B` | 与页面同色，靠边框与焦点环区分输入框 |
| `--color-card-foreground` | `#F8FAFC` | `#EDEDED` | 随正文改为近白中性 |

对比度实测（WCAG 2.1，`python3` 计算）：正文/背景 16.90:1、正文/卡片 15.72:1、正文/弱化表面 14.52:1、次要文字/背景 7.72:1、次要文字/卡片 7.18:1、on-primary/primary 16.90:1、on-primary/primary-hover 13.39:1、on-secondary/secondary 12.86:1、on-accent/accent 8.69:1、ring/背景 8.69:1、destructive/背景 5.26:1、warning/背景 9.21:1、info/背景 9.24:1；正文与背景 ≥ 4.5:1 的要求满足。边框 `#2A2A2E` 对背景 1.38:1，仅作分层与输入框轮廓，焦点态改用 ring。

## 登录页（US-011，2026-11-17）：无新增 token

登录页不新增 token，复用上表既有 token，Dark 仍为近黑中性、Light 保持 slate 体系。使用映射：

| 用途 | 复用 token |
|------|-----------|
| 登录页背景 | `--color-background` |
| 登录卡片 | `--color-card` + `--color-border` + `--radius-lg` + `--shadow-lg` |
| 口令输入 | `--color-input` + `--color-border` + `--radius-sm` + `--color-ring`（焦点） |
| 登录按钮 | `--color-primary` / `--color-on-primary` / `--color-primary-hover` |
| 错误与锁定 | `--color-destructive` / `--color-on-destructive` |
| 会话过期与登出提示 | `--color-info` |
| 页面标题 / 品牌 | `--font-family-heading`、`--font-size-xl` |

Light / Dark 下正文与背景对比度均 ≥ 4.5:1，与工作台正文一致（Dark 16.90:1，Light 17.06:1）。

## 收窄（2026-11-17）：无 token 变更

知识库（US-012 ~ US-016）已整体迁出到 `specs/knowledge-base_20261117205011`，其交互口径见该 spec 的 `_handoff/from-interaction-design.md`。本 spec 移除知识库列表 / 导入 / 浏览 / 详情 / 注入 / 删除后，未新增、修改或删除任何 token；上表保持原样，Light 与 Dark 两套值继续供剩余页面与登录页复用。
