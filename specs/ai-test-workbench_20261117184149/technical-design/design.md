# Technical Design — Design

> 阶段：tech-arch（步骤 1–3.5）。
> **文档状态：architecture-locked — 2026-11-18 10:24:32 用户重新确认（`approvals.md`，用户原话「全部确认」）。**
> 2026-11-18 依赖版本核实：FastAPI 0.163.2、SQLAlchemy 2.1.9、pydantic-settings 2.16.3，均为实际安装版本，无降级（见 ADR-043）。
> 依据：`technical-design/answers.md` 2026-11-17 19:49:04（STK-001~004 全 A）；2026-11-17 19:52:50 用户原话「打断一下，这不是本地部署的，所以需要mysql。不能只是sqllite。」与同节三项选择（MySQL 生产 + SQLite 开发/测试、加单用户登录、compose 默认并支持外接 MySQL）；2026-11-17 20:50:31 拆 3 个 spec（workbench-core / knowledge-base / repo-integration）。
> 现行结论：本 spec 只覆盖 `workbench-core`。Python/FastAPI + React；**MySQL 8.4 LTS 生产 + SQLite 开发/测试**；**单用户登录**（Argon2id + HttpOnly Cookie 会话）；**docker-compose 默认交付且支持外接 MySQL**。知识库部分（ADR-029 ~ ADR-040、决策 11 ~ 13、`knowledge_bases` / `knowledge_entries` 表与相关端点）已整体迁出至 `specs/knowledge-base_20261117205011`，技术原文见该 spec 的 `_handoff/from-tech-arch.md`；仓库集成迁出至 `specs/repo-integration_20261117205011`，其架构**扩展本 spec 现有设计**（复用凭证加密、错误体与分页，见 ADR-041）。
> 决策见 `docs/architecture-decisions.md`（ADR-003 / ADR-008 已被 ADR-015 / ADR-027 取代，原文保留；ADR-029 ~ ADR-040 编号保留并标注已迁出）。
> 仓库现有 `pyproject.toml` / `src/workbench/` / `tests/` 是占位（用户 2026-11-17 19:27 明确），不作为选型依据，可按选定技术栈删除重建。

## 技术选型

### 技术栈总览（方案 A + 2026-11-17 返工修订）

| 层次 | 选型 | 版本（联网核实 2026-11-17） | 来源 | 理由摘要 |
|------|------|------|------------------|---------|
| 前端框架 | React + TypeScript | react 19.3.1 (MIT) / typescript 7.0.2 (Apache-2.0) | 新增 | 组件生态最全，配自定义 Design Tokens 无需迁就组件库主题 |
| 前端构建 | Vite | 8.3.8 (MIT) | 新增 | 启动/构建快，产物为静态文件，可由后端同源托管 |
| 前端路由 | React Router | 8.5.1 (MIT) | 新增 | 覆盖 8 条路由，支持刷新直达（AC-001-2） |
| 数据获取 | TanStack Query | 5.107.2 (MIT) | 新增 | 列表/时间线的 loading / empty / error 三态与失效重取 |
| 样式 / 无障碍原语 | CSS 变量 + CSS Modules；Radix Primitives | radix-ui 1.8.1 (MIT) | 新增 | 直接落地 interaction-design 的 token；Dialog/Tabs/Toast 用无样式原语保证焦点管理 |
| 后端运行时 | Python | 3.12+（本机 3.14.7） | 新增 | 官方 openai/anthropic SDK 与加密、测试生态成熟 |
| 后端框架 | FastAPI + Uvicorn | fastapi 0.163.2 (MIT) / uvicorn 0.54.0 (BSD-3) | 新增 | 类型化 HTTP 契约、自动 OpenAPI、异步 IO |
| 数据校验 | Pydantic | 2.14.3 (MIT) | 新增 | 请求/响应边界校验，错误逐字段（AC-003-2） |
| ORM / 迁移 | SQLAlchemy + Alembic | 2.1.9 / 1.20.1（均 MIT） | 新增 | 异步 ORM，一套模型跑两套方言；迁移按方言生成 DDL |
| 数据库（生产） | MySQL 8.4 LTS | 镜像 `mysql:8.4.13`；兼容 8.0+ | 新增 | 用户要求非本地部署；事务、并发与运维工具成熟 |
| 数据库（开发/测试） | SQLite + aiosqlite | aiosqlite 0.22.1（MIT） | 新增 | 零依赖本地跑通与默认测试路径 |
| MySQL 驱动 | asyncmy（`mysql+asyncmy`） | 0.2.18（Apache-2.0） | 新增 | cp314 多平台 wheel，容器内无需编译；备选 aiomysql 0.3.2 |
| 口令哈希 | argon2-cffi（Argon2id） | 25.1.0（MIT）/ argon2-cffi-bindings 26.2.0 | 新增 | 内存硬、抗 GPU；RFC 9106 低内存档参数，cp314 wheel 齐全 |
| 配置 | pydantic-settings | 2.16.3（MIT） | 新增 | 环境变量集中声明与启动期校验（`AW_ADMIN_PASSWORD` / `AW_DATABASE_URL` 等） |
| 测试基础设施 | testcontainers（本地可选）+ CI service 容器 | 4.15.0（Apache-2.0） | 新增 | 本地按需起 MySQL，CI 用 service 容器，不依赖 Docker-in-Docker |
| AI 接入 | 官方 SDK | openai 3.52.0 (Apache-2.0) / anthropic 2.9.0 (Apache-2.0) | 新增 | 覆盖两类协议，base_url 可自定义；避免自写重试/错误映射 |
| 密钥加密 | cryptography（AES-256-GCM） | 50.0.2 (Apache-2.0 OR BSD-3-Clause) | 新增 | AEAD，认证加密；口令来自环境变量（AMB-005 A） |
| 上传解析 | python-multipart | 0.0.34 | 新增 | FastAPI 文件上传依赖（制品上传） |
| 后端测试 | pytest + httpx | 仓库 `.aw/config.json` 已配 pytest preset | 新增 | 默认跑 SQLite；`AW_TEST_DATABASE_URL` 指向 MySQL 时同一套用例跑第二方言；接口级测试可跑 TC 编号 |
| 前端测试 | Vitest + Testing Library；Playwright | vitest 5.1.0 / @testing-library/react 16.3.3 / @playwright/test 1.65.1 | 新增 | 组件状态覆盖 + 关键流程 E2E |
| 部署 | docker-compose（app + mysql:8.4）默认；支持外接 MySQL 实例；单进程 Uvicorn 托管前端 `dist` | compose 文件（tech-tasks 产出） | 新增 | 一个端口、同源无 CORS；连接串走 `AW_DATABASE_URL` |

