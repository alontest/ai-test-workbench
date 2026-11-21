# Technical Design — Design（knowledge-base）

> 阶段：tech-arch（步骤 1–3.5）。上游：`requirements-analysis/docs/context.md`（5 US / 24 AC / 7 EARS，已确认）、`interaction-design/docs/context.md`（已确认，2026-11-18 11:12:30）、`_handoff/from-tech-arch.md`（拆分前草稿，按当前需求重新论证）。
> 架构决策：`docs/architecture-decisions.md`（ADR-101 ~ ADR-118，architecture-locked）。跨 spec 扩展已拍板（`answers.md` 2026-11-18 11:23:18）：OQ-ARCH-101 A（core 落库扩展）、102 A（`complete` 追加可选 `injection`）、103 B（复用 core 的 `/ai/complete` 入口，不新增 calls 端点）。

## 技术选型

### 技术栈总览

> 技术栈已由用户与 workbench-core 锁定「与 core 一致」，本阶段**不重新选型**，只记录继承关系与知识库侧受影响的层。版本以 core 的 `pyproject.toml` / `uv.lock` / `package-lock.json` 为唯一真源。

| 层次 | 选型 | 版本 | 来源 | 理由摘要 |
|------|------|------|------|---------|
| 后端运行时 | Python | 3.12+（core 容器为 `python:3.14-slim` 系） | 已有（core） | 与 core 同进程，不引入第二运行时 |
| 后端框架 | FastAPI + Uvicorn（单进程） | fastapi 0.163.1 / uvicorn 0.54.0 | 已有（core） | 复用 `require_session`、错误处理器、分页依赖 |
| 数据校验 | Pydantic 2 | 2.14.3 | 已有（core） | 请求/响应与 multipart 元数据校验 |
| ORM / 迁移 | SQLAlchemy 2.1 + Alembic | 2.1.9 / 1.20.1 | 已有（core） | 两张新表 + 一次 core 表扩展，双方言同构 |
| 数据库 | MySQL 8.4（生产）/ SQLite（开发测试） | mysql:8.4.13 / aiosqlite 0.22.1 | 已有（core） | core ADR-015；知识库表必须双方言通过 |
| 文件存储 | 本地文件系统 `$AW_DATA_DIR/knowledge-bases/` | — | 已有（core 的 `AW_DATA_DIR` 约定） | 与 `sessions/` 平级、互不跨根；不引入对象存储 |
| 上传解析 | `python-multipart` | 0.0.34 | 已有（core） | 复用制品上传依赖；`index.json` 用标准库 `json` |
| 前端框架 | React 19 + TypeScript + Vite + React Router | react 19.3.1 / typescript 7.0.2 / vite 8.3.8 / react-router 8.5.1 | 已有（core） | 复用 AppShell、AuthGate 与同源托管 |
| 前端数据 | TanStack Query | 5.107.2 | 已有（core） | 列表三态、preview 与选择器缓存 |
| 前端 UI 原语 | CSS 变量 + CSS Modules + Radix Primitives | radix-ui 1.8.1 | 已有（core） | 直接落地 interaction-design 的 token；对话框焦点管理 |
| 测试 | pytest + httpx / Vitest + Testing Library / Playwright | core 锁定版本（vitest 5.1.0 / @testing-library/react 16.3.3 / @playwright/test 1.65.1） | 已有（core） | 双方言后端用例 + 组件状态 + 关键流程 E2E |

### 详细决策

#### 决策 1：继承技术栈，不引入任何新的解析/检索依赖

- **选择**：全部继承 core；`index.json` 用标准库 `json`，正文匹配用正则逐行扫描，检索用 SQLAlchemy `LIKE`。
- **理由**：`index.json` 结构与正文格式由本地本体工具固定，解析逻辑是纯函数级复杂度；引入 `orjson` / `ijson` / `markdown-it-py` 只会增加依赖与许可证审查面，与「单库 ≤100MB、条目 ≤20,000」的规模不匹配。
- **备选方案**：`ijson` 流式解析（本阶段不需要，`index.json` ≤20MB 可直接 `json.loads`）；`markdown-it-py` 渲染正文（明确不做 HTML 渲染，见 ADR-114）。
- **权衡**：接受 20MB JSON 一次性读入内存的峰值（单用户、单请求），换取更简单的解析护栏与可直接单测的纯函数。

