# Architecture Decisions Record (ADR)

> **文档状态：architecture-locked** — 2026-11-18 用户重新确认（`approvals.md` 2026-11-18 10:24:32，用户原话「全部确认」；spec 拆分后知识库 ADR 已迁出，新增 ADR-041）。
>
> 状态：**已确认（architecture-locked）**。依据 `technical-design/answers.md` 2026-11-17 19:49:04 用户原话「STK-001 A，STK-002 A，STK-003 A，STK-004 A」，以及 2026-11-18 10:24:32 拆分后重新确认。
> ADR-001 ~ ADR-009 来自用户拍板；ADR-010 ~ ADR-014 为用户未反对、采用默认。仓库现有代码为占位，不构成「已有」来源。
> 2026-11-17 20:09:45 用户确认 OQ-ARCH-01/02/04/05 全按 A（见 `technical-design/answers.md`），ADR-015 ~ ADR-028 状态已更新为已确认，决策原文未改。
> 2026-11-17 知识库轮次（US-012 ~ US-016）新增 ADR-029 ~ ADR-040，决策原文只追加。**2026-11-17 spec 拆分后 ADR-029 ~ ADR-040 已迁出至 knowledge-base spec（编号保留、正文以 handoff 为准）**；新增 ADR-041 记录拆分后的对外契约与仓库集成复用点。

## 锁定时间

2026-11-17 19:49 首次锁定；2026-11-18 10:24:32 spec 拆分后由用户重新确认并恢复锁定（阶段整体确认由编排者记录于 `approvals.md`；用户原话「全部确认」）。

## 项目扫描摘要

| 层次 | 检测结果 | 置信度 |
|------|---------|--------|
| 前端框架 | 未检测到（仅空 `src/`、`tests/`；无 `package.json`、无前端构建配置） | 高 |
| 前端组件库 / API 层 | 未检测到 | 高 |
| 后端框架 | 未检测到（`pyproject.toml` 仅占位，无依赖、无应用代码） | 高 |
| 数据库 / ORM | 未检测到（无迁移、无 schema、无 SQL） | 高 |
| 文件存储 | 未检测到 | 高 |
| 部署 | 未检测到（无 Dockerfile / compose / 部署配置） | 高 |
| 测试与门禁 | `.aw/config.json` 已配 `pytest` preset，`code_paths` 为 `src/`、`tests/` | 高 |
| 已有 ADR / 本体切片 | 无（暂存区无 KB 底稿；`ontology-slices/` 未生成） | 高 |

> 用户 2026-11-17 19:27 明确：`pyproject.toml` / `src/` / `tests/` 是占位，不代表技术选型，可按选定栈覆盖或删除。

## 已确认决策

### ADR-001：后端运行时与框架
- **决策**：Python 3.12+（本机 3.14.7）+ FastAPI 0.163.x + Uvicorn 0.54.x；Pydantic 2.14.x 做请求/响应校验。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：官方 openai / anthropic SDK 同步及时；密钥加密、上传、迁移库成熟；仓库测试门禁已是 pytest，选 A 无需改 `.aw/config.json`。
- **影响**：需 Python 工具链（uv）+ Node 仅用于前端构建；服务层与适配层用 async。
- **取代**：无

### ADR-002：前端框架、构建与路由
- **决策**：React 19.3 + TypeScript 7.0 + Vite 8.3 + React Router 8.5 + TanStack Query 5.107。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：组件状态多（时间线、对话框、表单三态），React 生态与无障碍原语最全；产物为静态文件，可由后端同源托管。
- **影响**：前端单独目录 `web/`（tech-tasks 定路径），构建产物 `web/dist` 由后端挂载。
- **取代**：无

### ADR-003：数据库与数据访问
- **决策**：SQLite（WAL 模式）+ SQLAlchemy 2.1 + Alembic 1.20 + aiosqlite。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：单用户自托管（AMB-004 A），关系约束与级联删除清晰；零运维、单文件备份；未来可换 PostgreSQL URL。
- **影响**：写操作串行，必须遵守「外部 AI 调用不在 DB 事务内」；启用 `busy_timeout` 与 WAL。
- **取代**：无

