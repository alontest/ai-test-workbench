# Requirements Analysis Context → 下游阶段

## 模块名称

knowledge-base

## 需求类型

➕ 功能新增

## 后续阶段执行路径

- 交互设计：执行（SCOPE: ui=yes）。复用 workbench-core 的 AppShell、设计 token、登录态与通用组件；`_handoff/from-interaction-design.md` 的 5 处线框、17 个组件行为与 10 条交互取舍可直接照用，本阶段只复核新 spec 边界与 AC-UX 编号
- 技术方案：全部执行（tech-stack-advisor 只记录继承约束，不重新选型；risk-analysis → architecture-confirm → api-design → database-design → component-breakdown → file-structure-generator → task-breakdown）。`_handoff/from-tech-arch.md` 已给表结构、索引、接口签名、解析护栏与检索方案，需逐条复核并确认 7 项「待技术方案」
- 测试验证：全部执行（test-case-generator → auto-test-runner），覆盖 24 条 AC 与 7 条 EARS

## 归档路径

docs/knowledge-base/
specs/knowledge-base_20261117205011/

## 商业目标

- BG-05: 打通知识库「导入 → 浏览 → 注入」闭环；每次使用注入的调用 100% 可在 AiCallRecord 与 SessionEvent 中回查到知识库名、版本、编号列表与字符数（不含正文）；导入失败 0 残留、超限 0 截断、日志 0 正文泄露

## 功能范围

### In Scope（P0 优先）

| 功能点 | 优先级 | 说明 |
|--------|--------|------|
| 导入知识库并建立编号索引 | P0 | `.json` / `.md` / `.markdown`，必须含 `index.json`；`index.json` ≤20MB、其他单文件 ≤10MB、单次 ≤50 个、单库合计 ≤100MB；前缀映射七类 + 「其他」；部分条目跳过并报行号；失败整体回滚；项目上下文展示 0..n 个知识库 |
| 浏览与检索条目 | P0 | 按项目 / 知识库 / 类型筛选；编号前缀、完整编号、关键词（标题 / 摘要 / 正文）；详情含字段、表、代码路径、一跳邻居、来源文件、新鲜度；正文缺失标「正文缺失」 |
| 会话内按编号注入 | P0 | 「编号 + 标题 + 正文（缺失用摘要）」；实时字数；注入 + 提示 ≤200,000 字符，超限拒绝不截断；失效条目剔除后弹阻塞式确认再继续（AMB-026）；不另设条目数上限（AMB-027）；只记录知识库、版本、编号、字符数，不记正文 |
| 新鲜度与版本冲突提示 | P1 | 只读 `index.json` 元数据；缺失「未知」；同编号摘要不同「版本冲突」并列来源；超 30 天「可能过期」；只提示不阻断；不克隆仓库、不解析代码 |
| 删除知识库 | P1 | 级联删除知识库 / 条目 / 文件并移除项目关联；历史会话、制品与调用记录不变，编号标「知识库已删除」；永久保留，不自动过期 |

### Out of Scope

- 本体生成（`ontology-builder` 独立域）、服务端路径引用、在线编辑条目
- 代码级新鲜度校验、向量检索 / RAG / 代码索引
- AI 网关、会话 / 事件、制品落盘、凭证加密、登录与访问控制、AppShell 与设计 token（归 workbench-core）
- 云效 / GitHub 仓库绑定、同步与凭证（归 repo-integration）
- 多用户 / 角色权限、知识库跨项目转移与重命名、单独删除历史版本、自动过期清理

## 用户故事摘要

| US ID | 标题 | 优先级 | AC 数量 |
|-------|------|--------|---------|
| US-012 | 导入知识库并建立编号索引 | P0 | 7 |
| US-013 | 浏览与检索知识库条目 | P0 | 5 |
| US-014 | 勾选编号注入调用上下文 | P0 | 5 |
| US-015 | 识别知识库新鲜度与版本冲突 | P1 | 4 |
| US-016 | 删除知识库 | P1 | 3 |
| 合计 | — | — | 24 |

EARS 验收标准：AC-REQ-18 ~ AC-REQ-24（7 条，见 `requirements.md`）。

## AC 完整列表

