# Requirements Analysis Context → 下游阶段

## 模块名称

repo-integration

## 需求类型

➕ 功能新增

## 后续阶段执行路径

- 交互设计：执行（SCOPE: ui=yes）。**在 workbench-core 项目上下文页（US-008）内做增量面板**：绑定表单（含掩码与更新令牌）、连通性测试四类结果、同步按钮与上次同步时间 / 耗时 / 结果、仓库 / 分支选择器、提交与目录树、单文件查看、令牌失效提示与撤销二次确认。复用 core 的 AppShell、侧边栏「基座管理」分组、Dark-first 设计基调与既有错误 / 分页约定，不重画整页；需补 AC-UX 与组件状态。
- 技术方案：全部执行（`tech-stack-advisor` 只确认沿用增量，不重新选型；`risk-analysis` → `architecture-confirm` → `api-design` → `database-design` → `component-breakdown` → `file-structure-generator` → `task-breakdown`）。必须给出四类表与 Alembic 迁移、五个供应商适配器契约、错误分类映射、响应头读取（分页 `x-total` / `x-page`、限流 `X-RateLimit-*`）、并发同步互斥、目录树 `truncated` 表示与跨域只读接口；对 8 项「待技术方案」逐条结论。
- 测试验证：全部执行（`test-case-generator` → `auto-test-runner`），覆盖 36 条 AC 与 11 条 EARS，重点为令牌不落日志 / 掩码、四类连通性结果、并发同步、失败保留旧元数据、限流提示、目录树 truncated、1 MiB 上限、二进制 / 非 UTF-8 拒绝、路径穿越、令牌失效恢复、解绑后不再请求。

## 归档路径

docs/repo-integration/
specs/repo-integration_20261117205011/

## 商业目标

- BG-06: 打通仓库接入闭环（承接口径，待用户复核）——仓库元数据与按需文件内容可直接查看与引用；7 个 US / 36 条 AC / 11 条 EARS 全部通过；接口响应与日志中完整令牌出现次数为 0

## 功能范围

### In Scope（P0 优先）

| 功能点 | 优先级 | 说明 |
|--------|--------|------|
| 仓库绑定与令牌 | P0 | 云效 Codeup / GitHub；令牌加密存储、掩码回显；同项目同提供商 + 同仓库唯一；0..n 并提示建议 ≤ 5；更新令牌只替换令牌与掩码；只读最小权限提示 |
| 连通性测试 | P0 | 一次只读请求、10s 内四类结果（成功 / 鉴权失败 / 网络失败 / 权限不足）；记录时间与分类；不写会话、制品与 AiCallRecord |
| 手动同步 | P0 | 仓库信息 + 全部分支 + 最近 100 条提交作为**基线快照**（不含目录树与文件内容）；同绑定禁止并发；失败保留上次成功元数据与时间；限流展示可重试时间；不做定时与轮询 |
| 仓库 / 分支选择 | P0 | **实时读取**（供应商分页）并支持名称 / 关键词检索；默认绑定仓库与默认分支；未同步空态；令牌失效时展示带时间标记的上次同步基线 |
| 提交与目录树浏览 | P0 | 提交与目录树**实时读取**；提交 sha 短号、标题、作者、时间、倒序、翻页；目录逐级展开（名称、类型、大小）；截断提示「目录树不完整」 |
| 按需读取单文件 | P0 | 按 ref 读取、≤ 1 MiB、仅 UTF-8；路径与 ref 前置校验；二进制 / 非 UTF-8 拒绝；读取记录审计不存正文 |
| 令牌失效与解绑 | P1 | 401 / 403 标「令牌失效」并统一提示；重填并测试成功恢复「已连接」；过期时间 < 7 天提示；二次确认解绑、删令牌、仓库 / 分支 / 提交快照只读可查，目录树与读文件入口置灰；重新绑定新 bindingId |
| 落盘与接口 | P0 | ENT-C12 ~ ENT-C15；对外 REST 接口；跨域只读接口（按 `repoBindingId` 引用元数据与按需文件内容） |

### Out of Scope

- 整库克隆、代码索引 / 向量检索、Webhook、定时任务与后台轮询、仓库写操作
- 令牌自动轮换 / 代续期、OAuth 授权流、多用户与团队权限
- 文件内容持久化（不落盘、不写会话制品与 AiCallRecord 正文）
- 分析会话与 AI 调用编排（workbench-core）、知识库（knowledge-base）、其他业务域
- 令牌加密方案本身（沿用 workbench-core AMB-005，本 spec 只接线）