> 备选方案 B（Node.js）与 C（Go）见「决策 1」「决策 2」。

### 研究与复用（2026-11-17 返工核实）

本轮新增的技术点全部先核实版本与维护状态，不凭记忆写版本号：

- **PyPI JSON**（`curl -s https://pypi.org/pypi/<包>/json`）：`asyncmy` 0.2.18（2026-11-07，Apache-2.0，含 cp313/cp314 的 macOS、manylinux、musllinux wheel）；`aiomysql` 0.3.2（2025-10-22，MIT，纯 Python）；`pymysql` 1.2.4（2026-11-09）；`aiosqlite` 0.22.1；`argon2-cffi` 25.1.0（MIT；绑定 `argon2-cffi-bindings` 26.2.0 有 cp314 wheel）；`bcrypt` 5.0.0；`sqlalchemy` 2.1.9（2026-11-16，requires-python ≥3.11；2026-11-18 经 `uv lock`/`uv sync` 实装复核）；`alembic` 1.20.1；`testcontainers` 4.15.0（2026-07-24）；`pydantic-settings` 2.16.3（2026-11-13）。
- **Docker Hub tags API**（`hub.docker.com/v2/repositories/library/mysql/tags`）：当前标签含 `8.4.13` / `9.7.4` / `26.10.0` 与 `lts`；选 8.4 LTS 作为生产基线。
- **Context7**：`/sqlalchemy/sqlalchemy`（10,372 stars）确认异步 MySQL 方言用法为 `create_async_engine("mysql+asyncmy://…?charset=utf8mb4")`；`/hynek/argon2-cffi`（verified，630 stars，2026-11-02 更新）确认 `PasswordHasher` / `Parameters` 用法与 RFC 9106 低内存默认档；`argon2.profiles.get_default_parameters()` 按平台给出兼容参数。
- **复用结论**：MySQL 驱动、连接池、迁移、口令哈希全部用成熟库，不自研；未用 `fastapi-users` / `Authlib`（单账号、无注册与 OAuth，带来的用户表与找回流程用不上）；未用 `slowapi`（失败计数要按 AC-011-4 跨重启保持并可清零，放数据库比进程内存更可验证）。
- 备选驱动 `aiomysql` 仅在目标平台缺 asyncmy wheel 时替换，ORM 与迁移代码不变。

**知识库轮次追加核实（2026-11-17）已随 spec 迁出**：`markdown-it-py` / `orjson` / `ijson` / `Pygments` 均未引入；`MEDIUMTEXT` 变体与 `sa.JSON` 写法、`LIKE` 检索等结论见 `specs/knowledge-base_20261117205011/_handoff/from-tech-arch.md` 第 1、6 节。本 spec 不新增解析或检索依赖。

### 详细决策

#### 决策 1：后端运行时与框架

| 候选 | 版本现状 | 优点 | 代价 |
|------|---------|------|------|
| A. Python 3.12+ / FastAPI | fastapi 0.163.2、sqlalchemy 2.1.9 | 官方 openai/anthropic SDK 同步最及时；pytest 与现有 `aw verify` 门禁天然一致；加密、上传、迁移库成熟 | 需同时装 Python 与 Node 两套工具链 |
| B. Node.js 24 / NestJS | Node 24.21.0、@nestjs/core 12.5.1、fastify 5.12.8、drizzle-orm 0.45.4 | 前后端同语言；内置 `crypto` 与 node:sqlite；单工具链 | 推荐 Fastify/Express + Drizzle 也可行；NestJS 对单用户自托管偏重；需改 `.aw/config.json` 的 pytest test 命令 |
| C. Go 1.2x / Chi | 单二进制、低内存、无运行时依赖 | 生态与 AI SDK 需自行封 HTTP，前端仍需 Node 构建；团队调试成本更高 | 需改 `.aw/config.json` test 命令 |

- **选择**：A（已确认）。
- **理由**：本项目 ~80% 复杂度在「AI 协议适配 + 密钥安全 + 会话/记录一致性」，Python 官方 SDK（openai 3.x、anthropic 2.x）与 `cryptography` 能直接复用；且仓库测试门禁已是 pytest，选 A 不需要改门禁配置。
- **备选方案**：B Node.js（若用户希望前后端统一 TypeScript）；C Go（若强调单二进制分发）。
- **权衡**：接受双工具链（Python 后端 + Node 仅构建前端）；接受异步 Python 在 CPU 密集任务上的劣势（本项目无重计算）。