#### 决策 2：知识库作为同一进程内的垂直模块，不独立部署

- **选择**：`src/workbench/knowledge/`（解析）+ `src/workbench/services/knowledge/`（服务）+ `api/v1/knowledge*.py` + `frontend/src/knowledge/`。
- **理由**：与 core 的 `AiGateway`、`sessions.append_event`、`project_context` 是进程内调用；独立部署会把进程内契约退化成 HTTP（违反 core ADR-041「不新增 HTTP 客户端」）并复制登录态。
- **备选方案**：独立服务 + 内网 HTTP；被否，单用户场景无收益且引入网络失败面。
- **权衡**：与 core 同发布单元；core 的迁移与知识库迁移在同一条 Alembic 链上，需要协调编号（见 ADR-103、约束条件）。

#### 决策 3：文件存储复用 `AW_DATA_DIR`，不进入制品通道

- **选择**：`$AW_DATA_DIR/knowledge-bases/<kbId>/` + `.staging/` + `.trash/`；不复用 `artifacts.save` 与 `sessions/<sessionId>/`。
- **理由**：知识库是项目级、跨会话、可删除的独立实体，生命周期与制品不同；`artifacts.save` 绑定会话与 10MB/会话级限额，语义不匹配。`AW_DATA_DIR` 的备份与恢复语义可复用（core ADR-019）。
- **备选方案**：全部塞进制品目录；被否，删除与备份粒度会互相污染。
- **权衡**：`scripts/backup.sh` 需扩展覆盖新根；恢复顺序与核对方式写进运维说明。

#### 决策 4：调用入口唯一——core 的 `/ai/complete`，本 spec 只提供进程内注入服务

- **选择**：不新增 `/knowledge-injection/calls` 端点。core 的 `POST /api/v1/sessions/{sessionId}/ai/complete` 请求体追加可选 `knowledgeRefs: [{kbId, code}]` 与 `confirmInvalidCodes: string[]`；core 在调用 `AiGateway` 前调用本 spec 的 `KnowledgeInjectionService.prepare_for_call(...)` 完成失效重校验、注入块组装与字符预算，再用返回的 `PreparedInjection` 调 `AiGateway.complete(..., injection=snapshot)`。知识库模块不直接访问上游模型、不读取凭据。
- **理由**：`AiGateway` 已收口超时、重试、并发、AiCallRecord 生命周期与最终预算校验；会话页只有一条调用路径，避免「勾选知识库走一个端点、未勾选走另一个」的分叉与两套错误展示。用户已按 OQ-ARCH-103 B 拍板。
- **备选方案**：本 spec 新增 `knowledge-injection/calls` 端点（原推荐 A）；被否，会让会话页出现两条调用路径，且调用入口不唯一。
- **权衡**：core 的 `/ai/complete` 请求 schema、错误码与前端调用路径需要同步扩展；本 spec 的注入服务要作为进程内契约被 core 依赖，签名与域错误必须在 tech-design 冻结。

## 系统架构

### 分层说明

| 层次 | 职责 | 技术 |
|------|------|------|
| 前端展示层 | 知识库列表/导入/浏览/详情、注入选择器、字符预算、阻塞确认、项目摘要 | React 19 + TS + TanStack Query + CSS Modules/Radix；复用 AppShell 与设计 token |
| API 层 | 路由、请求/响应 schema、认证、Origin 校验、错误映射、分页 | FastAPI + Pydantic 2；`require_session` |
| 领域服务层 | 导入编排、检索/详情的查询组装、注入预览/组装/失效重校验、版本与删除生命周期 | `services/knowledge/*`（纯业务，无 HTTP 依赖） |
| 解析与内容层 | `index.json` 解析护栏、编号前缀映射、正文匹配、摘要归一化 | `src/workbench/knowledge/index_parser.py`、`body_matcher.py`（纯函数） |
| 持久化层 | 两张新表、索引、双方言映射（本 spec 迁移从 `0007` 起）；`ai_call_record` 扩展列由 core 的 `0006` 创建，本 spec 只读、经 `injection` 参数交由 gateway 写入 | SQLAlchemy 2.1 + Alembic |
| 文件存储层 | 暂存、原子 rename、服务端命名、包含校验、trash 与孤儿扫描 | 本地文件系统 + `pathlib` |
| core 集成层 | 模型调用、会话事件、项目归属、登录态、错误体/分页约定；core 反向调用本 spec 的 `prepare_for_call` | `AiGateway.complete`、`sessions.append_event`、`project_context` 只读；`KnowledgeInjectionService.prepare_for_call` |

