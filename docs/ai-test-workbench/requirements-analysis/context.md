# Requirements Analysis Context → 下游阶段

## 模块名称

ai-test-workbench（本 spec 只覆盖首个域 `workbench-core`）

## 需求类型

🆕 新产品

## 后续阶段执行路径

- 交互设计：执行。理由：Web 应用需要浏览器端首页入口、会话详情、提供商配置与输入采集界面（`SCOPE: ui=yes`）
- 技术方案：全部执行（tech-stack-advisor → risk-analysis → architecture-confirm → api-design → database-design → component-breakdown → file-structure-generator → task-breakdown）。理由：新库、有对外进程内接口、有密钥与文件落盘、有持久化实体
- 测试验证：全部执行

## 归档路径

docs/ai-test-workbench/
specs/ai-test-workbench_20261117184149/

## 商业目标

- BG-01：后续 4 个域接入 AI 调用与会话记录时零新增密钥读取与 HTTP 客户端代码（以代码评审结论判定）
- BG-02：从任一入口到第一次获得 AI 结果 ≤ 3 步（选项目 → 给输入 → 发起调用）
- BG-03：成功调用 100% 有 AiCallRecord，失败调用 100% 有失败状态与原因
- BG-04：未认证访问 100% 被登录前置校验拦截；登录口令与令牌不落日志、不以明文存储（answers.md 2026-11-17 19:52:50 部署形态变更）
- BG-05 / BG-06：已迁出（知识库 → `specs/knowledge-base_20261117205011`；仓库集成 → `specs/repo-integration_20261117205011`）

## 功能范围

### In Scope（P0 优先）

| 功能点 | 优先级 | 说明 |
|--------|--------|------|
| 单用户登录与访问控制 | P0 | 除登录页/接口外全部要求登录；口令来自 `AW_ADMIN_PASSWORD`、加盐慢哈希比对；会话令牌（HttpOnly/SameSite/Secure）、每次请求刷新 lastSeenAt、空闲 8h 失效且无绝对上限、登出吊销；同一来源 IP 连续 5 次失败锁 5 分钟、成功登录清零（AMB-011~013 已确认） |
| 6 入口导航与占位降级 | P0 | 入口常驻：用例库、分析 bug、排查日志、分析 SQL、生成回归清单、生成测试报告（原「生成测试用例」更名为「用例库」，生成能力在入口内部，AMB-019）；未交付入口进入占位页，配置驱动 |
| AI 提供商配置与连接测试 | P0 | 名称/协议/baseURL/密钥；10s 内返回测试结果 |
| 模型绑定 | P0 | 模型名、显示名、默认参数、启用状态 |
| 统一调用 `ai.complete` + AiCallRecord | P0 | 唯一模型出口，必记录每次调用 |
| 文本粘贴输入 | P0 | 标题 + 正文，追加为会话事件 |
| 文件上传输入 | P0 | 白名单文本类型，落为会话制品 |
| 项目上下文 | P0 | 项目名唯一，绑定仓库地址/技术栈/需求来源 |
| 会话记录 | P0 | 创建、列表、详情、时间线、状态流转 |
| 制品落盘与查看下载 | P0 | `sessions/<sessionId>/` 隔离 |
| 调用记录查询界面 | P1 | 记录本身 P0，查询界面 P1 |
| 会话级参数覆盖 | P1 | temperature / max_tokens |
| 会话删除 / 筛选 | P1 | 手动删除整个会话并级联清理（AMB-009 已确认） |

> 知识库（US-012 ~ US-016）与仓库集成（US-017 ~ US-023）已迁出至独立 spec，编号保留，口径见 `migration-to-specs.md`。

### Out of Scope

- `test-case` / `diagnosis` / `regression-list` / `test-report` 业务能力：独立域，单独 `aw-start`（依据 answers.md：「4,按照建议首个域为 workbench-core」）
- 多用户账号体系、注册 / 口令找回与角色权限：本期只做单用户登录（AMB-004 原「无登录」已被用户于 2026-11-17 19:52:50 推翻）；owner 字段保留但不参与鉴权
- 流式输出、提示词模板库：本期 Won't Have（见 `design.md`）
- 仓库整库克隆、代码索引 / 向量检索 / 代码搜索、Webhook 与定时同步、仓库写操作：已随仓库集成迁出至 `specs/repo-integration_20261117205011`
- 自动过期清理、归档与压缩：会话与制品永久保留，仅手动删除（AMB-009 已确认）
- 本体生成（`ontology-builder-native` 内嵌、人工确认对话框）：独立域 `ontology-builder`，另行 `aw-start`；其产出的知识库文件由 `knowledge-base` spec 导入消费（answers.md 2026-11-17 20:06:58；2026-11-17 20:50:31 拆 spec 后）
- 知识库服务端路径引用、在线编辑条目、代码级新鲜度校验、向量检索 / RAG：已随知识库迁出至 `specs/knowledge-base_20261117205011`