## 用户故事摘要

| US ID | 标题 | 优先级 | AC 数量 |
|-------|------|--------|---------|
| US-017 | 绑定云效 / GitHub 仓库并保存访问令牌 | P0 | 6 |
| US-018 | 测试仓库连通性 | P0 | 5 |
| US-019 | 手动同步仓库元数据 | P0 | 6 |
| US-020 | 选择仓库与分支 | P0 | 4 |
| US-021 | 浏览提交与目录树 | P0 | 4 |
| US-022 | 按需读取单个文件内容 | P0 | 5 |
| US-023 | 处理令牌失效与撤销仓库绑定 | P1 | 6 |
| 合计 | — | — | 36 |

EARS 验收标准：AC-REQ-25 ~ AC-REQ-35（11 条，见 `requirements.md`）。

## AC 完整列表

- AC-017-1: GIVEN 在项目上下文页 WHEN 选择提供商、填写令牌与仓库标识、可选 API 域名并保存 THEN 创建绑定返回 bindingId，令牌加密存储，列表与详情只显示掩码，响应不返回完整令牌
- AC-017-2: GIVEN 必填缺失、仓库标识非法或 API 域名不是 `https://` WHEN 保存 THEN 拒绝并逐字段说明，不写入绑定或令牌
- AC-017-3: GIVEN 同项目同提供商 + 同仓库已绑定 WHEN 再次绑定 THEN 拒绝并提示重复，原绑定与令牌不变
- AC-017-4: GIVEN 绑定已存在 WHEN 更新令牌 THEN 只替换加密令牌与掩码，bindingId、已同步元数据与历史记录不变
- AC-017-5: GIVEN 填写绑定 WHEN 页面展示 THEN 说明只读元数据与按需文件内容、不克隆不建索引，并给出最小权限建议
- AC-017-6: GIVEN 已有若干绑定 WHEN 新增 THEN 不设硬上限（0..n），提示建议不超过 5 个
- AC-018-1: GIVEN 绑定已保存，或表单已填写当前值（未保存） WHEN 点击测试连接 THEN 发起一次只读请求，10s 内返回成功（含默认分支）或失败原因；未保存测试不落库、改字段即失效
- AC-018-2: GIVEN 令牌无效 / 过期 / 撤销 WHEN 测试 THEN 归类「鉴权失败」，提示重填，状态置「令牌失效」，响应与日志无令牌原文
- AC-018-3: GIVEN 域名不可达 / DNS 失败 / 拒绝 / 超时 WHEN 测试 THEN 归类「网络失败」并给可读原因；不写同步记录、不改元数据
- AC-018-4: GIVEN 令牌有效但无权访问 WHEN 测试 THEN 归类「权限不足」并提示所需只读权限，不误归为网络失败或令牌无效
- AC-018-5: GIVEN 测试返回 WHEN 查看绑定 THEN 展示测试时间、分类与原因；成功后状态「已连接」；不写会话、制品与 AiCallRecord
- AC-019-1: GIVEN 绑定已连接 WHEN 点击同步 THEN 拉取仓库信息 + 全部分支 + 最近 100 条提交写入快照，展示上次同步时间、耗时与结果
- AC-019-2: GIVEN 同绑定正在同步 WHEN 再次点击 THEN 返回「同步进行中」并阻止并发，不产生第二次记录
- AC-019-3: GIVEN 同步因鉴权 / 网络 / 限流失败 WHEN 结束 THEN 记录失败状态与原因，保留上次成功元数据与时间
- AC-019-4: GIVEN 打开项目上下文页 WHEN 查看绑定 THEN 展示上次同步时间与结果；从未同步展示「从未同步」
- AC-019-5: GIVEN 供应商返回限流（429 或 `X-RateLimit-Remaining: 0`） WHEN 结束 THEN 展示「供应商限流」与可重试时间（若提供），不自动重试、不轮询
- AC-019-6: GIVEN 同步完成 WHEN 检查保存内容 THEN 只有元数据基线；仓库与分支全量覆盖、提交保留 100 条；不含目录树与文件；不保存代码、不建索引、不自动触发
- AC-020-1: GIVEN 绑定已同步 WHEN 打开选择器 THEN 实时请求列表，可按名称 / 关键词检索并选择，默认绑定仓库
- AC-020-2: GIVEN 已选定仓库 WHEN 选择分支 THEN 实时展示分支列表（供应商分页与名称检索），默认默认分支；切换后提交与目录树随之切换
- AC-020-3: GIVEN 元数据未同步或为空 WHEN 打开选择器 THEN 空态并引导先同步，不返回错误页
- AC-020-4: GIVEN 令牌已失效 WHEN 打开选择器 THEN 提示「令牌失效」并提供重填入口，仍可看上次同步基线并标注上次同步时间
- AC-021-1: GIVEN 已选定仓库与分支 WHEN 查看提交 THEN 实时加载并按时间倒序展示 sha 短号、标题、作者、时间，支持翻页；无提交空态
- AC-021-2: GIVEN 已选定分支 WHEN 浏览目录树 THEN 按层级展示名称、类型、大小，可逐级展开；受供应商分页限制时按页加载并提示还有更多
- AC-021-3: GIVEN 供应商标记目录树截断 WHEN 展示 THEN 提示「目录树不完整，请逐级浏览」，不当作完整结果
- AC-021-4: GIVEN 在提交或目录树节点 WHEN 查看详情 THEN 展示仓库、分支 / ref、路径与文件大小；不写入 AiCallRecord 正文
- AC-022-1: GIVEN 选定单个文件与 ref WHEN 查看 THEN 通过供应商 API 读取并展示，不下载整库、不建索引
- AC-022-2: GIVEN 文件超过 1 MiB WHEN 读取 THEN 拒绝并显示大小与上限，不截断后冒充完整内容
- AC-022-3: GIVEN 文件为二进制或非合法 UTF-8 WHEN 读取 THEN 拒绝预览并说明不支持，不展示乱码
- AC-022-4: GIVEN 读取成功 WHEN 查看 THEN 展示路径、ref、大小、读取时间与内容；不写会话制品与 AiCallRecord；引用进分析计入 200,000 字符
- AC-022-5: GIVEN 路径含 `..`、绝对路径或非法 ref WHEN 读取 THEN 请求前拒绝并说明，不产生读取记录
- AC-023-1: GIVEN 同步 / 浏览 / 读文件返回 401 或 403 WHEN 识别 THEN 标「令牌失效」，项目上下文页与相关入口统一提示重填，不重复弹错
- AC-023-2: GIVEN 已标「令牌失效」 WHEN 重填有效令牌且测试成功 THEN 恢复「已连接」，bindingId、元数据与历史记录不变
- AC-023-3: GIVEN 响应提供令牌过期时间 WHEN 查看绑定 THEN 展示过期时间，剩余 < 7 天提示「即将过期」；无数据不推测
- AC-023-4: GIVEN 二次确认撤销 WHEN 完成 THEN 状态「已解绑」，删除加密令牌且不再请求；仓库 / 分支 / 提交快照保留标「已解绑」只读可查，目录树与读文件入口置灰
- AC-023-5: GIVEN 已解绑 WHEN 查看历史会话、调用记录或元数据 THEN 历史不变；元数据只读、不可同步或读文件；不参与任何 AI 调用
- AC-023-6: GIVEN 重新绑定同一仓库 WHEN 保存成功 THEN 生成新 bindingId 与新令牌，不复用旧令牌与旧同步记录