### ADR-004：AI 接入层为唯一模型出口
- **决策**：`AiGateway.complete()` 为唯一对外模型出口；内部用官方 SDK（openai 3.52.x 配自定义 `base_url`、anthropic 2.9.x）实现 OpenAI 兼容与 Anthropic 两类协议，统一领域错误码（`auth` / `rate_limit` / `server_error` / `timeout` / `unreachable` / `invalid_request` / `interrupted`）。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：满足 BG-01（后续 4 域零新增客户端代码）与 AMB-003 A（只两类协议，不做逐家厂商专属适配）；不引入 LangChain 等厚抽象。
- **影响**：超时 120s、仅网络错误与 5xx 重试 1 次、`retryCount` 入库；连接测试独立 10s 超时；失败不自动切模型。
- **取代**：无

### ADR-005：API 密钥加密与口令来源
- **决策**：AES-256-GCM（`cryptography` 50.x），密文格式 `v1:<nonce_b64>:<ciphertext_b64>`；口令来自环境变量 `AW_ENCRYPTION_KEY`（32 字节 base64），缺失或非法则拒绝启动；对外一律掩码（`sk-****abcd`）。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：AEAD 认证加密；版本前缀支持未来轮换；符合 AMB-005 A「服务端加密、口令来自环境变量、回显掩码」。
- **影响**：密钥丢失不可恢复（只能重新登记提供商）；日志与错误出口统一脱敏；数据库备份需与口令分开保管。
- **取代**：无

### ADR-006：制品文件存储与路径隔离
- **决策**：本地文件系统，根 `AW_DATA_DIR`（默认 `./data`），结构 `sessions/<sessionId>/<artifactId>.<ext>`；原名只存 DB；服务端生成存储名并对解析后路径做包含校验。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：AC-007 / AMB-007 只要求本机隔离与查看下载；对象存储引入凭据与网络依赖，单用户无收益。
- **影响**：备份/迁移需同时复制 DB 与 `sessions/`；删除走「先重命名到 `.trash`，DB 事务提交后清理」。
- **取代**：无

### ADR-007：前端样式与无障碍原语
- **决策**：CSS 变量直接映射 interaction-design Design Tokens + CSS Modules；Dialog / Tabs / Toast / Tooltip 用 Radix Primitives 1.8（无样式、MIT），不引入完整组件库。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：设计要求自定义近黑暗色与绿色强调，组件库预设主题会冲突；Radix 只提供行为与焦点管理，视觉完全由 token 控制。
- **影响**：表格、表单、Pill 等需自建；对比度与焦点态需回归测试。
- **取代**：无

### ADR-008：部署形态与网络绑定
- **决策**：单进程 Uvicorn 同时服务 `/api/v1` 与前端 `dist`（同源）；默认绑定 `127.0.0.1`；非本地绑定需显式 `AW_ALLOW_REMOTE=1` 并在启动时告警；Docker 作为可选交付。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：无登录（AMB-004 A），同源避免 CORS/CSRF 复杂度；本地绑定缩小密钥管理面暴露。
- **影响**：远程访问前必须先加认证与 TLS；开发态用 Vite proxy 到后端端口。
- **取代**：无

### ADR-009：HTTP 接口风格与错误结构
- **决策**：REST `/api/v1`，JSON；错误体 `{code, message, details[], requestId}`；列表统一 `limit` + `cursor` 分页；写操作返回资源表示。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 19:49 用户拍板 STK-001 A / STK-002 A / STK-003 A / STK-004 A）
- **理由**：前端只需消费一套错误与分页约定；后续域可通过同一风格扩展。
- **影响**：tech-design 的 api-spec 按此约定逐端点展开。
- **取代**：无

### ADR-010：AiCallRecord 持久化口径
- **决策**：不持久化完整请求/响应报文。存 `prompt_digest`（sha256）、`prompt_preview`（前 200 字符）、`prompt_char_count`、`result_text`（响应全文）、`latency_ms`、`retry_count`、`status`（`running`/`success`/`failed`/`timeout`）、`error_code`、`error_message`、模型快照字段；不存请求头与密钥。
- **来源**：新增
- **状态**：✅ 已确认（用户未反对，采用默认；见 `open-questions.md`「默认结论」）
- **理由**：满足 AC-005-1/2/4 与 AC-010-2 的复核需求，同时避免请求正文重复存储与敏感信息扩散；保留策略随会话永久保留、随会话级联删除（AMB-009 A）。
- **影响**：发起前插入 `running`，结束时更新；进程启动把遗留 `running` 归并为 `failed(interrupted)`，保证失败 100% 有记录。
- **取代**：无