#### 决策 2：前端框架与构建

| 候选 | 版本现状 | 说明 |
|------|---------|------|
| A. React 19 + Vite + TypeScript | react 19.3.1 / vite 8.3.8 / ts 7.0.2 | 生态与可访问性原语最全；与 interaction-design 的自定义组件清单一一对应 |
| B. Vue 3 + Vite | vue 3.5.45 / vite 8.3.8 | 模板语法上手快，SFC 组织清晰 |
| C. Svelte 5 + SvelteKit | svelte 5.57.3 / @sveltejs/kit 3.2.0 | 产物小；但 SvelteKit 默认 SSR/Node 运行时，本项目只需 SPA，需额外裁剪 |
| D. 无框架（原生 TS + Web Components） | — | 无依赖；但 15+ 组件、时间线与对话框状态管理成本高，不推荐 |

- **选择**：A（已确认）。
- **理由**：页面含 15+ 有状态组件、时间线、多步表单与对话框焦点管理，React + Radix 原语能直接对应组件清单与状态列表。
- **备选方案**：Vue 3（团队偏好时替换，设计 token 与 API 契约不变）；Svelte 5（仅当接受裁剪 SvelteKit）。
- **权衡**：React 依赖体积大于 Svelte，内网单用户场景可接受。

#### 决策 3：数据库与数据访问（2026-11-17 修订，取代原「只用 SQLite」）

| 候选 | 说明 |
|------|------|
| **A. MySQL 8.4 LTS（生产）+ SQLite（开发/测试）** | 生产用远程 MySQL；本地与自动化测试零依赖跑 SQLite；SQLAlchemy 2.1 异步 + Alembic 1.20 单一迁移树 |
| B. 只用 MySQL | 测试也依赖容器，本地开发门槛高；`aw verify` 在无 Docker 的机器上会红 |
| C. PostgreSQL | 能力更强，但用户已明确 MySQL，且部署方已有 MySQL 运维能力 |
| D. 双 ORM / 双 schema | 模型与迁移双份维护，长期漂移风险最高，否决 |

- **选择**：A（修订后）。
- **理由**：用户 2026-11-17 19:52 明确「这不是本地部署的，所以需要mysql」；同时保留 SQLite 让 `aw verify` 的默认 pytest 无需外部服务（仓库门禁命令不变）。
- **备选方案**：B（若不介意每次跑测试都起容器）；C（若后续放弃 MySQL）。
- **权衡**：接受双方言维护成本，必须显式处理下表差异；任何新字段/索引都要求两种方言下迁移成功（ADR-016 / ADR-017）。

| 差异点 | MySQL 8.4 | SQLite | 本项目处理 |
|--------|-----------|--------|-----------|
| JSON 字段 | 原生 `JSON` 类型 | `TEXT` 存 JSON | 统一 `sqlalchemy.JSON`；只用于 `SessionEvent.payload`，不建索引 |
| 字符串索引长度 | utf8mb4 下 InnoDB 索引上限 3072 字节（≈768 字符） | 无限制 | 被索引的 `VARCHAR` ≤191 字符；哈希列用 `CHAR(64)` |
| 大小写敏感性 | 默认 `utf8mb4_0900_ai_ci` 不区分大小写 | `BINARY` 区分 | 唯一性键另存 `*_key`（`casefold()` 归一）列，列级 `utf8mb4_bin`，两方言行为一致 |
| 事务隔离级别 | 默认 REPEATABLE READ | 串行写（WAL） | 引擎级 `isolation_level="READ COMMITTED"`；事务保持毫秒级 |
| 自增主键 | `AUTO_INCREMENT` | `INTEGER PRIMARY KEY`（rowid 别名） | `BigInteger().with_variant(Integer, "sqlite")`；DDL 全部由 Alembic 按方言生成，不手写方言语法 |
| 时间类型 | `DATETIME(6)`、无时区语义 | `TEXT` | 应用层写 UTC，不用数据库 `NOW()`；时间比较只在应用层做 |
| Upsert / 行锁 | `INSERT … ON DUPLICATE KEY UPDATE`、`SELECT … FOR UPDATE` | `ON CONFLICT`、全库写锁 | 登录失败计数用「事务内 `SELECT … FOR UPDATE` + 更新」，不用方言专属 upsert |
| DDL 事务 | DDL 隐式提交，失败留半成品 | DDL 可回滚 | 一个 revision 只做一类变更；CI 在两种方言上从零迁移冒烟 |

#### 决策 4：AI 接入层

| 候选 | 说明 |
|------|------|
| A. 官方 SDK + 薄适配层（openai `base_url` / anthropic `base_url`） | 重试、超时、错误类型由 SDK 处理；只写「协议 → 领域错误」映射 |
| B. 统一用 httpx 手写两类协议 | 完全可控、依赖少；需自行处理重试/流/错误分类，测试面更大 |
| C. LangChain / 统一抽象框架 | 抽象层厚、版本漂移快、调试困难；本需求只有 2 种协议，收益低 |