## 用户故事摘要

| US ID | 标题 | 优先级 | AC 数量 |
|-------|------|--------|---------|
| US-001 | 从首页进入六类工作入口 | P0 | 3 |
| US-002 | 进入尚未交付的入口 | P0 | 3 |
| US-003 | 配置 AI 提供商并验证连通 | P0 | 4 |
| US-004 | 为提供商绑定模型 | P0 | 3 |
| US-005 | 统一调用 AI 并记录每次调用 | P0 | 5 |
| US-006 | 粘贴文本作为分析输入 | P0 | 3 |
| US-007 | 上传文件作为分析输入 | P0 | 3 |
| US-008 | 维护项目上下文 | P0 | 3 |
| US-009 | 创建分析会话并回看历史 | P0 | 5 |
| US-010 | 查询 AI 调用记录 | P1 | 3 |
| US-011 | 以单用户身份登录后使用工作台 | P0 | 7 |
> US-012 ~ US-023 已迁出至 `specs/knowledge-base_20261117205011`（US-012 ~ US-016）与 `specs/repo-integration_20261117205011`（US-017 ~ US-023），编号保留。


## AC 完整列表

- AC-001-1: GIVEN 工作台服务可用 WHEN 我打开首页 THEN 展示 6 个入口（含名称与用途说明）
- AC-001-2: GIVEN 我在首页 WHEN 我点击任一入口 THEN 跳转到对应页面路径，刷新后仍在该页面
- AC-001-3: GIVEN 首页加载 WHEN 需要继续上次工作 THEN 展示最近 10 条会话（按更新时间倒序），无会话时展示空态
- AC-002-1: GIVEN 入口对应的域尚未交付 WHEN 进入该页面 THEN 说明所属域与状态，并提供返回首页入口
- AC-002-2: GIVEN 入口尚未交付 WHEN 我停留或刷新 THEN 不创建会话、不发起模型调用、不产生 AiCallRecord
- AC-002-3: GIVEN 入口的域已接入 WHEN 进入该入口 THEN 展示真实功能页；占位状态由入口配置决定
- AC-003-1: GIVEN 填写名称/协议（openai-compatible / anthropic）/baseURL/密钥并保存 WHEN 保存成功 THEN 列表出现该提供商，密钥加密存储且掩码展示，接口不返回完整密钥
- AC-003-2: GIVEN 必填缺失或 baseURL 非法 WHEN 保存 THEN 拒绝并逐字段说明，不写入数据
- AC-003-3: GIVEN 已保存提供商 WHEN 点击连接测试 THEN 10s 内返回成功（含可选模型数）或分类失败原因，不写入会话与制品
- AC-003-4: GIVEN 提供商启用中 WHEN 停用 THEN 其模型不可再选，历史调用记录仍可查
- AC-004-1: GIVEN 存在启用中的提供商 WHEN 新增模型 THEN 出现在可选列表；temperature 0–2、max_tokens 正整数校验
- AC-004-2: GIVEN 同提供商下已有同名模型 WHEN 再次新增 THEN 拒绝并提示重复
- AC-004-3: GIVEN 模型存在 WHEN 在会话中调用 THEN 使用登记默认参数，除非本次显式覆盖
- AC-005-1: GIVEN 会话存在且模型可用 WHEN 调用 `ai.complete` THEN 返回结果文本与 callId，并写成功 AiCallRecord（模型、耗时、提示摘要）
- AC-005-2: GIVEN 提供商返回鉴权失败/限流/5xx 或 120s 内无响应 WHEN 调用结束 THEN 写失败 AiCallRecord 并附错误信息，向调用方抛可读错误
- AC-005-3: GIVEN 会话不存在或模型已停用 WHEN 调用 THEN 在发起外部请求前拒绝，且不产生 AiCallRecord
- AC-005-4: GIVEN 一次调用完成 WHEN 查看会话详情 THEN 展示模型、耗时、状态与提示摘要，摘要不含密钥
- AC-005-5: GIVEN 网络错误或 5xx WHEN 调用结束 THEN 至多自动重试 1 次（每次超时 120s），重试次数写入 AiCallRecord；仍失败按 AC-005-2 记录，不自动切模型
- AC-006-1: GIVEN 在会话内 WHEN 提交标题与正文 THEN 追加 SessionEvent 并可在后续调用中引用
- AC-006-2: GIVEN 正文为空或仅空白 WHEN 提交 THEN 拒绝并提示必填，不追加事件
- AC-006-3: GIVEN 正文超过 200,000 字符 WHEN 提交 THEN 提示当前字数与 200,000 字符上限并拒绝，不静默截断；未超限时正常提交
- AC-007-1: GIVEN 在会话内 WHEN 上传允许类型文件 THEN 保存为制品、时间线出现上传事件、可查看预览与大小
- AC-007-2: GIVEN 类型不在白名单（.txt .md .markdown .log .json .yaml .yml .csv .sql）、单文件 >10MB 或本次 >10 个 WHEN 提交 THEN 拒绝并说明允许范围，不写入制品
- AC-007-3: GIVEN 同会话已存在同名文件 WHEN 再次上传 THEN 自动改名并保留两份，不静默覆盖
- AC-008-1: GIVEN 填写项目名并保存 WHEN 创建 THEN 返回 projectId；项目名全局唯一，重名拒绝
- AC-008-2: GIVEN 项目已存在 WHEN 编辑并保存 THEN 再打开显示最新内容，并记录最后更新时间
- AC-008-3: GIVEN 项目不存在 WHEN 创建会话 THEN 要求先选择或创建项目，不允许无项目会话
- AC-009-1: GIVEN 选定项目与入口 WHEN 创建会话 THEN 生成 sessionId、状态为进行中、置顶于项目会话列表
- AC-009-2: GIVEN 存在多条会话 WHEN 按项目或状态筛选 THEN 只返回匹配项，按更新时间倒序
- AC-009-3: GIVEN 会话详情页 WHEN 一次成功调用后查看 THEN 时间线按发生顺序展示输入事件、调用记录与制品事件
- AC-009-4: GIVEN 会话进行中 WHEN 标记完成或未捕获失败 THEN 状态变为已完成或失败，之后不再接受新输入事件
- AC-009-5: GIVEN 在会话列表或详情页 WHEN 确认删除某会话 THEN 会话、事件、制品文件与调用记录一并删除且不可见，其他会话不受影响；不做自动过期清理
- AC-010-1: GIVEN 已发生多次调用 WHEN 按会话查询 THEN 按时间倒序展示模型、状态、耗时与时间
- AC-010-2: GIVEN 某次调用失败 WHEN 查看记录 THEN 展示错误信息与重试次数，不含密钥原文
- AC-010-3: GIVEN 按时间或项目筛选 WHEN 无匹配 THEN 展示空态而不是错误
- AC-011-1: GIVEN 未登录或登录会话失效 WHEN 访问任意页面或受保护接口 THEN 跳转登录页 / 返回 401，不返回任何业务数据
- AC-011-2: GIVEN 已配置管理员凭据 WHEN 提交正确口令登录成功、签发登录会话令牌并进入首页，响应不含口令或哈希
- AC-011-3: GIVEN 提交错误口令校验失败 THEN 返回不区分原因的统一提示，不签发令牌，响应与日志不含口令原文
- AC-011-4: GIVEN 同一来源 IP 连续失败 5 次 WHEN 再次尝试 THEN 5 分钟内拒绝该来源登录；成功登录后计数清零；不影响已建立会话
- AC-011-5: GIVEN 已登录 WHEN 会话空闲超过 8 小时（每次请求刷新 lastSeenAt，无绝对上限） THEN 下一次请求视为未登录并跳回登录页
- AC-011-6: GIVEN 已登录 WHEN 点击登出 THEN 服务端立即吊销令牌，携带该令牌的后续请求返回 401
- AC-011-7: GIVEN 登录成功 WHEN 浏览器保存令牌 THEN Cookie 为 HttpOnly、SameSite=Lax，HTTPS 下 Secure；令牌原文不出现在 URL、前端可读存储与日志
- AC-012-1 ~ AC-016-3（知识库 24 条）与 AC-017-1 ~ AC-023-6（仓库集成 36 条）已迁出；原文见两份 `_handoff/from-workbench-core.md`


