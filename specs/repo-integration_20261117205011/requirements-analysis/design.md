# Requirements Analysis — Design

## 需求类型

➕ 功能新增 — 本文件包含商业目标、优先级矩阵、核心决策、迁入假设与外部接口核实；不含用户研究与竞品分析（intake 已判定跳过）。

## 商业目标

- BG-06：打通仓库接入闭环（承接自 workbench-core，编号保留；原文未随交接文件保留量化口径，以下为承接口径，待用户复核）——项目上下文中的仓库元数据与按需文件内容可直接被查看与引用，不必手工抄写仓库地址。可量化口径：7 个用户故事共 36 条 AC 与 11 条 EARS 全部通过；已同步数据的项目在浏览提交 / 目录树 / 单文件时 100% 不依赖手工抄写的路径；接口响应与日志中完整令牌出现次数为 0。

## 用户研究综合（跳过）

本 spec 是同一产品规划内的功能新增（intake 判定），不重跑市场研究。迁入的假设原文：

- **H5（修订版）**：测试工程师能接受「不克隆、不建索引、只按需读单文件」的代码上下文能力——因为它避免了本地仓库与索引的维护成本；风险是跨文件理解能力弱于带索引方案。（2026-11-17 20:33:31 修订：原「不自动克隆仓库、不解析代码」改为「不整库克隆、不建代码索引，仅按需读取单文件原文」；未验证。）
- **H7**：仓库元数据（分支、提交、目录树）+ 按需单文件内容足以支撑首版的代码上下文引用，不需要整库克隆或代码索引。（未验证，需真实使用数据；本期以「浏览路径与读取成功率」作为替代证据。）

待验证问题（不编造数字或引语）：真实项目中平均绑定几个仓库、单次同步的分支 / 提交规模、用户单次浏览平均读取几个文件——均无原始数据，留待上线后从 RepoSyncRecord 与 RepoFileReadRecord 统计。

## 竞品分析（跳过）

功能新增，intake 判定跳过 `competitor-analysis`；本次未做竞品联网核实，不列对比结论。若后续需要定位差异化，可将「只读最小权限 + 元数据按需拉取 + 不落盘」作为候选对比维度，标注「待验证」。

## 优先级矩阵

### Must Have（P0）

| 功能 | 理由 |
|------|------|
| US-017 绑定仓库并保存访问令牌 | 闭环入口；没有绑定就没有后续测试、同步与浏览；令牌安全（加密、掩码、不落日志）是安全底线（BR-C21） |
| US-018 测试仓库连通性 | 在同步前把鉴权 / 网络 / 权限问题分辨清楚，避免用户把失败归因错；四类结果是后续错误分类的基线（BR-C22） |
| US-019 手动同步仓库元数据 | 分支与提交数据的唯一来源；并发互斥、失败保留旧数据、限流提示都在此收口（BR-C23） |
| US-020 选择仓库与分支 | 把「同步到的数据」变成「可浏览的上下文」；未同步空态与令牌失效缓存是可用性底线（BR-C24） |
| US-021 浏览提交与目录树 | 定位变更与文件路径的主路径；截断提示防止把不完整结果当完整（AC-021-3） |
| US-022 按需读取单个文件 | 闭环价值所在；1 MiB 上限、UTF-8 限制、路径穿越校验与不落盘在此收口（BR-C25） |

### Should Have（P1）

| 功能 | 理由 |
|------|------|
| US-023 令牌失效处理与撤销绑定 | 失效提示防止长期静默失败；解绑语义（删除令牌、元数据只读、重新绑定新编号）必须在首版定死，事后改会污染历史数据（BR-C26 / BR-C27） |

### Could Have（本期不做）

| 功能 | 理由 |
|------|------|
| 同步历史与耗时趋势 | AC 只要求展示上次同步时间与耗时；趋势图价值有限，非闭环必需 |
| 仓库 / 分支选择器记忆上次选择 | 交互优化，不影响 AC；可由交互设计决定是否作为前端本地状态 |
| 文件内容内搜索 / 行号定位 | 读文件 AC 只要求展示内容；扩展价值待验证 |