- **选择**：A（已确认）。
- **理由**：BG-01 要求后续 4 域零新增 HTTP 客户端；`AiGateway.complete()` 一处的适配层即可满足，SDK 只是其内部实现。OpenAI 兼容厂商（含国内厂商、Ollama）通过 `base_url` 覆盖。
- **备选方案**：B（若对 SDK 大版本变动不放心，可用 httpx 实现同接口）。
- **权衡**：接受 SDK 依赖与版本锁定（`uv.lock`）；`max_retries=1`、`timeout=120s` 由适配层显式传入并按 AC-005-5 记录 `retryCount`。

#### 决策 5：密钥加密与掩码

- **选择**：AES-256-GCM（`cryptography`），密文格式 `v1:<nonce_b64>:<ciphertext_b64>`；密钥由环境变量 `AW_ENCRYPTION_KEY`（32 字节 base64）提供，启动时校验缺失即拒绝启动。
- **理由**：AEAD 同时保证机密性与完整性；版本前缀为密钥轮换留出空间；比 Fernet（AES-128-CBC + HMAC）更现代。
- **备选方案**：Fernet（实现更短，但仅 AES-128）；OS Keychain/keyring（无头部署不可用，不符合自托管）。
- **权衡**：环境变量密钥需用户自行保管；密钥丢失则已存密钥不可解密（设计为登记新提供商，不做恢复）。

#### 决策 6：制品存储

- **选择**：本地文件系统，根目录 `AW_DATA_DIR`，结构 `sessions/<sessionId>/<artifact存储名>`；存储名由服务端生成（`<artifactId>.<ext>`，原名另存 DB），禁止客户端路径参与拼接。
- **理由**：AC-007 / AMB-007 只要求本机隔离与查看下载；对象存储引入凭据与网络依赖，单用户场景无收益。
- **备选方案**：S3/MinIO（未来多机部署时）。
- **权衡**：备份需同时复制 DB 与 `sessions/`；删除需 DB + 文件两步（见 RISK-006）。

#### 决策 7：前端样式与组件

- **选择**：CSS 变量（直接映射 interaction-design 的 Design Tokens）+ CSS Modules；交互原语用 Radix Primitives（Dialog / Tabs / Toast / Tooltip），不引入完整组件库。
- **理由**：设计系统已自定义暗色近黑 + 绿色强调，Ant Design / MUI / shadcn 预设主题会与之冲突并引入覆盖成本；Radix 只提供行为与 a11y（焦点陷阱、Esc 归还焦点），样式完全由 token 驱动。
- **备选方案**：Tailwind CSS 4（需把 token 映射为 theme，团队熟悉时可选）；Element Plus / Ant Design（牺牲视觉一致性换开发速度）。
- **权衡**：通用组件（表格、表单、Pill）需自建，工作量略高于组件库；换取 1:1 还原设计稿与对比度。

#### 决策 8：部署形态（2026-11-17 修订）

- **选择**：docker-compose 为默认交付：`app`（多阶段构建、非 root、Uvicorn 托管 `/api/v1` 与 `web/dist`）+ `db`（`mysql:8.4`，具名卷，utf8mb4）；迁移在 app 启动脚本中先于服务执行。同时支持「只给 `AW_DATABASE_URL`、不启动 db 服务」的外接 MySQL 部署。端口默认发布到 `127.0.0.1:8000`。
- **理由**：用户要求非本地部署，需要可复制的交付物；外接实例覆盖已有 MySQL 的运维环境。
- **备选方案**：Kubernetes/Helm（本期过度）；Nginx + systemd 裸机（文档给出等价步骤，不作为默认）。
- **权衡**：对外暴露需改端口映射并加 TLS 反代（OQ-ARCH-05）；不接受「compose 直接对公网裸奔」。绑定策略见决策 9 与 ADR-028。

#### 决策 9：单用户登录、会话与凭据

- **选择**：单账号登录。口令由 `AW_ADMIN_PASSWORD` 提供，启动时以 Argon2id 转存（argon2-cffi 默认 RFC 9106 低内存参数：m=64 MiB、t=3、p=4）；环境变量视为真源，启动时校验不符即改写哈希（即轮换）。会话令牌 = `secrets.token_urlsafe(32)`，库中只存 SHA-256 十六进制；Cookie `aw_session`（HttpOnly、SameSite=Lax、Path=/、HTTPS 下 Secure）；空闲 8 小时失效（每次请求刷新 `last_seen_at`，无绝对上限）；登出写 `revoked_at`。失败锁定按来源 IP：5 次 / 5 分钟，计数与锁定截止时间存库。
- **理由**：AC-011-1~7 / AC-REQ-13~17 已由用户定稿；不引入第三方认证框架（单账号、无 OAuth、无注册）。
- **备选方案**：`fastapi-users` / Authlib（用户表、找回流程、OAuth 面全部用不上）；bcrypt（72 字节截断，参数上限更硬）；进程内字典存失败计数（重启即清空，无法验证 AC-011-4 的锁定期）。
- **权衡**：单进程部署下无分布式会话问题；将来多副本时会话表本身可共享，但「每请求刷新」会成为写热点（见扩展计划）。

#### 决策 10：启动自检与环境变量