## 数据实体

- AdminCredential：credentialId（单用户固定一条）、passwordHash（加盐慢哈希）、updatedAt；口令明文不落库
- LoginSession：loginSessionId、tokenHash（仅存哈希）、createdAt、lastSeenAt、expiresAt（空闲 8 小时后失效）、revokedAt（登出 / 轮换时写入）
- ProjectContext：projectId、name（全局唯一）、repoUrl、techStack、requirementSource、notes、createdAt、updatedAt（仓库绑定与知识库关联已迁出，本 spec 只保留人工填写字段）
- ProviderConfig：providerId、name、protocol（openai-compatible / anthropic）、baseUrl、apiKeyCiphertext、enabled、createdAt、updatedAt
- ModelBinding：modelId、providerId、modelName、displayName、defaultTemperature、defaultMaxTokens、enabled、createdAt
- Session：sessionId、projectId、entranceKey（6 入口枚举）、title、status（进行中 / 已完成 / 失败）、modelId、createdAt、updatedAt
- SessionEvent：eventId、sessionId、type（输入 / 调用 / 制品 / 状态变更）、payload、createdAt
- Artifact：artifactId、sessionId、kind、fileName、relativePath（`sessions/<sessionId>/…`）、mimeType、byteSize、createdAt
- AiCallRecord：callId、sessionId、modelId、promptDigest、status（成功 / 失败 / 超时）、latencyMs、retryCount、errorMessage、createdAt；不存完整请求正文