### Won't Have（明确排除）

| 功能 | 理由 |
|------|------|
| 整库克隆、代码索引 / 向量检索 | 决策 15（只做元数据 + 按需读文件）；用户 20:33:31 与 20:46:07 已定 |
| 仓库写操作（建分支 / 提交 / 合并请求 / 评论） | AC-REQ-35 明确禁止；只读最小权限 |
| Webhook、定时同步、后台轮询 | AC-REQ-27 / AC-REQ-28 明确禁止；手动同步是已确认口径 |
| 令牌自动轮换 / 代续期 / OAuth 授权流 | AMB-021 A 已确认；OAuth 属账号体系，超出本期 |
| 多用户、团队权限、跨项目共享绑定 | 沿用 workbench-core 单用户登录边界 |
| 文件内容持久化 / 会话制品 / 写 AiCallRecord 正文 | AC-REQ-34 明确禁止；内容只在请求与展示期间存在 |
| 云效 / GitHub 之外的供应商 | 本期只支持两家；抽象预留但不承诺 |

## 核心决策

### 决策 15：只做元数据 + 按需读文件（承接）
- **选择**：通过供应商 API 读取仓库、分支、提交、目录树元数据，并按 ref 读取单个文件内容；不整库克隆、不建立代码索引 / 向量库。
- **理由**：用户 2026-11-17 20:33:31 四项全按建议默认 A；避免本地仓库与索引的维护成本，数据边界更小。
- **权衡**：跨文件理解与全局检索能力弱；单文件受 1 MiB 与 UTF-8 限制，超大文件需用户改用片段。

### 决策 16：仓库令牌与模型密钥同级管理（承接）
- **选择**：仓库访问令牌与模型密钥采用同一安全等级——服务端加密存储、口令来自环境变量、接口只回显掩码、令牌不落日志；本 spec 复用 workbench-core AMB-005 方案，不重新定义加密算法。
- **理由**：两处都是外部系统凭据，混用低标准会形成短板；统一实现便于审查。
- **权衡**：令牌与模型密钥是否共用同一密钥由 AMB-029 决定（建议不共用）；若共用，轮换会同时影响两类凭据。

### 决策 17：手动同步、失败不清空旧数据（承接）
- **选择**：同步只由用户点击触发；同一绑定禁止并发；失败时记录失败状态与可读原因，保留上次成功元数据与时间；不做定时任务与后台轮询。
- **理由**：限流风险可控，行为可预期；用户能明确知道「当前看到的是哪次同步的结果」。
- **权衡**：数据可能滞后，需以「上次同步时间」显式提示；用户需自行决定何时刷新。

### 决策 18：扩展 workbench-core 线框与架构，不完整重跑（本 spec 新增，用户已定）
- **选择**：交互层在 core 的项目上下文页（US-008）内新增绑定 / 测试 / 同步 / 浏览 / 读文件 / 解绑面板；技术层沿用 FastAPI + Pydantic + SQLAlchemy 2.x + Alembic + MySQL 8.4 / SQLite 与 React + Vite + TanStack Query；错误结构与分页约定沿用 core，不另起一套。
- **理由**：用户 2026-11-17 21:00 拆分归属决策与本次委派约束均要求扩展而非重跑；重复建设会让同一页面出现两套交互与错误语义。
- **权衡**：仓库集成面板受既有页面信息密度约束，可能需要折叠 / 分区；core 交互稿若返工，本 spec 的面板需同步调整（跨 spec 依赖）。

### 决策 19：编号承接、不重排，本 spec 新增条目自建编号（本 spec 新增）
- **选择**：US-017 ~ US-023、AC-017-1 ~ AC-023-6、AC-REQ-25 ~ AC-REQ-35、AMB-020 ~ AMB-025、ENT-C12 ~ ENT-C15、BR-C21 ~ BR-C27、BP-C9 ~ BP-C11、TERM-C14 ~ TERM-C16 保持原编号；本 spec 新识别歧义从 AMB-026 起编，并在条目里注明来源（intake IQ-x）。
- **理由**：跨 spec 追溯与历史会话 / 文档引用不失效；避免同一编号在两个 spec 指向不同定义。
- **权衡**：本 spec 的编号不从 1 开始，阅读时需要 handoff 对照。

