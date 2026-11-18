# tech-arch · 技术选型确认记录

> 状态：**原确认有效**（2026-11-17 19:49:04）。用户原话：「STK-001 A，STK-002 A，STK-003 A，STK-004 A」，完整记录见 `technical-design/answers.md`。
> 2026-11-17 部署形态变更返工：原 STK-003 / STK-004 的结论被新决策取代；本轮新增的可感知取舍见文末「返工待确认（2026-11-17）」，共 5 项，均附默认值与建议。

## STK-001：技术栈方案 — ✅ 已确认 A

用户原话：「STK-001 A」

- **A（采用）**：Python 3.12+ / FastAPI 0.163 + SQLAlchemy 2.1 / Alembic + SQLite（WAL）+ OpenAI 3.52 / Anthropic 2.9 官方 SDK + cryptography；
  前端 React 19.3 + TypeScript 7.0 + Vite 8.3 + React Router 8.5 + TanStack Query；CSS 变量 + Radix Primitives；单进程 Uvicorn 同源托管。
- 未采用：B（Node.js 24 + Fastify/NestJS + Drizzle）、C（Go + Chi）。
- 选 A 后 `.aw/config.json` 的 pytest 测试命令保持不变。

## STK-002：前端框架 — ✅ 已确认 A

用户原话：「STK-002 A」

- **A（采用）**：React 19 + Vite + TypeScript。
- 未采用：B（Vue 3.5）、C（Svelte 5）。

## STK-003：数据库与环境 — ✅ 已确认 A

用户原话：「STK-003 A」

- **A（采用）**：SQLite（WAL）单文件，位于 `AW_DATA_DIR`；无额外服务。
- 未采用：B（PostgreSQL）。

## STK-004：网络绑定 — ✅ 已确认 A

用户原话：「STK-004 A」

- **A（采用）**：默认 `127.0.0.1:8000`，仅本机访问；非本地绑定需 `AW_ALLOW_REMOTE=1` 并告警。
- 未采用：B（默认绑定 `0.0.0.0`）。

## 默认结论（用户未反对，采用默认）

以下 5 项在本次确认中未被用户提出异议，按默认定稿，已写入 ADR-010 ~ ADR-014：

1. **调用记录正文**：不存完整请求正文；存提示摘要（sha256 + 前 200 字符 + 字数）与响应全文 `result_text`；随会话永久保留、级联删除。
2. **结果文本形态**：存 AiCallRecord 字段（`result_text` + `result_format`，本期 `text`），不落制品。
3. **状态审计**：SessionEvent `status_change` payload 记录 `{from,to,actor,at,reason}`；`actor` = `local-user` / `system`。
4. **制品预览/下载**：元数据 + `content` 接口（inline/download，`max_bytes` 预览上限 256KB，下载完整 ≤10MB），服务端映射 Content-Type + `nosniff`。
5. **导出/分享**：本期不做跨会话导出与只读分享，记入扩展计划。

## 返工项（2026-11-17 部署形态变更）— ✅ 已确认

> 2026-11-17 20:09:45 用户拍板：OQ-ARCH-01/02/04/05 全部按建议默认 A，已写入 `answers.md`；OQ-ARCH-03 按 B 处理（interaction-design 已回补登录页线框并确认）。ADR-015 ~ ADR-028 已据此标为已确认。

### OQ-ARCH-01：MySQL 版本与字符集 — ✅ 已确认 A
- **选项**：A（默认）MySQL 8.4 LTS，`utf8mb4` / `utf8mb4_0900_ai_ci`，兼容 8.0+；B 只支持 8.0 系列；C 跟随 9.x innovation。
- **建议**：A。8.4 是当前 LTS（镜像 `mysql:8.4.13`），9.x innovation 生命周期短，不适合长期自托管。
- **影响**：`docker-compose.yml` 的镜像标签、`.env.example` 的最低版本说明；若部署方已有 8.0 实例，需确认字符集为 utf8mb4 后再接。