- **选择**：启动按序 fail-fast：①`AW_ENCRYPTION_KEY` 合法；②`AW_ADMIN_PASSWORD` 非空（缺失拒绝启动并给出可执行提示）；③`AW_DATABASE_URL` 方言可识别（未设置时默认 `sqlite+aiosqlite:///<AW_DATA_DIR>/workbench.db`，仅开发）；④数据库连通（compose 场景最多退避重试 30s）；⑤schema 版本等于 Alembic head，否则拒绝启动并提示 `alembic upgrade head`；⑥凭据转存/轮换；⑦遗留 `running` 调用记录归并为 `failed(interrupted)`；⑧清理过期登录会话与失败计数。
- **理由**：非本地部署下「连错库」「忘了建表」「忘配口令」是最常见故障；AC-REQ-17 要求口令缺失拒绝启动。
- **备选方案**：应用启动自动执行迁移（省一步，但多副本并发迁移与失败回滚不可控；本期单副本仍选显式迁移，便于排障）。
- **权衡**：部署多一个迁移步骤（compose 启动脚本已封装）；换来版本不一致时明确报错而不是半可用。

#### 决策 11 ~ 13：知识库（已迁出）

知识库存储形态与版本化（决策 11）、文件落盘与导入原子性（决策 12）、注入组装与预算收口（决策 13）已随 spec 迁出至 `specs/knowledge-base_20261117205011`；原文见该 spec 的 `_handoff/from-tech-arch.md` 第 1、2、5、7、8 节。本 spec 只保留 `AiGateway.complete` 作为唯一模型出口与 200,000 字符上限常量（ADR-041）。

## 系统架构

### 分层说明

| 层次 | 职责 | 技术 |
|------|------|------|
| 浏览器（SPA） | 路由、页面（含登录页）、表单校验、三态展示、掩码；不持有任何明文密钥，不把令牌写入 JS 可读存储 | React 19 + Radix + CSS token |
| 认证与访问控制 | 登录、令牌校验、空闲刷新、登出、失败锁定、Origin 校验 | FastAPI 中间件 + `services/auth` |
| HTTP API | REST `/api/v1`，请求/响应 Pydantic 校验，统一错误结构 | FastAPI |
| 应用服务层 | 用例编排：项目、提供商、模型、会话、事件、制品、调用记录 | Python services |
| 领域/适配器 | AI 协议适配（openai-compatible / anthropic）、加密、口令哈希、文件存储、日志脱敏 | `adapters/`、`core/` |
| 持久化 | 关系实体 + 事务 + 级联删除；生产 MySQL，开发/测试 SQLite | SQLAlchemy 2.1 async / asyncmy / aiosqlite |
| 文件系统 | `sessions/<sessionId>/` 制品隔离 | pathlib + containment 校验 |
| 外部集成 | OpenAI 兼容 API、Anthropic API（出站 HTTPS） | 官方 SDK |

### 模块划分

| 模块 | 职责 | 关联 US |
|------|------|---------|
| `frontend/auth` | 登录页、401 跳转、登出 | US-011 |
| `frontend/app-shell` | 侧边栏、顶栏、路由骨架、占位降级 | US-001 / US-002 |
| `frontend/entrances` | 6 入口配置与占位页 | US-001 / US-002 |
| `frontend/providers`、`frontend/models` | 提供商 CRUD、掩码、连接测试、模型绑定 | US-003 / US-004 |
| `frontend/projects` | 项目上下文 CRUD | US-008 |
| `frontend/sessions` | 列表/筛选/创建/详情/时间线/删除 | US-009 |
| `frontend/composer` | 文本粘贴、字数、文件上传与校验 | US-006 / US-007 |
| `frontend/calls` | 发起调用、参数覆盖、调用记录查询 | US-005 / US-010 |
| `backend/api` | 路由 + 请求/响应 schema + 依赖注入 | 全部 |
| `backend/services/auth` | 口令校验、会话签发/刷新/吊销、失败计数与锁定 | US-011 |
| `backend/services/session` | 会话状态机、事件追加、级联删除 | US-009 |
| `backend/services/artifact` | 上传校验、落盘、预览/下载 | US-007 |
| `backend/services/provider` | 加密存储、掩码、连接测试 | US-003 / US-004 |
| `backend/services/ai_gateway` | **唯一模型出口**：参数合并、超时、重试、AiCallRecord | US-005 / US-010 |
| `backend/adapters/ai` | 两类协议 → 统一 `AIResult` / `AIError` | US-005 |
| `backend/core` | 配置与启动自检、AES 加密、Argon2id 口令哈希、日志脱敏、错误码 | 全部 |
| `backend/db` | ORM 模型、双方言迁移、仓储、连接池 | 全部 |

**依赖方向**：`api → services → adapters/repositories`；`adapters` 不反向依赖 `api`；`ai_gateway` 是唯一允许调用外部 AI 的模块（BG-01）。后续域通过 `services` 的进程内接口（`ai.complete`、`sessions.create/append_event`、`artifacts.save`）接入；签名已冻结（ADR-041），参数类型由 tech-design 展开并保持向后兼容。

### 关键架构约定