### ADR-011：AI 结果文本存储形态
- **决策**：结果存 AiCallRecord 的 `result_text`（TEXT）+ `result_format`（本期固定 `text`，预留 `json`），不落为制品；前端用统一结果块渲染，后续域结构化输出复用同一字段。
- **来源**：新增
- **状态**：✅ 已确认（用户未反对，采用默认；见 `open-questions.md`「默认结论」）
- **理由**：级联删除与制品 10MB/10 个规则保持简单；避免「结果既在 DB 又在文件」的双源不一致。
- **影响**：超长结果受模型 `max_tokens` 约束；若后续需要导出为文件，作为新需求生成制品。
- **取代**：无

### ADR-012：状态变更审计字段
- **决策**：不单独建审计表；SessionEvent（type=`status_change`）payload 存 `{from, to, actor, at, reason}`；单用户自托管下 `actor` 取 `local-user`（用户操作）或 `system`（未捕获失败/启动归并）。
- **来源**：新增
- **状态**：✅ 已确认（用户未反对，采用默认；见 `open-questions.md`「默认结论」）
- **理由**：AC-009-4 要求状态流转可见，UX「人工可复核」要求进入时间线；多用户前无需独立审计模型。
- **影响**：未来启用 owner 时，`actor` 改为 ownerId，payload 结构保持兼容。
- **取代**：无

### ADR-013：制品预览与下载接口
- **决策**：`GET /api/v1/artifacts/{id}` 返回元数据；`GET /api/v1/artifacts/{id}/content?mode=inline|download[&max_bytes=262144]` 返回内容。Content-Type 由服务端按扩展名白名单映射，`X-Content-Type-Options: nosniff`，inline 仅限纯文本与 JSON，前端按纯文本转义渲染；下载返回完整文件（≤10MB）。
- **来源**：新增
- **状态**：✅ 已确认（用户未反对，采用默认；见 `open-questions.md`「默认结论」）
- **理由**：AC-007-1 要求可查看预览与大小；白名单内不含 HTML/SVG，杜绝脚本执行；限制 `max_bytes` 避免前端一次渲染超大文本。
- **影响**：tech-design 需定错误码（404 / 410）与文件名编码（RFC 5987）。
- **取代**：无

### ADR-014：跨会话导出与只读分享
- **决策**：本期不做跨会话导出与只读分享；`/calls` 仅提供筛选、展开核对与浏览器打印。
- **来源**：新增
- **状态**：✅ 已确认（用户未反对，采用默认；见 `open-questions.md`「默认结论」）
- **理由**：单用户本机场景下复核路径已闭合；只读分享需新增令牌/鉴权面，与本期「无登录」约束冲突。
- **影响**：若用户需要，作为独立需求（新 `aw-start`）或扩展计划中的「多用户 / 远程访问」阶段实现。
- **取代**：无

> **返工修订（2026-11-17，部署形态变更）**：用户 2026-11-17 19:52:50 原话「打断一下，这不是本地部署的，所以需要mysql。不能只是sqllite。」；同节记录的选项：数据库 MySQL 生产 + SQLite 开发/测试、加单用户登录、compose 默认并支持外接 MySQL。
> 下列 ADR-015 ~ ADR-028 为本轮新增，**已确认**（2026-11-17 20:09:45，OQ-ARCH-01/02/04/05 全按 A，见 `answers.md`）；ADR-001 ~ ADR-014 原文一字未改，ADR-003 / ADR-008 由新条目标注取代。
> 知识库轮次（US-012 ~ US-016）新增 ADR-029 ~ ADR-040，**已确认**（2026-11-17 20:27:18，OQ-ARCH-06 ~ OQ-ARCH-09 全按 A，见 `answers.md`）；接口与字段已按已确认的 interaction-design 知识库页面（Playwright 43 项断言通过）反向核对。

### ADR-015：数据库选型（MySQL 生产 + SQLite 开发/测试）
- **决策**：生产使用 MySQL 8.4 LTS（InnoDB / utf8mb4）；开发与默认自动化测试使用 SQLite（aiosqlite）；SQLAlchemy 2.1 异步引擎 + Alembic 1.20 单一迁移树。生产连接串来自环境变量 `AW_DATABASE_URL`；未设置时回退 `sqlite+aiosqlite:///<AW_DATA_DIR>/workbench.db`（仅开发）。
- **来源**：新增（取代 ADR-003；原「只用 SQLite」因用户 2026-11-17 19:52:50 的要求被推翻）
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：非本地部署需要服务端数据库；MySQL 是用户指定目标；保留 SQLite 是为了让仓库门禁 `pytest` 在无容器的机器上仍能跑通。
- **影响**：所有 schema 变更必须通过两种方言（ADR-016 / ADR-017）；`aw verify` 默认只覆盖 SQLite，MySQL 由 CI 第二 job 与本地 `AW_TEST_DATABASE_URL` 覆盖。
- **取代**：ADR-003