- AC-012-1: GIVEN 在某项目下发起导入 WHEN 上传含一个 `index.json` 与可选 `.md` / `.markdown` 的文件 THEN 校验解析后创建知识库，列表展示名称、生成时间（缺失「未知」）、条目数与状态「已就绪」
- AC-012-2: GIVEN 类型不在 `.json .md .markdown`、缺 `index.json`、单文件或单次超限 WHEN 提交 THEN 拒绝并逐项说明允许范围与上限，不写文件、不建知识库
- AC-012-3: GIVEN `index.json` 非法 / 缺最小结构（版本标识 + 条目集合）/ 条目集合为空 WHEN 提交 THEN 拒绝并提示期望结构，不创建知识库
- AC-012-4: GIVEN `index.json` 合法 WHEN 解析 THEN 按编号建索引（编号、类型、标题、字段、表、代码路径、一跳邻居、新鲜度），`TERM/ENT/ST/BR/BP/API/DE` 映射七类，未知前缀归「其他」
- AC-012-5: GIVEN 部分条目不合法（缺编号 / 编号重复 / 字段类型错误） WHEN 解析结束 THEN 跳过并在报告列行号与原因，其余正常导入；无可导入条目则整体失败
- AC-012-6: GIVEN 导入成功 WHEN 打开项目上下文页 THEN 看到关联的 0..n 个知识库及状态，可跳转浏览页
- AC-012-7: GIVEN 导入失败或解析 / 落盘出错 WHEN 结束 THEN 不留任何文件、知识库记录或条目索引（整体回滚）
- AC-013-1: GIVEN 项目下已有知识库 WHEN 打开浏览页 THEN 按知识库与类型分组列出编号与标题，支持按项目 / 知识库 / 类型筛选；无匹配展示空态
- AC-013-2: GIVEN 在浏览页 WHEN 点击编号 THEN 详情展示字段、表、代码路径、一跳邻居、来源文件与新鲜度；邻居编号可跳转同项目条目
- AC-013-3: GIVEN 输入编号前缀 / 完整编号 / 关键词（匹配标题、摘要、正文） THEN 只返回匹配条目并标明所属知识库与版本；无匹配空态
- AC-013-4: GIVEN 版本已被新版本取代 WHEN 查看详情 THEN 标「已被新版本取代」并提供跳转最新版；浏览页默认最新版
- AC-013-5: GIVEN 正文来自 `.md` WHEN 查看详情 THEN 展示正文；`.md` 未上传或无法匹配 THEN 展示摘要并标「正文缺失」
- AC-014-1: GIVEN 在会话内 WHEN 打开选择器勾选条目 THEN 实时显示已选条目数、注入字符数与「用户正文 + 注入」合计字符数
- AC-014-2: GIVEN 勾选条目并发起调用 WHEN 调用发起 THEN 按「编号 + 标题 + 正文（缺失用摘要）」注入，并在 AiCallRecord 与 SessionEvent 记录知识库、编号列表与字符数（不记正文）
- AC-014-3: GIVEN 提示正文 + 注入超过 200,000 字符 WHEN 发起调用 THEN 拒绝并显示分段字符数与上限，不截断；可调整后重试
- AC-014-4: GIVEN 条目属于已删除知识库 / 已被取代 / 不存在 WHEN 发起调用 THEN 发起外部请求前剔除这些条目并弹阻塞式确认列出被剔除编号（不静默降级）；确认后其余有效条目照常参与调用并产生 AiCallRecord，取消则不发起调用且不产生 AiCallRecord（2026-11-18 按 AMB-026 修正，原编号保留）
- AC-014-5: GIVEN 注入并完成调用 WHEN 回看会话与调用记录 THEN 看到所用知识库、编号列表与字符数；正文与注入内容不出现在日志与错误响应
- AC-015-1: GIVEN 知识库已导入 WHEN 查看浏览页或详情 THEN 展示生成时间与条目新鲜度；缺失显示「未知」，不推测
- AC-015-2: GIVEN 同项目两个知识库或同一知识库两个版本存在相同编号且摘要不同 WHEN 查看条目 THEN 标「版本冲突」并列出冲突来源（知识库名 + 版本 + 生成时间）
- AC-015-3: GIVEN 条目新鲜度超 30 天 WHEN 查看或勾选 THEN 标「可能过期」；注入预览与注入块携带知识库名与生成时间
- AC-015-4: GIVEN 存在新鲜度或冲突提示 WHEN 发起调用 THEN 只提示不阻止（失效条目按 AC-014-4）；不克隆仓库、不解析代码
- AC-016-1: GIVEN 项目下存在知识库 WHEN 确认删除 THEN 知识库、条目索引与已存文件一并删除，项目关联移除，浏览页不再出现
- AC-016-2: GIVEN 知识库已删除 WHEN 回看历史会话与调用记录 THEN 记录与编号列表保留并标「知识库已删除」；历史事件、制品与调用记录不被修改或清空
- AC-016-3: GIVEN 同项目还有其他知识库 WHEN 删除其中一个 THEN 其他知识库与条目不受影响；知识库默认永久保留，不自动过期