- **固定请求路径**：项目 → 会话（选定启用模型）→ 输入事件 → `ai.complete` → 成功/失败 AiCallRecord + 时间线事件；入口占位页不创建会话、不调用模型（AC-002-2）。
- **事务边界**：外部 AI 调用与文件写入都不在数据库写事务内；调用前只做只读校验，结果单事务写入记录与事件。
- **AiCallRecord 生命周期**：发起前插入 `running`，结束更新为 `success / failed / timeout`；进程启动时把遗留 `running` 归并为 `failed`（错误码 `interrupted`），保证 BG-03「失败 100% 有记录」。
- **并发**：单进程 asyncio；AI 调用并发上限可配置（默认 4），超时预算 120s/次、最多 2 次尝试。
- **安全边界**：密钥只在 `core.crypto` 解密、仅在适配器内使用；任何 API schema 不含 `apiKey` 字段（写请求除外），日志出口过滤器统一替换 `sk-*` 与 Authorization。
- **接口风格**：REST `/api/v1`，JSON；错误 `{code, message, details[], requestId}`；列表统一分页参数（`limit` / `cursor`）。
- **认证前置**：除 `/api/v1/auth/login`、`/login` 与静态资源外，所有 `/api/v1` 接口经统一依赖校验 Cookie；HTML 导航无有效会话时 302 到 `/login`；未认证接口返回 401 且不含任何业务字段。容器健康检查以「请求受保护接口得到 401」判定进程存活，不新增匿名端点。
- **会话刷新**：命中有效会话即写 `last_seen_at = now()`；判定 `now - last_seen_at > 8h` 即失效（无绝对上限），登出/轮换写 `revoked_at` 后立即失效。
- **写事务边界（MySQL 版）**：外部 AI 调用与文件写入仍不在事务内；登录失败计数在同一事务内 `SELECT … FOR UPDATE` 后更新，避免并发丢计数。
- **双方言纪律**：新表/新列必须同时通过 SQLite 与 MySQL 的迁移与用例；禁止写方言专属 DDL、`ON DUPLICATE KEY`、`NOW()`、区分大小写的唯一约束；评审把「只在一种方言跑过」视为缺陷。
- **数据目录**：`AW_DATA_DIR` 只承载制品、删除中转与开发用 SQLite 文件；生产库数据在 MySQL 卷内，两者备份方式不同（ADR-019）。知识库原文目录与备份扩展已随 spec 迁出。
- **对外契约冻结**：`sessions.create` / `sessions.append_event` / `artifacts.save` / `AiGateway.complete` 的名称与语义不得改；新 spec 只调用（ADR-041）。

### 受影响的既有决策（原文保留，结论更新）

| 既有条目 | 影响 | 处理 |
|---------|------|------|
| ADR-003 数据库（SQLite 单文件） | 生产库改为 MySQL | 由 ADR-015 / ADR-016 取代，原文不动 |
| ADR-008 部署与网络绑定 | 部署形态改为 compose + 外接 MySQL；有登录后暴露面收敛方式变化 | 由 ADR-027 / ADR-028 取代，原文不动 |
| ADR-004 / ADR-005 | 不变 | AI 出口与 `AW_ENCRYPTION_KEY` 策略沿用；新增 `AW_ADMIN_PASSWORD` 与登录会话，与其正交 |
| ADR-006 制品存储 | `AW_DATA_DIR` 语义收窄（不再含生产库），仍按 `sessions/<sessionId>/` 隔离 | 由 ADR-019 细化，决策不变 |
| ADR-019 备份范围 | 备份覆盖制品目录与开发/测试 SQLite，恢复顺序先库后文件 | 维持原口径；知识库目录扩展已迁出 |
| ADR-012 状态审计 actor | 登录后仍为单账号 | 保持 `local-user` / `system`，payload 结构不变 |
| ADR-014 不做分享 | 决策不变；原「与无登录冲突」的理由已过时 | 理由更新为「范围与优先级」，不新增 ADR |
| RISK-004 / RISK-010 | SQLite 写锁、无鉴权暴露 | 风险登记表中改写：RISK-004 降级为开发/测试路径；RISK-010 由登录 + 绑定策略缓解 |

### 交互阶段遗留问题结论（5 项）

| # | 问题 | 结论 | 归属 |
|---|------|------|------|
| 1 | 是否持久化完整请求/响应正文 | **不存完整请求正文**：存 `prompt_digest`（sha256）+ `prompt_preview`（前 200 字符）+ `prompt_char_count`；**响应正文存全文** `result_text`（受 max_tokens 约束）。不存原始 HTTP 报文、头、密钥。保留策略随会话永久保留、随会话级联删除。 | 本阶段决定 |
| 2 | 结果文本存储形态 | 存 AiCallRecord 的 `result_text` TEXT + `result_format`（本期固定 `text`，预留 `json` 供后续域结构化输出），**不落为制品**；统一结构块由前端按同一 schema 渲染。 | 本阶段决定 |
| 3 | 状态变更审计字段 | SessionEvent（type=`status_change`）payload 存 `{from, to, actor, at, reason}`；单用户自托管下 `actor` 取 `local-user`（用户操作）或 `system`（未捕获失败/启动归并）；不单独建审计表。 | 本阶段决定 |
| 4 | 制品预览/下载接口与范围 | `GET /api/v1/artifacts/{id}`（元数据）与 `GET /api/v1/artifacts/{id}/content?mode=inline\|download[&max_bytes=262144]`；服务端按扩展名白名单映射 Content-Type（不接受客户端声明），`X-Content-Type-Options: nosniff`，inline 仅用于纯文本与 JSON，前端按纯文本转义渲染；下载提供完整文件（≤10MB）。 | 本阶段决定 |
| 5 | 跨会话导出 / 只读分享 | **本期不做**：单用户、`/calls` 已有筛选与展开核对；分享需新增只读令牌与匿名访问路径，属于新安全面且不在本期范围。记入扩展计划，若确认需要则作为新需求立项。 | 本阶段决定（不纳入范围） |