### ADR-016：MySQL 驱动与 ORM 方言策略
- **决策**：驱动 `asyncmy`（`mysql+asyncmy://`，SQLAlchemy 2.1 官方异步 MySQL 方言之一），备选 `aiomysql`。类型与语义按差异清单落地：`sqlalchemy.JSON`；索引列 `VARCHAR(≤191)`；唯一性键用 `casefold()` 归一列 + 列级 `utf8mb4_bin`；引擎 `isolation_level="READ COMMITTED"`；自增主键 `BigInteger().with_variant(Integer, "sqlite")`；时间统一由应用写 UTC；表参数 `mysql_engine=InnoDB`、`mysql_charset=utf8mb4`、`mysql_collate=utf8mb4_0900_ai_ci`。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：asyncmy 0.2.18（2026-11-07，Apache-2.0）提供 cp314 的 manylinux / musllinux / macOS wheel，容器内无需编译；aiomysql 0.3.2（纯 Python，MIT）作为缺 wheel 环境的后备。上列差异是两台引擎在 JSON、索引长度、大小写、隔离级别与 DDL 上真实存在的分叉点。
- **影响**：ORM 层禁止方言专属语法（`ON DUPLICATE KEY`、`NOW()`、区分大小写的唯一约束、TEXT 前缀索引）；新增字段在评审时对照差异清单；「只在一种方言跑过」视为缺陷。
- **取代**：无

### ADR-017：迁移工具与双方言执行
- **决策**：Alembic 单迁移树，`compare_type=True`；SQLite 用 `render_as_batch=True`，MySQL 直接 DDL；一个 revision 只做一类变更；compose 的 app 启动脚本先执行 `alembic upgrade head` 再起 Uvicorn；应用启动只校验 `alembic_version == head`，不自动改表。测试以「从空库升级到 head」验证两种方言。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：MySQL DDL 隐式提交，失败会留下半成品，小粒度 revision 才能排障；SQLite 不支持多数 ALTER，必须 batch 模式；显式迁移比启动自动迁移更易定位版本不一致。
- **影响**：部署多一步迁移（compose 已封装）；外接 MySQL 的账号需要 DDL 权限；tech-tasks 需产出 `docker-entrypoint.sh` 与迁移运维说明。
- **取代**：无

### ADR-018：连接池
- **决策**：SQLite 用 `NullPool`（aiosqlite 不做池化；内存测试库用 `StaticPool`）；MySQL 用 `AsyncAdaptedQueuePool`：`pool_size=5`、`max_overflow=5`、`pool_recycle=1800`、`pool_pre_ping=True`、`pool_timeout=10`；连接数上限由 `AW_DB_POOL_SIZE`（默认 5）可调。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：SQLite 文件库多连接无收益且更易撞锁；MySQL 需要连接复用与死连接探测；单用户流量下 5 连接充足。
- **影响**：`pool_pre_ping` 带来一次额外往返（可接受）；`pool_recycle` 必须小于 MySQL 的 `wait_timeout`。
- **取代**：无

### ADR-019：`AW_DATA_DIR` 语义、备份与恢复
- **决策**：`AW_DATA_DIR`（默认 `./data`，compose 为 `/data`）只承载：制品目录 `sessions/<sessionId>/`、删除中转 `.trash/`、开发/测试 SQLite 文件；**不承载生产库**。备份 = `mysqldump --single-transaction --routines --triggers`（或 MySQL 卷快照）+ 制品目录打包 + `AW_ENCRYPTION_KEY` 独立保管；恢复顺序「先库后制品」，恢复后跑启动自检确认 schema 版本与制品数量。tech-tasks 产出 `scripts/backup.sh` 与恢复步骤。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：数据库与文件的生命周期不同；只用文件快照无法保证 MySQL 一致性；加密口令与密文必须配套保管，否则恢复后提供商密钥不可解。
- **影响**：备份为两份而非一份；恢复演练列为验收项；备份时排除 `.trash/`。
- **取代**：无