## 数据实体

- CodeRepoBinding（仓库绑定，ENT-C12）：bindingId、projectId、provider（yunxiao / github）、apiBaseUrl、orgId / owner、repoId / repoName、displayName、tokenCiphertext、tokenMasked、tokenExpiresAt（可空）、status（未验证 / 已连接 / 令牌失效 / 已解绑）、lastVerifiedAt、lastSyncAt、lastSyncStatus、createdAt、updatedAt；同项目同提供商 + 同仓库唯一
- RepoSyncRecord（同步记录，ENT-C13）：syncId、bindingId、startedAt、finishedAt、status（成功 / 失败）、repoCount、branchCount、commitCount、errorCategory（鉴权 / 网络 / 限流 / 其他）、errorMessage、createdAt；不保存令牌与供应商响应原文
- RepoMetadataSnapshot（元数据快照，ENT-C14）：snapshotId、bindingId、repoId、kind（仓库 / 分支 / 提交 / 目录树）、ref、payload（名称、ID、sha、标题、作者、时间、路径、文件大小）、fetchedAt、truncated；目录树是否入快照取决于 AMB-026
- RepoFileReadRecord（文件读取记录，ENT-C15）：readId、bindingId、repoId、ref、filePath、byteSize、encoding（text / base64）、status（成功 / 拒绝）、rejectReason（超限 / 二进制或非 UTF-8 / 非法路径）、fetchedAt；不保存正文