### OQ-ARCH-02：迁移执行时机 — ✅ 已确认 A
- **选项**：A（默认）compose 启动脚本显式执行 `alembic upgrade head`，应用只校验版本；B 应用启动自动迁移；C 完全手动执行，容器不碰 schema。
- **建议**：A。升级只多一步（已封装进镜像入口），失败了能看到明确报错；自动迁移在多副本与回滚场景不可控。
- **影响**：部署文档与升级步骤；外接 MySQL 的账号是否需要 DDL 权限（A/B 需要，C 可由 DBA 执行）。

### OQ-ARCH-03：登录页的 UI 归属 — ✅ 已按 B 解决
- **背景**：interaction-design 于 2026-11-17 19:36 确认，其 `requirements.md` 明确「本期单用户、无登录」，没有登录页线框与组件；US-011 在 19:52 之后才加入。
- **选项**：A（默认）tech-design 按现有 Design Tokens 直接出登录页（单卡片、口令输入、统一错误、锁定提示），不回填 interaction-design；B 先回补 interaction-design 的登录页线框，再进 tech-design；C 用最简静态页，不做视觉打磨（不推荐，登录页是 US-011 的唯一用户界面）。
- **建议**：A。登录页只有一个表单，token 全部复用现有设计系统；代价是没有独立线框稿可供逐项对照。
- **影响**：tech-design 的组件树与 tech-tasks 的前端任务；若选 B，本 spec 需回退一个阶段并由编排者重新记录确认。

### OQ-ARCH-04：反向代理与客户端 IP — ✅ 已确认 A
- **选项**：A（默认）默认不信任 `X-Forwarded-For`，取直连对端；仅 `AW_TRUST_PROXY=1` 时取首跳；B 始终信任 XFF；C 按 `AW_TRUSTED_PROXY_CIDRS` 白名单取最右可信跳。
- **建议**：A。compose 默认由 uvicorn 直连，不需要代理；部署在 nginx 之后且忘记开启时，所有用户共享一个 IP，连续失败会互相误锁，因此 `.env.example` 与文档必须显式提示。
- **影响**：AC-011-4 的「同一来源 IP」判定、日志中的来源识别、误锁风险。

### OQ-ARCH-05：TLS 与备份是否随 compose 交付 — ✅ 已确认 A
- **选项**：A（默认）compose 不含 TLS，文档要求反代（Caddy/nginx）并配置 `AW_PUBLIC_ORIGIN`、`AW_COOKIE_SECURE=auto`；提供 `scripts/backup.sh`（mysqldump + 制品打包）与恢复步骤；B compose 内置 Caddy 自动证书；C 备份只写文档、不提供脚本。
- **建议**：A。内置 Caddy 会绑定域名与证书申请，超出本期范围；备份脚本成本低且直接支撑 ADR-019 的恢复演练。
- **影响**：远程部署是否「开箱即用 HTTPS」；验收时是否执行一次恢复演练。

## 知识库轮次（2026-11-17，US-012 ~ US-016）— ✅ 已确认

> 2026-11-17 20:27:18 用户拍板：OQ-ARCH-06 ~ OQ-ARCH-09 全部按建议默认 A，已写入 `technical-design/answers.md`；ADR-029 ~ ADR-040 已据此标为已确认。

### OQ-ARCH-06：解析护栏默认值（条目数 / JSON 深度 / 邻居数）— ✅ 已确认 A

- **背景**：需求只给了字节与文件数上限（`index.json` ≤20MB、其他 ≤10MB、单次 ≤50 个、单库 ≤100MB），没有条目数与嵌套深度上限。20MB JSON 若由极小条目组成可达十万级，单事务写库与后续渲染都会失控。
- **选项**：A（默认）单库 ≤20,000 条、JSON 深度 ≤32、单条邻居 ≤200，超限整包拒绝并报实测值；B 单库 ≤50,000 条、深度 ≤64（更宽松，导入更慢、内存峰值更高）；C 不设条目/深度上限，只按字节限制（实现最简单，但存在解析与写库的长尾）。
- **结论**：A。真实本体知识库通常数百到数千条，20,000 条留足余量；深度 32 足以容纳 `entries[].neighbors[]` 这类结构，同时挡住恶意嵌套；邻居 200 条已超过任何可读详情页。
- **影响**：超过 20,000 条的知识库需拆分或调整 `AW_KB_MAX_ENTRIES`；调大后需同步压测导入耗时与内存。