### ADR-020：启动自检与失败策略
- **决策**：启动顺序 fail-fast：加密口令 → 管理员口令（缺失拒绝启动，日志提示「设置 `AW_ADMIN_PASSWORD` 后重启」）→ 连接串解析 → 数据库连通（最多 30s 退避重试）→ schema 版本等于 Alembic head（否则提示 `alembic upgrade head`）→ 凭据转存/轮换 → 遗留 `running` 调用记录归并 `failed(interrupted)` → 清理过期会话与失败计数。任一失败以非 0 退出，不进入服务状态。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：AC-REQ-17 要求口令缺失拒绝启动；非本地部署最常见的故障是连错库、忘迁移、忘配口令，必须显式报错。
- **影响**：compose 的 app 容器依赖 db healthy；健康检查不复用匿名端点（请求受保护接口并期望 401）；启动多一次 Argon2 校验（<0.2s）。
- **取代**：无

### ADR-021：管理员口令哈希与轮换
- **决策**：Argon2id（`argon2-cffi` 25.1.0，绑定 26.2.0），参数取库默认 RFC 9106 低内存档（memory_cost=64 MiB、time_cost=3、parallelism=4、hash_len=32、salt_len=16），编码串整体存 `admin_credential.password_hash`（单行 `credential_id=1`）。启动时读 `AW_ADMIN_PASSWORD`：无记录则哈希入库；有记录则用 Argon2 校验，不符即替换为环境变量对应的哈希（即轮换）。口令比较只经 Argon2 `verify`，不手写字符串比较。环境变量缺失或为空 → 拒绝启动。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：内存硬哈希对离线爆破成本最高；把环境变量当唯一真源，使「改环境变量 + 重启」就是轮换（AC-REQ-17），且从旧备份恢复后重启会自动回到部署方设定的口令。
- **影响**：数据库泄露时口令仍受 Argon2 保护；口令不落库、不入日志；每次启动有一次 Argon2 校验开销；`AW_ADMIN_PASSWORD` 需与数据库同等级保密。
- **取代**：无

### ADR-022：登录会话令牌形态
- **决策**：令牌 = `secrets.token_urlsafe(32)`（约 256 位熵），只在响应的 `Set-Cookie` 中下发；表 `login_session(login_session_id, token_hash CHAR(64) UNIQUE, created_at, last_seen_at, revoked_at NULL, source_ip_hash CHAR(64))`，只存 SHA-256 十六进制。校验 = 计算哈希后按唯一索引查行，要求 `revoked_at IS NULL` 且 `now - last_seen_at <= 8h`；命中即刷新 `last_seen_at`。登出与轮换写 `revoked_at`。过期/吊销记录保留 30 天供排查后清理。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：库泄露不等于会话可被冒用；8 小时空闲策略由服务端判定，不依赖客户端时钟；AC-011-5 / AC-011-6 / AC-REQ-15 要求服务端可吊销。
- **影响**：每次请求一次小 UPDATE（单用户可接受；多副本时需改为节流）；空闲超时必然要求重新登录；令牌不写入 URL、localStorage 或日志。
- **取代**：无

### ADR-023：会话 Cookie 安全属性
- **决策**：Cookie 名 `aw_session`；`HttpOnly`、`SameSite=Lax`、`Path=/`；Secure 由 `AW_COOKIE_SECURE=auto|true|false` 控制，`auto` 时按 `AW_PUBLIC_ORIGIN` 的 scheme 判定（https → Secure）；不设 `Expires/Max-Age`（浏览器会话 Cookie），失效完全由服务端空闲 8 小时判定；登录成功与登出都返回 `Set-Cookie`（登出置空并过期）。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：HttpOnly 阻断 XSS 读取；Lax 阻断跨站 POST 携带 Cookie；Secure 依赖部署是否 TLS，用显式配置避免反代下误判。
- **影响**：纯 HTTP 远程部署时 Cookie 仍会发送，但传输可被窃听，文档明确要求 TLS 反代；关闭浏览器后需重新登录（AC 未要求记住登录，符合最小暴露）。
- **取代**：无