### 决策 20：未核实的外部事实不编造，统一留「待技术方案」（本 spec 新增）
- **选择**：能联网核实的（GitHub 官方 OpenAPI / 文档、云效官方 MCP server 源码）本轮已核实并记录地址；核实不到的（云效限流数值、云效单文件上限、GitHub PAT 过期响应头、地域版域名细节）保留「待技术方案」，实现不得假设具体数值。
- **理由**：限流与大小上限直接影响拒绝逻辑与用户提示，猜错会造成静默失败或错误拒绝。
- **权衡**：技术方案阶段需要补研究；在拿到数值前，限流与超限行为只按供应商实际响应处理。

## 迁入假设与待技术方案项

### 假设

- **H5（修订版）**：用户接受「不克隆、不建索引、只按需读单文件」的能力边界（未验证）。
- **H7**：元数据 + 按需单文件内容足以支撑首版代码上下文引用（未验证）。

### 外部接口核实（2026-11-18，本轮实际访问）

> 只记录本轮真正取到的内容；未取到的一律列入「未核实」。

已核实：

1. GitHub REST OpenAPI 描述（`https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json`，14,275,550 字节）：`components.headers` 只包含 `link`、`content-type`、`x-common-marker-version`、`x-rate-limit-limit`、`x-rate-limit-remaining`、`x-rate-limit-reset`、`location`；**没有**任何令牌过期时间响应头定义。限流响应头为 `X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset`。
2. GitHub 限流文档（`https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api`）：PAT 5,000 请求/小时、未认证 60 请求/小时、超限返回 429，响应含上述三个限流响应头。
3. GitHub fine-grained PAT 权限表（`https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens`）：`GET /repos/{owner}/{repo}/contents/{path}`、`GET /repos/{owner}/{repo}/git/trees/{tree_sha}`、`GET /repos/{owner}/{repo}/commits` 归入 **Contents** 权限且均为 `read`；`GET /repos/{owner}/{repo}/commits/{ref}/status` 归入 **Commit statuses** 且为 `read`。→ 只读最小权限建议「Contents: read + Metadata: read」有官方依据；分支列表端点自身的权限行本轮未单独定位（见未核实）。
4. GitHub PAT 管理文档（`https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens`）：过期时间由用户在创建令牌时设置；GitHub 会自动移除一年未使用的 PAT；文档未提供「通过 REST 响应读取 PAT 过期时间」的说明。
5. GitHub App installation token 文档（`https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app`）：installation access token 1 小时后过期，创建响应体返回过期时间；本轮访问的页面未出现 `github-authentication-token-expiration` 头名。
6. 云效官方 MCP server 源码（`https://raw.githubusercontent.com/aliyun/alibabacloud-devops-mcp-server/master/...`）：
   - `common/utils.ts`：默认域名 `https://openapi-rdc.aliyuncs.com`；鉴权头 `x-yunxiao-token`；region 判定（显式 `YUNXIAO_EDITION` 或域名不含 `openapi-rdc.aliyuncs.com`）；源码注释明确「需要读取响应头（如分页 x-total / x-page）的场景应使用它（request 封装）」；日志对 `x-yunxiao-token` / `authorization` 自动脱敏。
   - `common/errors.ts`：401（Authentication failed）、403（Insufficient permissions）、429（Rate limit exceeded，携带 `reset_at`）三类错误对象。
   - `operations/codeup/repositories.ts` / `branches.ts` / `commits.ts` / `files.ts`：中心站路径前缀 `/oapi/v1/codeup/organizations/{orgId}/repositories/...`，地域版为 `/oapi/v1/codeup/repositories/...`（不带 organizations 段）；提交列表支持 `page` / `perPage`，提交对象含 `id`、`shortId`、`title`、`authorName`、`authoredDate` 等字段；文件内容接口响应含 `content` / `size` / `encoding`，`encoding` 可为 `text` 或 `base64`；目录树接口 `/files/tree` 支持 `path` / `ref` / `type`。
