# Design System

本文件继承 `workbench-core` 的 Design Tokens（来源：`specs/ai-test-workbench_20261117184149/interaction-design/docs/design-system.md`）。下表所有行**逐字保留、未改未删**；`repo-integration` 的新增 token 追加在文件末尾，供 `kb-sync` 逐条比对。

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

## repo-integration 新增（2026-11-18）

只新增 3 条；不重定义配色与组件体系。

| Token | 值 | 用途 |
|-------|----|------|
| `--color-overlay` | `rgba(15,23,42,0.45)` / `rgba(0,0,0,0.65)` | 文件查看抽屉与解绑确认对话框的遮罩（非文本，不参与对比度要求） |
| `--spacing-5` | `20px` | 目录树单级缩进（`20px × depth`） |
| `--repo-drawer-width` | `480px` | 文件查看抽屉宽度；≤768px 时为 100% |

## 沿用映射（本增量使用）

| 用途 | 复用 token |
|------|-----------|
| 绑定状态：已连接 / 测试成功 / 同步成功 | `--color-success` |
| 令牌失效 / 鉴权失败 / 超限 / 二进制 / 非法路径 / 解绑 | `--color-destructive` |
| 即将过期 / 权限不足 / 供应商限流 / 目录树不完整 | `--color-warning` |
| 同步进行中 / 实时读取提示 / GitHub 提供商徽标 | `--color-info` |
| 未验证 / 已解绑 / 次要说明 | `--color-muted-foreground` + `--color-border` |
| 主按钮（添加绑定 / 同步 / 保存） | `--color-primary` + `--color-on-primary` + `--color-primary-hover` |
| 仓库全名 / 分支 / sha / 路径 / 令牌掩码 / 文件内容 | `--font-family-mono` |
| 卡片、绑定行、同步记录表 | `--color-card` + `--color-border` + `--radius-md` |
| 文件抽屉 / 解绑对话框 | `--shadow-lg` + `--radius-lg` + `--color-overlay` |

对比度：除 `--color-overlay`（非文本遮罩）外，全部沿用 core 已实测值（Light / Dark 正文与背景 ≥ 4.5:1；暗色正文/背景 16.90:1、次要文字/背景 7.72:1、on-primary/primary 16.90:1）。