### 模块划分

| 模块 | 职责 | 关联 US |
|------|------|---------|
| 导入模块（`knowledge/import`） | 文件白名单/大小/数量/合计校验、流式落盘、`index.json` 与正文解析、跳过报告、整体回滚、同名版本化 | US-012 |
| 浏览检索模块（`knowledge/browse`） | 项目/知识库/版本/类型筛选，编号前缀/完整编号/关键词检索，详情与邻居跳转，正文缺失降级 | US-013 |
| 注入模块（`knowledge/injection`） | 条目取数与组装、固定模板、Unicode 字符预算、preview、失效集重校验、阻塞确认；向 core 提供 `prepare_for_call` 进程内接口，不自行发起模型调用 | US-014 |
| 生命周期模块（`knowledge/lifecycle`） | 新鲜度与冲突判定、版本取代、删除逻辑库与文件、trash/孤儿清理、`kbDeleted` 判定 | US-015、US-016 |
| 前端知识库模块（`frontend/src/knowledge`） | 4 条路由页面 + 17 个组件；token 复用，不新增样式变量 | US-012 ~ US-016 |
| core 嵌入点 | 会话页注入面板 3 个组件；项目上下文页 `data-mount="knowledge-summary"` 的 `ProjectKnowledgeSummary` | US-014、US-012 |

### 关键数据流

**导入**：`POST /knowledge-bases`（multipart）→ API 层逐文件校验（扩展名/大小/数量/合计）→ 流式写 `.staging/<token>` → `index_parser` 解析 `index.json`（结构/护栏/前缀映射/跳过报告）→ `body_matcher` 匹配 `.md` → 取同名逻辑库行锁与 `version` → `rename` 到 `knowledge-bases/<kbId>` → 单事务写 KB 行 + 条目（分块 `executemany`）→ 提交并返回 201 + 导入报告；任一步失败回滚并删目录。同名重导把旧版本置 `superseded`，返回 `versionBumped=true`。

**浏览/检索**：`GET /knowledge-entries`（或库内快捷路径）→ 查询条件收敛到当前版本 → `LIKE` 检索 + 排序分页 → 一次聚合 `countsByType` → 列表返回徽标（`superseded` / `bodyMissing` / `freshness` / `hasConflict`）。详情按 `entryId` 取条目 + 批量查冲突来源 + 邻居编号解析（同项目、可选跳转）。

**注入**：会话页选择器 → `GET .../knowledge-injection/candidates`（当前版本 + 徽标）→ 勾选后前端按固定模板即时估算 → `POST .../preview` 取权威分段字数与失效项 → 用户点「发起调用」→ **core 的 `POST /api/v1/sessions/{sessionId}/ai/complete`**（请求体带 `prompt`、`knowledgeRefs`、可选 `confirmInvalidCodes`）：
1. core 在调用网关前调用本 spec 的 `KnowledgeInjectionService.prepare_for_call(...)`；服务重算有效集 / 失效集（已删除 / 已被取代 / 不存在）；
2. 失效集非空且 `confirmInvalidCodes` 不完全相等 → 服务抛 `knowledge_invalid_entries`，core 映射 409（不调用、不写记录）；
3. 确认后服务组装注入块 → `total_chars` 超 `AW_PROMPT_MAX_CHARS` → 抛 `prompt_budget_exceeded`，core 映射 400（不截断）；
4. 通过 → core 调 `AiGateway.complete(prepared, injection=snapshot)`（唯一模型出口；最终预算与 AiCallRecord 生命周期在 core）；
5. gateway 同事务写注入快照（core `0006` 扩展列 + `knowledge_injection` 事件），只记知识库/版本/编号/字符数，不记正文。