## 数据实体

- KnowledgeBase（知识库，一个版本快照）：kbId、projectId、name（同项目内唯一）、nameKey、version、currentFlag、status（ready / superseded）、indexGeneratedAt、entryCount、fileCount、totalByteSize、sourceIndexSha256、storageDir、supersededByKbId、createdAt、updatedAt
- KnowledgeEntry（知识库条目）：entryId、kbId、code、codeKey、type（term / entity / state / rule / process / api / domain_event / other）、title、summary、body、bodyMissing、bodySourceFile、fields、tables、codePaths、neighbors、extras、sourceDoc、anchor、freshnessAt、contentDigest
- 知识注入快照（会话事件 / AiCallRecord 载荷，归 core 记录）：kbId、kbName、kbVersion、entryCodes、injectedChars、promptChars、totalChars；只记标识与字符数，不复制正文

## 系统集成点

| 集成目标 | 方向 | 用途 |
|---------|------|------|
| ProjectContext（workbench-core） | 读取 | 知识库归属 `projectId`；同项目名称唯一；项目上下文页展示关联知识库 |
| `AiGateway.complete`（workbench-core） | 调用 | 唯一模型出口与唯一预算校验点；本 spec 产出 `PreparedPrompt`（注入块 + 分段字数） |
| `sessions.create` / `sessions.append_event`（workbench-core） | 调用 | 追加 `knowledge_injection` 事件（知识库、版本、编号列表、字符数） |
| AiCallRecord（workbench-core） | 读取 / 由 core 写入 | 记录注入快照与字符数；读取时按 kbId 判定「知识库已删除」 |
| `artifacts.save`（workbench-core） | 不使用 | 知识库文件走独立 `knowledge-bases/` 根，不复用制品通道与限额 |
| 登录态 / AuthGate / AppShell / 设计 token（workbench-core） | 复用 | 侧边栏「基座管理」入口与会话面板注入；不另建外壳 |
| 本地本体工具（工作台外） | 文件上传（外部） | `ontology-builder-native` / `ontology-consumption` 产出 `index.json` + `.md`，用户上传；工作台无外部网络调用 |

## 关键约束

- 仅 `.json` / `.md` / `.markdown`，必须含 `index.json`；`index.json` ≤20MB、其他单文件 ≤10MB、单次 ≤50 个、单库合计 ≤100MB；超限逐项拒绝并提示，失败整体回滚
- 注入按「编号 + 标题 + 正文（缺失用摘要）」；注入 + 提示合计 ≤200,000 字符（Unicode 码点）；超限拒绝、不截断；常量 `AW_PROMPT_MAX_CHARS` 由 workbench-core 单点定义，本 spec 引用同值
- 知识库归属项目（0..n），同项目名称唯一；同名重导生成新版本，旧版本只读，浏览默认最新版
- 新鲜度与版本冲突只提示不阻断；缺失显示「未知」；不克隆仓库、不解析代码
- 删除级联知识库 / 条目 / 文件并移除项目关联；历史会话、制品与 AiCallRecord 不变，相关编号标「知识库已删除」；永久保留，不做自动过期
- 知识库内容视为不可信输入；正文 / 摘要 / 字段值不得进入应用日志、错误响应与 AiCallRecord；正文按纯文本展示，不渲染 HTML
- 知识库正文只来自上传的 `.md`，缺正文时用摘要并标「正文缺失」，不以空内容冒充正文
- 跨 spec 依赖不得改写 core 契约：`AiGateway.complete`、`sessions.*`、凭证加密、单用户登录边界、错误体 `{code, message, details[], requestId}` 与分页 `limit` + `cursor`
- 失效条目（已删除 / 已被取代 / 不存在）在发起外部请求前剔除并弹阻塞式确认，列出被剔除编号；确认后其余条目照常调用并产生 AiCallRecord，取消则不发起调用（AMB-026，2026-11-18）
- 单次注入不另设条目数上限，仅受 200,000 字符合计与条目可用性约束（AMB-027，2026-11-18）

## 状态

confirmed