> 上述 1–5 项按默认结论定稿：2026-11-17 19:49 用户确认技术栈（STK-001~004 全 A）时未提出异议，视为「用户未反对，采用默认」，已固化到 ADR-010 ~ ADR-014。
>
> **已闭环**：US-011 登录页缺口按 OQ-ARCH-03 方案 B 处理——interaction-design 已回补登录页线框并随该阶段确认；tech-design 直接沿用其线框与 Design Tokens，不再另出登录页设计，也不再保留「tech-design 自行出登录页」的待定项。
>
> **知识库页面已迁出**：US-012 ~ US-016 的知识库列表、导入、浏览检索、详情、版本与注入面板原已由 interaction-design 出稿确认（`docs/demo.html` Playwright 43 项断言通过），现随 spec 拆分迁出至 `specs/knowledge-base_20261117205011`，本 spec 不再包含。

## spec 拆分与对外契约（2026-11-17）

本文件原有一节「知识库架构设计」（US-012 ~ US-016，ADR-029 ~ ADR-040）。2026-11-17 因 spec 拆分整体迁出至 `specs/knowledge-base_20261117205011`，技术原文（表结构、索引、`index.json` 解析契约、注入组装签名、API 契约、检索方案、限额）见其 `_handoff/from-tech-arch.md`。本 spec 不再包含 `knowledge_bases` / `knowledge_entries` 表、知识库解析/检索/注入服务与相关端点。

拆分后冻结的对外契约与 repo-integration 复用点见 ADR-041：

```python
# 三个进程内签名：名称与语义冻结，新 spec 只调用、不修改（参数类型由 tech-design 展开）
sessions.create(...)          # 创建会话：项目、入口、标题、模型为硬前置
sessions.append_event(...)    # 追加 SessionEvent；业务域不直接写事件表
artifacts.save(...)           # 保存会话制品：上传校验、服务端命名、落盘 sessions/<sessionId>/

async def complete(session_id: str, model_id: str, prepared: str, *,
                   temperature: float | None = None,
                   max_tokens: int | None = None) -> AIResult
```

- `AiGateway.complete` 仍是唯一模型出口；外部调用、超时 120s、网络错误与 5xx 重试 1 次、`retryCount` 入库、AiCallRecord 生命周期都在这里收口。
- `sessions.*` / `artifacts.*` 的数据库与文件副作用遵循本 spec 的事务边界；新 spec 复用这些签名时不新增凭据读取或 HTTP 客户端。
- repo-integration 复用：AES-256-GCM 凭证加密与掩码、错误体 `{code, message, details[], requestId}`、`limit` + `cursor` 分页、`require_session` 认证前置、`project_context` 外键归属、双方言纪律、pytest 门禁（ADR-041）。

## 风险登记表

| ID | 风险 | 类别 | 影响 | 概率 | 评分 | 缓解措施 |
|----|------|------|------|------|------|---------|
| RISK-001 | 明文 API 密钥经响应/日志/错误信息/前端缓存泄露 | 安全 | 高 | 中 | 🔴 Critical | 响应 schema 永不含密钥；统一掩码函数；日志脱敏过滤器（Authorization、`sk-`）；禁用请求体日志；测试断言响应/日志无明文；默认仅绑定 127.0.0.1 |
| RISK-002 | 两类协议与各家「OpenAI 兼容」实现差异（错误体、usage、模型列表、必填字段）导致适配失败 | 集成 | 高 | 中 | 🔴 Critical | 薄适配层 + 契约测试夹具（成功/401/429/5xx/超时）；连接测试用最小请求；错误映射为固定错误码；不在 UI 暴露厂商差异 |
| RISK-003 | 120s 超时 + 1 次重试导致单次最长 ~240s，用户等待、连接与工作线程被占满 | 技术 | 中 | 中 | 🟡 Medium | 异步 SDK 调用；并发上限 + 排队提示；前端请求超时略大于服务端；调用中禁用重复提交；结果与失败都落时间线 |
| RISK-004 | 开发/测试走 SQLite 时并发写触发 `database is locked`，用例偶发失败 | 技术 | 中 | 中 | 🟡 Medium | 生产 MySQL 不受影响；外部调用不在事务内；SQLite 用 `NullPool` + WAL + `busy_timeout=5000`；测试用临时文件库串行写；偶发失败按缺陷处理而不是重跑 |
| RISK-005 | 上传路径穿越、类型伪装或大小限制绕过 | 安全 | 高 | 中 | 🔴 Critical | 服务端扩展名白名单 + 逐文件/数量上限；服务端生成存储名；解析后路径必须位于会话目录内；不执行、不渲染 HTML；下载加 `nosniff` |
| RISK-006 | 删除会话时文件或记录残留，违反「级联清理且不可见」 | 技术 | 中 | 中 | 🟡 Medium | 先原子重命名会话目录到 `.trash/<id>`，DB 事务删除成功后清理目录；失败保留 trash 并记日志；提供启动时孤儿扫描 |
| RISK-007 | 依赖版本漂移（SDK 大版本、TS 7 / Vite 8 生态）导致构建或行为变化 | 技术 | 中 | 中 | 🟡 Medium | `uv.lock` / `package-lock.json` 锁定精确版本；CI 用 frozen 安装；升级单独任务并跑全量 TC |
| RISK-008 | 自定义暗色 token 与组件样式冲突，对比度或焦点态回归 | 技术 | 低 | 中 | 🟢 Low | 只用 token 变量与 CSS Modules；不引入带主题的组件库；用 axe/对比度检查与 9 项交互回归覆盖 |
| RISK-009 | 范围蔓延（4 个后续域、导出分享、流式）挤压基座质量 | 范围 | 高 | 中 | 🔴 Critical | 本 spec 严格按 In Scope；进程内接口先定契约后实现；新能力走新 `aw-start` |
| RISK-010 | 登录被绕过或远程部署未加 TLS，导致口令/令牌在传输中或未认证路径泄露 | 安全 | 高 | 中 | 🔴 Critical | 路由级统一鉴权（白名单仅登录接口）；HttpOnly + SameSite=Lax + HTTPS 下 Secure；`AW_ALLOW_REMOTE=1` 显式开关；文档与 `.env.example` 要求 TLS 反代并配置 `AW_PUBLIC_ORIGIN`；未认证与 401 用例列入 TC |
| RISK-011 | 双方言漂移：迁移或行为只在一种方言通过（JSON、大小写、索引长度、DDL 事务） | 技术 | 高 | 中 | 🔴 Critical | 只允许 SQLAlchemy 通用类型与差异清单内的写法；CI 两个 job 从空库迁移到 head 后跑全量用例；本地 `AW_TEST_DATABASE_URL` 复跑；方言差异写进评审清单 |
| RISK-012 | 管理员口令或会话令牌被爆破、离线破解或泄露 | 安全 | 高 | 中 | 🔴 Critical | Argon2id（64 MiB/t=3/p=4）；会话令牌仅以其哈希入库；5 次失败锁 5 分钟；统一失败提示；日志与响应脱敏测试；`AW_ADMIN_PASSWORD` 按密钥管理 |
| RISK-013 | CSRF：跨站构造写请求携带会话 Cookie | 安全 | 高 | 低 | 🟡 Medium | SameSite=Lax + Origin/Referer 校验（缺失即拒绝）+ 写接口 JSON content-type；测试覆盖缺 Origin / 错 Origin / 跨站 POST |
| RISK-014 | 反向代理下来源 IP 识别错误，导致误锁正常用户或锁不住攻击者 | 技术 | 中 | 中 | 🟡 Medium | 默认不信任 `X-Forwarded-For`（取直连对端）；仅 `AW_TRUST_PROXY=1` 时取首跳；compose 默认直连；文档写明代理场景的两条配置路径 |
| RISK-015 | MySQL 运维面出错：未建库、字符集不是 utf8mb4、迁移权限不足、备份缺失导致不可恢复 | 运维 | 高 | 中 | 🟡 Medium | 启动自检（连通/版本/口令）；compose 固定 utf8mb4；文档写明迁移所需最小权限；`scripts/backup.sh` + 恢复演练作为验收项 |
| RISK-016 | 登录页没有交互设计稿，视觉与交互偏离已确认的设计系统 | 范围 | 中 | 高 | 🟢 Low | 已闭环：OQ-ARCH-03 按 B，interaction-design 已回补登录页线框并确认；tech-design 直接沿用 |