**删除**：`DELETE /knowledge-bases/{kbId}` → 查逻辑库全部版本 → 事务删 `knowledge_base`（条目级联）→ 提交 → 目录 rename 进 `.trash/` 并清理；历史会话/事件/调用记录不动，读取时按 `kbId` 左连接标「知识库已删除」。

> 涉及本体：ENT-C10 知识库、ENT-C11 知识库条目、TERM-C12 知识注入、TERM-C13 知识库版本、BR-C15 ~ BR-C20、BP-C5 ~ BP-C8（来源 `_shared/ontology/`；本 spec 无 `ontology-slices/tech-arch.md`，项目尚无 `ontology-work/views/index.json`）。模块划分与对象归属沿用切片，不新增模块或跨模块依赖。

## 风险登记表

> 编号从 RISK-101 起，避免与 core 的 RISK-001 ~ RISK-016 冲突。评分矩阵：影响 × 概率 → 🔴 Critical / 🟡 Medium / 🟢 Low。

| ID | 风险 | 类别 | 影响 | 概率 | 评分 | 缓解措施 |
|----|------|------|------|------|------|---------|
| RISK-101 | 知识库正文/摘要/字段值经日志、错误响应或调用记录泄露 | 安全 | 高 | 中 | 🔴 Critical | 内容按不可信输入处理；日志与错误只允许 id/编号/文件名/行号/字符数/固定原因码；解析器异常不透传；`AiCallRecord` 不存正文；用例断言日志与错误体无正文片段 |
| RISK-102 | 导入路径穿越、巨型 JSON/深层嵌套/`NaN` 导致越权写盘、内存或 CPU 耗尽 | 安全 | 高 | 中 | 🔴 Critical | 客户端文件名不参与路径 + 服务端 sha256 命名 + `resolve()` 包含校验；扩展名白名单 + UTF-8 校验；深度 32、条目 20,000、单文件/合计上限；禁 `NaN/Infinity`、捕获 `RecursionError`；失败整包回滚 |
| RISK-103 | 导入半成品：文件已落盘但 DB 回滚，或 DB 提交但目录缺失 | 技术 | 中 | 中 | 🟡 Medium | 固定顺序 staging → rename → 单事务写库；失败删目录；启动扫描清理「有目录无行」；`manifest.json` 支持备份核对；用例在各阶段注入失败 |
| RISK-104 | 注入预算误算或绕过（前端估算、各域自行拼提示） | 技术 | 中 | 中 | 🟡 Medium | 唯一组装入口 `KnowledgeInjectionService` + 唯一最终校验点 `AiGateway`；preview 与 prepare 同实现；字符口径统一 Unicode 码点；超限分段报数；边界用例覆盖标题/分隔符 |
| RISK-105 | 双方言漂移：`TEXT` 静默截断、JSON 列不能建索引、可空唯一索引语义、`LIKE` 大小写与扫描性能、CHECK 变更在 SQLite 需重建表 | 技术 | 高 | 中 | 🔴 Critical | 大文本强制 `MEDIUMTEXT` 变体；`sa.JSON` 不建索引；`current_flag` 可空唯一索引两方言各跑迁移与用例；`LIKE` 转义并限制范围；`session_event.type` CHECK 变更用 Alembic batch；CI 两方言从空库到 head |
| RISK-106 | 版本取代/删除语义混淆，用户把旧版本条目当作现行结论注入 | 范围 | 中 | 中 | 🟡 Medium | 注入块带知识库名 + 版本 + 生成时间；默认只展示当前版本；旧版本只读并标「已被 vN 取代」；按 ADR-110 在调用前剔除已被取代条目并列出编号 |
| RISK-107 | 关键词检索 `LIKE` 全表扫描，大库下响应变慢 | 技术 | 中 | 中 | 🟡 Medium | 默认只搜当前版本；编号查询先走 `code_key` 索引；`q` 1..100；升级门禁（>50,000 条或 p95 >500ms）触发 FULLTEXT/FTS5；性能用例记录基线 |
| RISK-108 | 跨 spec 扩展实现漂移：core 的 `0006` 迁移漏列、`session_event.type` 未扩 CHECK、`complete` 的 `injection` 参数语义不一致 | 集成 | 高 | 中 | 🔴 Critical | 已按 OQ-ARCH-101 A / 102 A 定归属；合并前跑 core 的契约测试（列存在、CHECK 接受 `knowledge_injection`、`injection=None` 行为不变）；启动自检校验列；迁移顺序固定 core `0006` → 本 spec `0007`；不实现「回填」退化路径，未就绪则不发布 |
| RISK-109 | 阻塞确认被绕过或确认过期：preview 后条目失效，用户确认的集合与实际不一致 | 技术 | 中 | 中 | 🟡 Medium | core 在 `/ai/complete` 调用前由 `prepare_for_call` 重算失效集，`confirmInvalidCodes` 必须完全相等；不一致返回 409 并给新清单；确认后有效集为空则拒绝调用；覆盖「确认 → 再取代 → 409」用例 |
| RISK-110 | 大文件/大库导致请求内存峰值或超时 | 技术 | 中 | 中 | 🟡 Medium | 上传流式写盘、边写边校验；条目分块 `executemany`；解析前先校验字节上限；单请求不缓存全文到多份（解析后及时释放）；超时/内存用例用小值覆盖 |
| RISK-111 | 并发导入同名知识库导致版本号冲突或唯一约束报错 | 技术 | 低 | 中 | 🟢 Low | 行锁取 `version`；唯一冲突重试 1 次再 409；前端对 409 给出「稍后重试」提示 |
| RISK-112 | 删除时数据库已删但文件清理失败，留下孤儿目录 | 运维 | 低 | 中 | 🟢 Low | 先 DB 后文件；失败 rename 进 `.trash` 并记日志；启动扫描清理 trash；删除确认框说明不可撤销 |
| RISK-113 | 前端字符计数与后端模板漂移，用户看到「未超限」但服务端拒绝 | 技术 | 中 | 中 | 🟡 Medium | 模板与常量集中在服务端并导出为共享契约文档；前端只做即时估算，调用前以 preview 为准；边界用例同时断言两端数字 |