### OQ-ARCH-07：检索实现（便携 LIKE vs 方言全文索引）— ✅ 已确认 A

- **背景**：AC-013-3 只要求「按编号、标题、摘要或正文关键字检索」，没有性能指标。MySQL FULLTEXT（ngram）与 SQLite FTS5 是两套实现，中文分词行为也不同。
- **选项**：A（默认）统一 `LIKE '%q%'`（转义通配符），默认只搜当前版本，单库 ≤100MB / 单用户规模下可接受；B MySQL 建 FULLTEXT + ngram、SQLite 建 FTS5，检索更快但两套 DDL/排序/分词行为需分别验证；C 引入外部搜索引擎（本期明显过度）。
- **结论**：A。当前数据量与单用户并发下全表扫描是毫秒到百毫秒级；避免两套方言实现漂移，也避免建索引拖慢导入。检索变慢时按「扩展计划」升级到 B，接口与数据模型不变。
- **影响**：大库（接近 100MB 正文）上的关键字检索延迟；若后续要求「检索结果高亮/相关度排序」，A 只能做简单排序，需升级。

### OQ-ARCH-08：「已被新版本取代」的条目是否阻止注入 — ✅ 已确认 A

- **背景**：AC-014-4 已明确「已被新版本取代」属于发起调用前阻止的情形；AC-015-4 末尾写明「条目已删除或已失效时按 AC-014-4 处理」。二者一致，仅是「失效条目」与「新鲜度/冲突提示」两类不同对象。
- **选项**：A（默认）按 AC-014-4：选中条目属于已被取代版本 → 阻止使用该条目并提示具体编号，其余有效条目不受影响，浏览与查看不受限；B 允许注入旧版本条目并标注「来自 vN（已被取代）」；C 允许注入但默认不展示旧版本条目。
- **结论**：A。直接引用 AC-014-4，避免用户把旧结论当现行结论。
- **影响**：注入选择器只列当前版本条目；失效条目在调用前被剔除并提示，不需要回改需求。

### OQ-ARCH-09：删除知识库的范围（全部版本 vs 仅当前版本）— ✅ 已确认 A

- **背景**：AC-016-1 说「删除知识库、其条目索引与已存文件一并删除」，但知识库按版本存多行；需求没有单独的「删除某个版本」入口。
- **选项**：A（默认）删除该项目同名逻辑知识库的**全部版本**与文件，历史会话与 AiCallRecord 不变；B 只删当前版本，旧版本自动升为当前版本（需处理「删除最新版后旧版复活」）；C 只删当前版本且旧版本一并标记为不可用（保留文件但不展示，语义最绕）。
- **结论**：A。用户心智中「知识库」是名称而非版本号；B 会让旧结论无声复活，C 产生孤儿数据。二次确认文案需写明「将删除该名称下全部 N 个版本」。
- **影响**：删除确认弹窗文案、历史版本是否可单独清理；若后续要「只删某一版」，作为新需求加接口。

---

# tech-design · 取舍确认（2026-11-18）

> 以下 5 项为本阶段设计中的可感知取舍。**2026-11-18 10:44:10 用户原话「全按建议」，全部按 A 定稿**（记录见 `technical-design/answers.md` 同节）；产物已与结论一致。
> 不涉及 ADR-041 冻结签名的名称与语义（`sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete(session_id, model_id, prepared, *, temperature, max_tokens)` 均原样保留，只展开参数类型）。

## OQ-TD-01：对外 ID 形态

- **背景**：ADR-016 定了自增 `BIGINT` 主键（SQLite 用 `INTEGER` 变体），但没有规定 API 与进程内签名对外暴露数字还是字符串。
- **选项**：A（默认）JSON number + 进程内 `int`；B 对外不透明字符串（如 `ses_...`），服务端维护映射；C 全量 UUID 主键（推翻 ADR-016 的自增约定）。
- **建议**：A。单用户系统无枚举攻击面；与 ADR-016 一致；后续域拼路径/日志更简单。
- **结论**：✅ 已确认 A（2026-11-18 10:44:10「全按建议」）：主键自增整数 `int`；API 返回 JSON number；冻结签名参数保持 `int`。
- **影响**：前端路由 `/sessions/:id`、游标编码、所有进程内签名参数类型；当前产物已按 A 写。