### Critical 风险应急预案

- **RISK-001**：若脱敏仍出现泄露（例如新增厂商错误体回显密钥），立即在 `AIError` 构造处统一截断并加回归测试；发布前用脚本扫描日志与 API 响应快照；必要时禁用该厂商的原始错误透传，仅保留错误码与 HTTP 状态。
- **RISK-002**：若某「OpenAI 兼容」厂商无法通过最小请求，降级为「连接测试不校验模型列表、只校验鉴权与端点可达」，并把差异写入提供商备注；适配层保留逐厂商开关，但不做专属适配（AMB-003 A 边界）。
- **RISK-005**：若发现绕过（如大小写扩展名、双扩展名），立即改为「读取文件头 + 扩展名双重校验」，并对已上传制品做一次性扫描与隔离。
- **RISK-009**：范围冲突时按 In Scope 表删减 P1（调用记录查询界面、参数覆盖、筛选），保留 P0 基座能力；被删项记录到扩展计划。
- **RISK-011**：若某次迁移只在一种方言通过，立即撤销该 revision（未发布时直接改），补齐方言差异处理与两方言的冒烟用例后再提交；已发布时新增修正 revision，不修改历史迁移。
- **RISK-012**：若怀疑口令泄露，按「改 `AW_ADMIN_PASSWORD` + 重启」轮换，并吊销全部 `login_session`（`revoked_at = now()`）；若怀疑库泄露，同时轮换 `AW_ENCRYPTION_KEY` 并重新登记提供商密钥。
- **RISK-015**：若备份不可用，按「最近可用的 MySQL 备份 + 制品目录」恢复，恢复后核对制品数量与 `alembic_version`；密钥丢失时提供商密钥只能重新登记（ADR-005 既定）。

## 扩展计划

| 阶段 | 用户规模 | 架构变化 |
|------|---------|---------|
| 本期（workbench-core） | 1 人、远程部署 | docker-compose：FastAPI + MySQL 8.4 + 制品卷；单用户登录；SQLite 仅开发/测试 |
| 后续 4 域接入 | 同上 | 复用 `ai.complete` / 会话 / 制品进程内契约；新增域不新增凭据读取与 HTTP 客户端 |
| 多用户 / 远程运维 | 2–10 人 | 账号表与角色（`owner` 字段启用）、会话表复用；TLS 反代与审计；MySQL 读写分离可选 |
| 规模化 | >10 人或大数据量 | 制品转对象存储、AI 调用队列化、会话刷新写放大改为节流、MySQL 主从 |

> 未安装任何 AlonWorkflow pack（`.aw/install.json` 的 `packs` 为空），未套用 pack 专属约定；如需 `.NET`/`React` 等 pack 约定，可 `alonwf pack add <pack>` 后重跑本阶段。