### ADR-024：CSRF 防护
- **决策**：不使用 CSRF token。三层组合：①会话 Cookie `SameSite=Lax`；②所有非安全方法（POST/PUT/PATCH/DELETE）校验 `Origin`（缺失时退回 `Referer`）必须等于 `AW_PUBLIC_ORIGIN` 之一，不匹配返回 403；③写接口要求 `Content-Type: application/json`（文件上传为 `multipart/form-data`，同样受 Origin 校验）。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：同源 SPA + Cookie 会话下，Lax + Origin 校验覆盖浏览器实际可发起的跨站请求；token 方案需要下发/轮换与前端存储，与「令牌不落前端可读存储」相冲突。
- **影响**：`AW_PUBLIC_ORIGIN` 在远程部署时成为必填项，配错会 403；非浏览器客户端需带正确 Origin 或走登录接口；测试覆盖缺 Origin / 错 Origin / 跨站 POST 三类。
- **取代**：无

### ADR-025：登录失败计数与来源锁定
- **决策**：表 `login_attempt(source_ip_hash CHAR(64) PK, failed_count, first_failed_at, last_failed_at, locked_until NULL)`；来源 IP 存 SHA-256 而非原文。每次失败在同一事务内 `SELECT … FOR UPDATE`（MySQL）/ 串行写（SQLite）后自增；达到 5 次写 `locked_until = now + 5min`；锁定期内直接返回 429 + `Retry-After`。成功登录删除该行（清零）。连续计数窗口 = 距上次失败超过 5 分钟则重新计数。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：AC-011-4 的阈值与清零需要跨进程重启保持；哈希 IP 降低个人信息落库；行锁 + 事务避免并发失败丢计数。
- **影响**：反向代理后默认取直连对端 IP，可能把所有人算作同一来源（ADR-028 与 OQ-ARCH-04）；锁定只拦截新登录，不影响已建立会话；清理任务删除 `last_failed_at` 超过 1 天的行。
- **取代**：无

### ADR-026：访问控制执行点
- **决策**：FastAPI 依赖 `require_session` 挂在 `/api/v1` 路由级（白名单仅 `/api/v1/auth/login`）；同一校验用于 HTML 导航：无有效会话且路径非 `/login`、非静态资源时 302 到 `/login`。未认证 API 返回 401 统一错误体（`{code:"unauthorized"}`），不含任何业务字段。登录成功后由服务端 `Set-Cookie`，前端不接触令牌；任意 401 触发跳转登录页。容器健康检查请求受保护接口并期望 401，不新增匿名端点。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：AC-011-1 / AC-REQ-13 要求页面与接口双层拦截；路由级依赖比逐端点手写更难漏；保持「无匿名业务端点」使 AC-REQ-13 可用端到端用例验证。
- **影响**：新增端点默认受保护（豁免需评审）；静态资源与 `/login` 例外需测试覆盖；健康检查方式较重但只在内网。
- **取代**：无

### ADR-027：部署形态（docker-compose 默认 + 外接 MySQL）
- **决策**：默认交付 `docker-compose.yml`：`app`（多阶段构建，Node 构建 `web/dist` → Python 3.14-slim 运行，非 root）+ `db`（`mysql:8.4`，utf8mb4，具名卷 `mysql-data`，只在内网暴露）；`app` 依赖 `db` healthy；启动脚本执行 `alembic upgrade head` 后起 Uvicorn；端口默认发布 `127.0.0.1:8000`。外接 MySQL：不启用 `db` 服务，`AW_DATABASE_URL` 指向现有实例（账号需 DDL 权限），其余相同。配置经 `.env`（gitignore）+ `.env.example`，不把密钥写入镜像。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：用户明确需要非本地部署；compose 是单用户自托管的最低运维成本；外接实例让已有 MySQL 的部署方无需再维护一套。
- **影响**：镜像构建需要 Node 与 Python 两阶段；`AW_PUBLIC_ORIGIN` 与 `AW_COOKIE_SECURE` 必须按实际访问地址配置；TLS 不在 compose 内默认提供（OQ-ARCH-05）。
- **取代**：ADR-008

### ADR-028：网络绑定与暴露面收敛（沿用 STK-004）
- **决策**：继续保留 STK-004 的默认本机绑定：裸机运行默认 `127.0.0.1:8000`；非回环绑定必须显式 `AW_ALLOW_REMOTE=1`（compose 中显式写入）并打印告警；compose 端口映射默认 `127.0.0.1:8000:8000`。登录带来的收敛：所有业务面在认证之后，未认证只剩登录页、登录接口与静态资源；登录接口自带失败锁定与统一错误；远程部署必须经 TLS 反代（Secure Cookie），否则文档标注为不安全配置。
- **来源**：新增
- **状态**：✅ 已确认（2026-11-17 20:09:45 用户确认，依据 `technical-design/answers.md`）
- **理由**：STK-004 的默认值在远程场景同样是最小暴露；但「加了登录」不等于「可以直接对公网」，仍需 TLS 与绑定收敛。
- **影响**：用户在 compose 中改端口映射即对外暴露，文档必须并列写明「同时配置 TLS 反代与 `AW_PUBLIC_ORIGIN`」；`AW_ALLOW_REMOTE=1` 成为远程部署的显式确认开关。
- **取代**：无（ADR-008 的绑定部分由 ADR-027 承接，本条明确沿用 STK-004 并说明与登录的关系）