## OQ-TD-02：不为项目 / 提供商 / 模型提供删除接口

- **背景**：AC-008 / AC-003 / AC-004 只要求创建、编辑、启停与「停用后不可选」，未要求删除；删除会让历史会话与调用记录失去归属。
- **选项**：A（默认）不提供删除，提供商/模型只停用（`enabled=false`），项目只编辑；外键 `ON DELETE RESTRICT`；B 提供删除，被引用时拒绝（409）；C 提供删除并级联清理相关会话（风险高）。
- **建议**：A。与 AMB-009「只删整个会话」一致，避免「删项目导致历史分析消失」。
- **结论**：✅ 已确认 A（2026-11-18 10:44:10「全按建议」）：本期不提供项目 / 提供商 / 模型删除，只停用（`enabled=false`）；外键 `ON DELETE RESTRICT`。
- **影响**：前端不出现删除按钮；若后续确需清理，新增软删除字段与新需求。

## OQ-TD-03：AiCallRecord 冗余模型/提供商快照列

- **背景**：ADR-010 要求「模型快照字段」；模型显示名可能被编辑，提供商可能停用或改名。
- **选项**：A（默认）在 `ai_call_record` 冗余 `model_name_snapshot` / `display_name_snapshot` / `provider_name_snapshot` / `protocol_snapshot` 四列；B 只存外键，查询时 JOIN 现值；C 存一个 JSON 快照列。
- **建议**：A。历史记录显示调用当时的名称，查询无需 JOIN；四列体积可忽略。
- **结论**：✅ 已确认 A（2026-11-18 10:44:10「全按建议」）：冗余提供商名与模型名快照，历史记录不随改名变化。
- **影响**：写入时多复制 4 个字段；后续域做调用统计时以快照为准。

## OQ-TD-04：制品存储名改用 uuid（偏离 ADR-006 示例 `<artifactId>.<ext>`）

- **背景**：ADR-006 的结构示例是 `sessions/<sessionId>/<artifactId>.<ext>`；但 artifactId 由数据库自增生成，先拿 ID 再写文件会把文件写入拉进 DB 事务，或需要两阶段更新。
- **选项**：A（默认）存储名 `<uuid4hex>.<ext>`，与主键解耦，先落临时文件再原子移动；B 严格按 ADR-006 用 artifactId（需在事务内 flush 出 ID，再写文件）；C 用内容哈希命名（同内容去重，但同名制品语义复杂）。
- **建议**：A。服务端生成、隔离目录、原名只存 DB 的语义不变，只改存储名格式。
- **结论**：✅ 已确认 A（2026-11-18 10:44:10「全按建议」）：磁盘存储名用 uuid（`<uuid4hex>.<ext>`），原始文件名只存数据库。
- **影响**：备份/排障时无法从文件名反推 artifactId，需查 DB；`relative_path` 仍在 `sessions/<sessionId>/` 下。

## OQ-TD-05：上游失败的 HTTP 映射与 `timeout` 独立状态

- **背景**：AC-005-2 只要求「可读错误」，AC-010-1 展示「状态」，ADR-010 的状态含 `running/success/failed/timeout`；未规定 HTTP 状态码。
- **选项**：A（默认）鉴权/限流/5xx/网络不可达/参数错误统一 502（`ai_*` 码），120s 无响应 504（`ai_timeout`），记录 `status=timeout`；B 全部 502、只用 `error_code` 区分；C 把上游鉴权失败映射 401、限流映射 429（会与登录态语义混淆）。
- **建议**：A。前端可按 502/504 区分「上游失败」与「超时」，401 保留给本站登录态。
- **结论**：✅ 已确认 A（2026-11-18 10:44:10「全按建议」）：上游 5xx → 502，超时 → 504；超时记录 `status=timeout`。
- **影响**：前端错误提示分支、调用记录状态徽标；当前产物已按 A 写。

---

# tech-tasks · 已确认项（2026-11-18）