## 系统集成点

| 集成目标 | 方向 | 用途 |
|---------|------|------|
| AI 提供商 API（OpenAI 兼容 / Anthropic） | 出站 HTTP | 连接测试与 `ai.complete` 模型调用；仅这两类协议，不做逐家厂商专属适配（AMB-003 已确认） |
| 本地文件系统（会话制品目录） | 双向 | 制品落盘、预览与下载，按 `sessions/<sessionId>/` 隔离 |
| 关系型持久化存储 | 双向 | 项目、提供商、模型、会话、事件、制品与调用记录（选型属技术方案阶段） |
| 后续 4 个业务域 | 进程内 API | `ai.complete`、会话创建与事件追加、制品保存（契约需保持向后兼容） |

## 关键约束

- 交付形态为 Web 应用：浏览器访问的 Web 前端 + 服务端（answers.md：「3.交付web应用」）
- 本 spec 只覆盖 `workbench-core`，其余 4 域独立立项（answers.md：「4,按照建议首个域为 workbench-core」）
- 密钥只由本域持有；以服务端加密存储（口令来自环境变量），任何接口响应、日志与提示摘要中都不得出现完整密钥（AMB-005 已确认）
- 业务域不得自行直连模型；跨域只通过接口，不直接读写对方数据
- 制品按 `sessions/<sessionId>/` 隔离，路径不得跨会话引用
- 每次进入提供商的模型调用（成功或失败）都必须留下 AiCallRecord
- 单用户登录：除登录页与登录接口外所有页面/接口要求有效登录会话，未认证跳转登录页 / 返回 401；只做单账号，不做注册、找回与角色权限（AMB-004 原「无登录」已被用户 2026-11-17 19:52:50 推翻）
- 口令仅存加盐慢哈希并恒定时间比较；登录会话令牌仅存哈希，Cookie 为 HttpOnly、SameSite=Lax，HTTPS 下 Secure；每次请求刷新 lastSeenAt，空闲 8 小时失效且无绝对上限，登出立即吊销；同一来源 IP 连续失败 5 次锁 5 分钟，成功登录后计数清零（AMB-012/AMB-013 已确认）
- 登录口令、口令哈希与登录会话令牌原文不得出现在日志、接口响应、AiCallRecord 与界面中
- 管理员口令由环境变量 `AW_ADMIN_PASSWORD` 提供，启动时转存为加盐慢哈希；变量缺失则拒绝启动；轮换 = 修改环境变量后重启（AMB-011 已确认）
- 提供商只支持 OpenAI 兼容协议与 Anthropic 官方 API 两类（AMB-003 已确认）
- 上传白名单 `.txt .md .markdown .log .json .yaml .yml .csv .sql`，单文件 ≤10MB、单次 ≤10 个，同名自动改名（AMB-007 已确认）
- 模型调用单次超时 120s，仅网络错误与 5xx 自动重试 1 次，失败留痕且不自动切模型（AMB-008 已确认）；连接测试独立 10s 超时
- 会话与制品永久保留，仅支持手动删除整个会话并级联清理（AMB-009 已确认）
- 文本粘贴单次正文上限 200,000 字符（约 200KB），超出拒绝并提示当前字数与上限，不静默截断（AMB-010 已确认）
- 本体生成（`ontology-builder-native` 内嵌、人工确认）不在本期，拆为 `ontology-builder` 域（answers.md 2026-11-17 20:06:58）

## 状态

pending（2026-11-17 20:50:31 收窄：知识库与仓库集成已迁出至独立 spec；本 spec 只保留 workbench-core 基座，US-001 ~ US-011、AC 42 条、EARS 17 条；无遗留待确认项，本阶段需用户确认）