## 系统集成点

| 集成目标 | 方向 | 用途 |
|---------|------|------|
| ProjectContext / projectId（workbench-core） | 读取 | 绑定归属 `projectId`；只按 ID 引用，不跨域读写项目表 |
| 项目上下文页与 AppShell（workbench-core） | 复用 | 仓库集成面板挂在项目上下文页内；侧边栏「基座管理」分组与设计 token 不变 |
| 凭证加密与掩码（workbench-core，AMB-005） | 复用 | 仓库令牌同级加密与掩码回显；加密算法不重定义 |
| 单用户登录会话（workbench-core） | 复用 | 仓库绑定接口受既有登录态保护，不新建账号体系 |
| 文本输入上限 200,000 字符（workbench-core，AMB-010） | 引用 | 文件内容被引用进分析时按同一常量计入，数值不重复定义 |
| 其他业务域 / 未来域 | 只读接口 | 按 `repoBindingId` 读取元数据与按需文件内容；不得持有令牌或直连供应商 |
| 云效 Codeup OpenAPI | 出站 HTTPS | 鉴权 `x-yunxiao-token`；仓库 / 分支 / 提交 / 目录树 / 单文件；响应头分页 `x-total` / `x-page` |
| GitHub REST API | 出站 HTTPS | 鉴权 `Authorization: Bearer`；`/repos/{owner}/{repo}`、`/branches`、`/commits`、`/git/trees/{sha}`、`/contents/{path}`；`X-RateLimit-*` |

## 关键约束

- 令牌：服务端加密、口令来自环境变量、只回显掩码；完整令牌不得出现在接口响应、日志、同步记录、读取记录与 AiCallRecord；仓库令牌使用独立密钥 `AW_REPO_TOKEN_KEY`，不与模型密钥共用（AMB-029 已确认）
- 只读最小权限：界面提示 GitHub fine-grained PAT「Contents: read + Metadata: read」、云效令牌仅代码库读取；系统不发起任何写操作
- 同步：手动触发、同绑定禁止并发、失败保留上次成功元数据与时间、不做定时与后台轮询；每次拉仓库信息 + 全部分支 + 最近 100 条提交作为**基线快照**（不含目录树与文件内容）
- 新鲜度：仓库 / 分支 / 提交列表与目录树**实时读取**（供应商分页），不读快照；快照只作基线对照与令牌失效时的 last-known 展示（AMB-026 / AMB-027 已确认）
- 读文件：单文件 ≤ 1 MiB（1,048,576 字节）、仅 UTF-8 文本；超限 / 二进制 / 非 UTF-8 拒绝并说明；路径含 `..`、绝对路径、非法 ref 在请求前拒绝；内容不落盘、不写会话制品与 AiCallRecord
- 目录树：逐级实时展开；供应商标记截断必须提示「目录树不完整」
- 测试连接：一次只读请求、10s 超时；四类结果不得互相误归类；保存前可用表单当前值测试且不落库、改字段即失效（AMB-028 已确认，与 core UXAMB-006 一致）；测试不写会话、制品与 AiCallRecord
- 仓库信息单一事实来源：绑定列表为准；core 项目上下文页「仓库地址」文本框降级为自由备注并标注来源（AMB-030 已确认）
- 解绑：二次确认；删除加密令牌、此后不再发请求；仓库 / 分支 / 提交快照保留标「已解绑」只读可查，目录树与读文件入口置灰；历史会话 / 制品 / AiCallRecord 不变；重新绑定生成新 bindingId（AMB-031 已确认）
- 跨 spec 依赖不得改写 core 契约：登录态、凭证加密、错误体与分页约定、200,000 字符常量
- 外部事实：云效限流数值、云效单文件上限、GitHub PAT 过期响应头、地域版域名细节均未核实，实现不得假设具体数值（见 `design.md`「外部接口核实」）
- AMB-026 ~ AMB-031 已于 2026-11-18 10:44:10 全部确认（answers.md：「全按建议」）

## 状态

pending-confirmation（AMB-026 ~ AMB-031 已确认；阶段本身待用户确认）