### Critical 风险应急预案

- **RISK-101**：发现正文进入日志/错误体时，立即在日志出口与错误构造处加字段白名单，禁止透传解析器异常原文；对已产生日志做一次性扫描；受影响知识库可要求重导。
- **RISK-102**：出现越界写盘或资源耗尽时，立即下线导入入口，修正包含校验/护栏后重跑安全用例；已上传目录按 `manifest.json` 审计并隔离。
- **RISK-105**：某方言出现截断、唯一索引不生效或 CHECK 变更失败时，停止发布并新增修正迁移；已截断数据按原文重导（不修改历史迁移）；SQLite 用 batch 重建表确保 CHECK 生效。
- **RISK-108**：若 core 的 `0006` 或 `injection` 参数未按契约落地，暂停本 spec 的注入相关验收（导入/浏览/删除不受影响），以 core 契约为准修正后重跑；**不做**静默降级或「回填」替代，因为用户已选择 A 且 AC-014-2 要求原子留痕。

## 扩展计划

| 阶段 | 用户规模 | 架构变化 |
|------|---------|---------|
| 本期（知识库闭环） | 1 人、单进程 | MySQL/SQLite 两张新表；本地文件根；`LIKE` 检索；进程内注入组装；人工上传 `index.json` + `.md` |
| 检索规模化 | 单项目多库、检索变慢 | `LIKE` 升级为 MySQL FULLTEXT（ngram）/ SQLite FTS5，或引入向量检索；HTTP 契约与 `content_digest` 不变，只替换服务层实现 |
| 知识库自动化 | 上游工具直连 | `ontology-builder` 通过进程内接口推送 `index.json` + `.md`，替代手工上传；复用同一解析/版本/报告契约；新增鉴权与幂等键 |
| 多用户 / 多副本 | 2–10 人 | 知识库归属与删除审计接入账号体系；文件存储转对象存储；导入改为后台任务队列，避免长请求占用 |

> 本阶段产出于 AlonWorkflow 时期，当时未安装任何 pack、未套用 pack 专属约定；该工作流已于 2026-11-19 整体移除，本说明仅作历史留痕。