### ADR-029：知识库归属、命名唯一与版本化
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 1、7 节
- **取代**：无

### ADR-030：知识库实体与双方言类型映射
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 1 节
- **取代**：无

### ADR-031：知识库文件落盘、导入原子性与容量控制
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 2 节
- **取代**：无

### ADR-032：`index.json` 解析契约
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 3、4 节
- **取代**：无

### ADR-033：条目正文匹配与「正文缺失」降级
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 3.3 节
- **取代**：无

### ADR-034：注入组装服务与 200,000 字符预算
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 5 节
- **取代**：无

### ADR-035：知识库注入的留痕口径
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 5 节
- **取代**：无

### ADR-036：知识库 API 契约与检索策略
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 6 节
- **取代**：无

### ADR-037：新鲜度与版本冲突判定
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 7 节
- **取代**：无

### ADR-038：删除语义
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 7 节
- **取代**：无

### ADR-039：知识库内容的安全与日志边界
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 3.4 节
- **取代**：无

### ADR-040：导入护栏与可配置限额
- **状态**：➡️ 已迁出至 knowledge-base spec（2026-11-17 spec 拆分；编号保留、不重排）
- **原文**：`specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 8 节
- **取代**：无

### ADR-041：spec 拆分后的对外契约保留与仓库集成复用点

- **决策**：
  1. 本 spec 保留 `workbench-core` 基座架构；知识库部分整体迁出至 knowledge-base spec（ADR-029 ~ ADR-040 保留编号、正文以 handoff 为准）；仓库集成迁出至 repo-integration spec，**其架构扩展本 spec 现有设计，不另起一套**。
  2. 进程内对外签名冻结（名称与语义不得改，具体参数类型由 tech-design 展开）：`sessions.create(...)`、`sessions.append_event(...)`、`artifacts.save(...)`；`AiGateway.complete(...)` 仍是唯一模型出口。新 spec 只调用，不修改。
  3. repo-integration 复用点：
     - 凭证加密：复用 `core.crypto` 的 AES-256-GCM、`AW_ENCRYPTION_KEY`、`v1:<nonce_b64>:<ciphertext_b64>` 格式与掩码函数（`ghp_****abcd` 形态），新增的 `repo_binding.token_ciphertext` 同口径；
     - 错误结构：复用 `{code, message, details[], requestId}` 与 HTTP 状态映射；域专属错误码不改变外层结构；
     - 分页：复用 `limit` + `cursor` 约定与统一排序语义；
     - 认证：复用 `require_session` 路由级依赖与 401 统一错误体，不新增匿名端点；
     - 项目归属：`repo_binding.project_id` FK → `project_context`，沿用 `ON DELETE RESTRICT`；
     - 双方言：新表/新列必须同时通过 SQLite 与 MySQL 的迁移与用例；
     - 数据目录与备份：若新增落盘内容，必须纳入 `AW_DATA_DIR` 与 `scripts/backup.sh` 范围（本期仓库集成只把元数据存 DB，不落文件）；
     - 测试门禁：沿用 `pytest` preset 与 TC 编号命名规则。
  4. 200,000 字符常量由本 spec 定义一次（`AW_PROMPT_MAX_CHARS`，与粘贴上限共口径）；knowledge-base 的注入正文与提示合计沿用同一常量，不另定义。
- **来源**：新增（用户 2026-11-17 20:50:31 决策拆 3 个 spec；用户已定「repo-integration 的架构扩展本 spec 现有设计」）
- **状态**：✅ 已确认（2026-11-18 10:24:32 用户重新确认，`approvals.md`；决策原文未改）
- **理由**：拆分后两个新 spec 都要调用 core 的会话、事件、制品与 AI 网关；把复用点写死在这里，新 spec 的 tech-arch 可以直接扩写，不必重新拍板认证、加密、错误与分页。
- **影响**：上述签名若需调整，必须走本 spec 变更；repo-integration 新增错误码/分页字段时须在自己的 ADR 声明，并保持外层结构兼容。
- **取代**：无

## 约束条件

- 交付形态为 Web 应用（浏览器访问，前后端同源部署）；本 spec 仅覆盖 `workbench-core` 域。
- 默认部署形态为 docker-compose（app + mysql:8.4），并支持只提供 `AW_DATABASE_URL` 的外接 MySQL 实例（ADR-027）。
- 生产库为 MySQL 8.4 LTS；SQLite 仅用于开发与默认测试；两套方言必须同时通过迁移与用例（ADR-015 ~ ADR-017）。
- 单用户登录（替代 AMB-004 原「无登录」，依据 2026-11-17 19:52:50 用户选择）：除登录页、`/api/v1/auth/login` 与静态资源外，所有页面/接口要求有效登录会话；只做单账号，不做注册、找回与角色权限；`owner` 字段保留但不参与鉴权。
- 口令仅存 Argon2id 哈希；会话令牌只以 SHA-256 哈希入库；`AW_ADMIN_PASSWORD` 缺失或为空时拒绝启动；轮换 = 改环境变量后重启（AMB-011、AC-REQ-17）。
- 登录会话空闲 8 小时失效（每请求刷新 `last_seen_at`，无绝对上限）；同一来源 IP 连续失败 5 次锁 5 分钟，成功登录清零（AMB-012、AMB-013、AC-011-4/5）。
- 登录接口失败提示不区分原因；登录口令、口令哈希与登录会话令牌不得出现在日志、接口响应、AiCallRecord 与界面（AC-011-3、AC-REQ-16）。
- `AW_DATA_DIR` 只承载制品、删除中转与开发用 SQLite 文件；生产库数据在 MySQL 卷内，备份与恢复按 ADR-019。
- 数据库不可达或 schema 版本不等于 Alembic head 时拒绝启动（ADR-020）。
- 提供商仅支持 OpenAI 兼容协议（自定义 baseURL）与 Anthropic 官方 API 两类（AMB-003 A）。
- API 密钥服务端加密存储，口令来自环境变量；响应、日志、提示摘要不得出现完整密钥（AMB-005 A）。
- 文本粘贴单次正文 ≤200,000 字符，超限拒绝并提示当前字数与上限（AMB-010 A）。
- 上传白名单 `.txt .md .markdown .log .json .yaml .yml .csv .sql`；单文件 ≤10MB、单次 ≤10 个；同名自动改名（AMB-007 A）。
- 模型调用单次超时 120s；仅网络错误与 5xx 自动重试 1 次；失败留痕且不自动切模型；连接测试 10s 独立超时（AMB-008 A）。
- 会话与制品永久保留，仅支持手动删除整个会话并级联清理（AMB-009 A）。
- 制品按 `sessions/<sessionId>/` 隔离，路径不得跨会话引用；业务域不得直连模型，跨域只通过进程内接口。
- 每次进入提供商的模型调用（成功或失败）都必须留下 AiCallRecord。
- 本 spec 只覆盖 `workbench-core`；知识库与仓库集成已迁出至各自 spec（ADR-041）。知识库相关约束（归属/版本/导入限额/解析/注入预算/删除/日志边界）原文见 `specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md`。
- 对外签名 `sessions.create` / `sessions.append_event` / `artifacts.save` 与 `AiGateway.complete` 冻结，新 spec 只调用、不修改（ADR-041）。
- repo-integration 扩展本 spec 现有设计：复用凭证加密（AES-256-GCM + `AW_ENCRYPTION_KEY` + 掩码）、错误体 `{code, message, details[], requestId}`、`limit` + `cursor` 分页、`require_session` 认证前置与双方言纪律（ADR-041）。
- `AW_PROMPT_MAX_CHARS=200000` 只在本 spec 定义一次；knowledge-base 的注入正文字符口径沿用同一常量（ADR-041）。
- 未安装任何 AlonWorkflow pack（`.aw/install.json` 的 `packs` 为空），未套用 pack 专属约定。

## 状态

architecture-locked（2026-11-18 10:24:32 用户重新确认并恢复锁定；2026-11-17 19:49 首次锁定、20:09:45 与 20:27:18 两轮确认记录保留于文首；ADR-003 / ADR-008 已被取代、原文保留；ADR-029 ~ ADR-040 已迁出至 knowledge-base spec、编号保留；ADR-041 记录拆分后的对外契约与仓库集成复用点）