> 以下 4 项已于 2026-11-18 由用户拍板（原话「TT-01 A 建 GitHub 公开仓库并 push 走 Actions，配置好 .gitignore，其他按建议」，记录见 `technical-design/answers.md`）。`tasks.md`、`requirements.md`、`docs/context.md` 已按结论更新；不改动任何 ADR 与已确认接口口径。

## OQ-TT-01：CI 平台

- **背景**：仓库无 remote、无现有 CI（`.aw/install.json` 的 `ci: null`），派单要求新增「pytest job + MySQL 第二 job」。
- **选项**：A（默认）GitHub Actions，新增 `.github/workflows/ci.yml`；B 其他平台（GitLab CI / 云效流水线），任务文件名随平台改；C 本期不加 CI，只在本地跑 `aw verify` 与 `AW_TEST_DATABASE_URL`。
- **建议**：A。工作流文件与 `python3 .aw/aw.py ci` 的语义最接近，迁移成本最低；仓库后续接 GitHub 时零改动。
- **结论**：✅ 已确认 A（2026-11-18，用户原话「TT-01 A 建 GitHub 公开仓库并 push 走 Actions，配置好 .gitignore」）：仓库建成 GitHub 公开仓库并 push，CI 用 GitHub Actions，文件 `.github/workflows/ci.yml`；`.gitignore` 覆盖 `.env`、`data/`、`web/node_modules/`、`web/dist/`、`*.db`、缓存与测试产物。
- **影响**：TASK-TD-018 按 GitHub Actions 写；TASK-TD-001 负责补齐 `.gitignore`。选 C 的「只剩本地手工」不再适用。

## OQ-TT-02：端点数 29 与 30 的口径

- **背景**：`technical-design/change-spec.md` §5 写「29 个端点」，`docs/api-spec.md` 端点总览列出 30 个（差异为 `POST /sessions/{sessionId}/inputs/text`）。
- **选项**：A（默认）以 `api-spec.md` 的 30 个为准，任务按 30 个实现；B 以 change-spec 的 29 个为准，把文本输入并入会话事件端点（改变契约）；C 回退 tech-design 统一文档后再开工。
- **建议**：A。api-spec 是逐端点契约，change-spec 的 29 是概述笔误；不改任何已确认契约，只在任务说明中注明差异。
- **影响**：无功能差异；仅文档一致性与评审口径。

## OQ-TT-03：前端自动化测试是否进入门禁

- **背景**：`change-spec.md` §6.1 列了 Vitest + Testing Library 与可选 Playwright，但 `.aw/config.json` 的 `test` 只有 pytest，`aw verify` / `aw close` 只认 pytest 报告里的 TC。
- **选项**：A（默认）前端不进门禁：TC 由服务端 pytest 承担，UI 状态用人工或 Playwright 记录，Vitest/Playwright 作为 P1 可选；B 把 Vitest 接进 `aw verify`（需改 `.aw/config.json` 与报告解析，超出本阶段范围）；C 只保留 Playwright E2E 手工脚本，不写组件测试。
- **建议**：A。保持门禁单一来源，避免「UI 绿」与「接口绿」两套证据；后续要接前端门禁时单独走配置变更。
- **影响**：TASK-TD-021/024/028/029/033/034/037/038/040/043/044/045/046 的验证方式写成「服务端 TC + 人工/Playwright 验收」。

## OQ-TT-04：备份恢复演练的验收方式

- **背景**：ADR-019 与 OQ-ARCH-05 A 要求提供 `scripts/backup.sh` 并做恢复演练，但该过程依赖真实 MySQL 与文件系统，无法在 pytest 内可信模拟。
- **选项**：A（默认）TASK-TD-049 标 `[no-test]`，以一次手工演练（备份 → 空库恢复 → 校验 `alembic_version` 与制品数量）作为验收证据并记录在 `docs/dev-setup.md`；B 用 testcontainers 写自动化恢复用例（成本高、CI 时间显著增加）；C 只交脚本，不做演练。
- **建议**：A。恢复演练是一次性运维验收，手工证据足够且成本最低；自动化恢复测试留到多环境部署阶段。
- **影响**：`aw close` 前需要一条人工验收记录；选 B 需新增 CI job 与 Docker 依赖。