7. 云效 GetFileBlobs 帮助页（`https://help.aliyun.com/zh/yunxiao/developer-reference/api-codeup-2021-02-22-getfileblobs`）：页面可访问但正文由脚本渲染，未取到文件大小上限等正文内容。

未核实（保留「待技术方案」，实现不得假设数值）：

1. 云效官方速率限制数值与配额维度（已查上述帮助页与 `https://help.aliyun.com/zh/yunxiao/developer-reference/limits`，后者返回 404 错误页）。
2. 云效单文件大小上限（帮助页正文未取到；源码未做大小限制）。
3. GitHub PAT 过期时间的可编程获取方式（OpenAPI 无该响应头；PAT 管理文档只说明在创建时设置与一年未用自动移除）。
4. GitHub `GET /repos/{owner}/{repo}/branches`（分支列表）在 fine-grained 权限表中的精确归属行（本轮只确认了 `branches/{branch}/protection` 系列与 Contents / Commit statuses 分组）。
5. 云效地域版实例的具体域名形态与域名清单（源码只给出「非中心站域名即 region」的判定方式与路径差异）。
6. 五个适配器接口契约、错误分类映射、分页游标与限流读取实现（原 TASK-RA-050）。
7. 元数据快照表结构与保留策略（含 `truncated` 表示）、并发同步互斥实现。
8. 仓库令牌加密密钥的最终变量名与轮换方式（AMB-029 待确认，建议独立密钥）。

### 决策 21：浏览实时读取、同步只存基线（AMB-026 / AMB-027 已确认）
- **选择**：仓库 / 分支 / 提交列表与目录树在浏览时**实时读取**（按供应商分页）；同步只拉仓库信息、全部分支与最近 100 条提交作为基线快照，不含目录树与文件内容。快照用于「对照过哪个提交」的基线证据与令牌失效时的 last-known 展示。
- **理由**：用户 2026-11-18 10:44:10 明确「保持与目录树同一新鲜度口径，否则用户会误以为看到的是当前状态」；两套数据源混用会产生时效不一致。
- **权衡**：浏览受供应商限流与网络影响更大，需要清晰的加载态与错误态；令牌失效时无法浏览实时列表，只能回看上次同步基线。

### 决策 22：「仓库地址」单一事实来源（AMB-030 已确认）
- **选择**：绑定列表是仓库信息的唯一来源；workbench-core 项目上下文页的「仓库地址」文本框降级为自由备注，并标注「人工备注，实际拉取以绑定列表为准」；原「两者并存、互不改写」方案作废。
- **理由**：用户 2026-11-18 10:44:10 拍板「单一事实来源」；避免同一信息两处维护、用户误把备注当实际绑定。
- **权衡**：core 页面文案与字段语义需同步调整（跨 spec 协作）；既有「仓库地址」文本保留但不参与任何同步或读文件逻辑。

## 已确认的新增口径（AMB-026 ~ AMB-031，2026-11-18 10:44:10）

| AMB | 结论 |
|-----|------|
| AMB-026 | 目录树浏览时实时逐级拉取，同步不拉全树 |
| AMB-027 | 仓库 / 分支 / 提交列表实时读取，快照仅作基线证据与令牌失效回看 |
| AMB-028 | 保存前可用表单当前值测试且不落库，改字段即失效（与 core UXAMB-006 一致） |
| AMB-029 | 仓库令牌独立密钥 `AW_REPO_TOKEN_KEY`，不与模型密钥共用 |
| AMB-030 | 绑定列表为单一事实来源，「仓库地址」降级为自由备注并标注来源 |
| AMB-031 | 解绑后仓库 / 分支 / 提交快照只读可查，目录树与读文件入口置灰 |
