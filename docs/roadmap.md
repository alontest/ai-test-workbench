# Vigil · 鸮巡 — 项目进度与排期

> 基线：2026-11-20 15:00（Asia/Shanghai），分支 `feat/batch-b-backend` @ `987c919`。
> 本文是接手时的现状快照与排期判断，不替代 `specs/` 下的阶段产物。所有估算都是人日口径（1 人日 ≈ 8h），依据是 core 已交付任务的实际密度。
> 2026-11-23 品牌与配置统一说明：项目已统一更名为 `vigil-workbench`，后端源码目录迁移至 `src/vigil_workbench/`，环境变量 `AW_*` / `AW_KB_*` 已切换为 `VIGIL_*` / `VIGIL_KB_*` / `VIGIL_ENCRYPTION_KEY`，Cookie 切换为 `vigil_session`，默认库切换为 `vigil.db` / `vigil`。最新环境与命令以 `AGENTS.md` 和 `docs/dev-setup.md` 为准。

## 一、现在到底做到哪了

一句话：**基座（workbench-core）真的做完了并已关闭；知识库和仓库集成只走到「方案定了、代码一行没写」；6 个入口里 6 个都还是占位页。**

| 域 | spec | 阶段 | 代码 | 状态 |
|---|---|---|---|---|
| 工作台基座 `workbench-core` | `ai-test-workbench_20261117184149` | 全部 7 阶段，2026-11-18 16:42 `aw close` | ✅ 已落地 | **已完成** |
| 知识库 `knowledge-base` | `knowledge-base_20261117205011` | intake → requirements → interaction → tech-arch 已确认；tech-design 已写、**tech-tasks 缺失** | ❌ 0 行 | 卡在拆任务 |
| 仓库集成 `repo-integration` | `repo-integration_20261117205011` | intake → requirements → interaction 已确认；tech-arch 锁定；**tech-design 未开始** | ❌ 0 行 | 卡在技术设计 |
| 用例域 `test-case` | 无 | 未立项 | ❌ | 未开始 |
| 诊断域 `diagnosis` | 无 | 未立项 | ❌ | 未开始 |
| 回归清单 `regression-list` | 无 | 未立项 | ❌ | 未开始 |
| 测试报告 `test-report` | 无 | 未立项 | ❌ | 未开始 |
| 本体生成 `ontology-builder` | 无 | 明确「待排期」 | ❌ | 未开始 |

### 代码基线实测

```
后端   src/workbench/        5,580 行   Python 3.12 + FastAPI + SQLAlchemy 2.1 + Alembic
测试   tests/                6,039 行   131 passed（pytest，SQLite）
前端   web/src/              7,624 行   React 19 + TS + Vite + Router 8 + TanStack Query 5
迁移   migrations/versions/  0001 ~ 0006
```

跑通的能力：登录态（Argon2 + Cookie + 失败锁定）→ 建项目 → 配提供商/模型（AES-256-GCM 加密 + 掩码）→ 建会话 → 贴文本/传制品 → 发起调用 → 时间线与调用记录。30 个端点全部实现。

### 一个必须先说明的口径问题

`docs/_shared/domain-map.md` 把 `workbench-core` 标成「✅ 已完成 / 2026-11-18 16:42」，但那是 `aw close` 的时间。当时 `specs/.../technical-design/tasks.md` 头部还挂着「**文档状态：draft — 待用户重新确认**」（因跨 spec 知识库注入扩展 A101/A102/A103 变更）。代码上批次 D（TASK-TD-051~055，含迁移 `0006`）是**已经实现并通过测试的**，只是文档状态没回填。

结论：功能上可信，文档上留了一个 draft 尾巴。建议找时间把 `tasks.md` / `change-spec.md` 的状态改回 confirmed，别让下一个接手的人以为这里还有坑。

## 二、技术方案（一次说清）

### 分层

```
浏览器 ── React 19 SPA（web/src，dist 由后端同源托管）
            │
            ▼
        FastAPI 单进程（src/workbench）
            ├── api/v1/        30 个端点，统一 require_session + 统一错误体
            ├── services/      业务编排
            ├── adapters/ai/   唯一模型出口：AiGateway.complete
            │     ├─ anthropic.py
            │     └─ openai_compatible.py
            ├── adapters/fs/   制品落盘（$AW_DATA_DIR/sessions/<id>/）
            ├── db/models/     SQLAlchemy 2.1 ORM，10 张表
            └── db/repositories/
            │
            ▼
   MySQL 8.4 LTS（生产） / SQLite（开发测试）  —— 同一套 ORM 与 Alembic 迁移
```

### 四条硬约束（后面所有 spec 都不许破）

1. **模型出口唯一**：任何域要调模型，只能走 `AiGateway.complete`，不许自己接 SDK。它统一收口超时（120s）、重试、并发（默认 4）、`AiCallRecord` 生命周期与 200,000 字符预算。
2. **凭证只由基座持有**：加密密钥来自环境变量（32 字节 base64），回显一律掩码，日志一律脱敏。其他域不许读密钥、不许直连供应商。
3. **跨域只走进程内接口**：不跨域读对方数据表。`projectId` / `sessionId` / `kbId` / `repoBindingId` 都只是 ID 引用。
4. **双方言纪律**：SQLite 绿 ≠ MySQL 绿。大文本用 `Text().with_variant(MEDIUMTEXT, "mysql")`，唯一性靠可空 `current_flag` / `active_flag`，CHECK 变更新增迁移不用 batch 改历史迁移。CI 有独立的 MySQL job。

### 两个待建域的设计要点

**知识库**（ADR-101~118，10 个端点，2 张表 `knowledge_base` / `knowledge_entry`）
- 解析 `index.json` + `.md` 正文，用标准库 `json` + 正则切块，不引第三方解析库。
- 注入不是独立调用入口 —— 复用 core 的 `POST /sessions/{id}/ai/complete`，追加可选 `knowledgeRefs`，由 `KnowledgeInjectionService.prepare_for_call()` 在进程内完成组装。**会话页只有一条调用路径**，这是 103 B 拍板的结果。
- 留痕只记知识库 + 版本 + 编号列表 + 字符数，**不复制正文**。
- 迁移必须是 `0007`，`down_revision = 0006`（core 已占 0006）。

**仓库集成**（ADR-201~217，15 个端点，4 张表）
- 只做「元数据 + 按需读单文件」，不克隆、不建索引、不做 Webhook。
- 出站必须用 `httpx.AsyncClient`（`follow_redirects=False`、`max_retries=0`），因为要读 `X-RateLimit-*`、`Link`、`x-total` / `x-page` 这些响应头 —— 这也是否掉官方 SDK 和 `requests` 的原因。
- 文件内容**不落盘、不缓存**，只在响应与内存中存在。
- 同步是请求内完成，总预算 120s，失败保留旧快照；并发靠数据库原子 claim + 20 分钟 TTL。
- 迁移必须是 `0008`，`down_revision = 0007`。

### 原型

三份可交互线框都在 spec 里，直接开浏览器看：

- `specs/ai-test-workbench_20261117184149/interaction-design/docs/demo.html`（101 KB，基座全站）
- `specs/knowledge-base_20261117205011/interaction-design/docs/demo.html`（78 KB，知识库 4 个视图）
- `specs/repo-integration_20261117205011/interaction-design/docs/demo.html`（75 KB，项目上下文页增量面板）

设计基调：Dark-first，CSS 变量 + CSS Modules + Radix Primitives，`docs/design-system.md` 是 token 唯一真源。已过 Playwright 亮/暗双主题检查（各 31/31）。

## 三、排期对比：计划 vs 实际

### core 的实际节奏（唯一可参照的样本）

| 批次 | 内容 | 任务数 | 估算工时 |
|---|---|---|---|
| A | 基座、数据层、冻结契约 | 18 | ~130h |
| B | 最小闭环（登录→建项目→配模型→建会话→调用） | 23 | ~200h |
| C | 调用查询、六入口、交付 | 9 | ~90h |
| D | 跨 spec 知识库注入扩展 | 5 | ~54h |
| 合计 | | **55** | **474h ≈ 59 人日** |

日历上 11-17 立项 → 11-18 16:42 关闭，约 **2 个工作日**。也就是说实际吞吐约 **30 人日/天**（多 agent 并行 + 单人 review）。

这个倍率是全项目的排期锚点：**估算工时 ÷ 25 ≈ 日历天数（带 buffer）。**

### 各域剩余工作量估算

| 域 | 任务数（估） | 估算工时 | 日历天数 | 依据 |
|---|---|---|---|---|
| `knowledge-base` | 12~18 | ~120h（15 人日） | 1~1.5 天 | 2 表 / 10 端点 / 24 AC，约为 core 的 55~65% |
| `repo-integration` | 16~20 | ~170h（21 人日） | 1.5~2 天 | 4 表 / 15 端点 / 36 AC / 5 个供应商适配器，比 KB 重 |
| `test-case` | 待定 | ~150h | 1.5~2 天 | 6 入口里最重的核心域，无 spec |
| `diagnosis` | 待定 | ~180h | 2 天 | 三合一（bug / 日志 / SQL），无 spec |
| `regression-list` | 待定 | ~90h | 1 天 | 依赖 test-case + diagnosis |
| `test-report` | 待定 | ~90h | 1 天 | 依赖前三个 |
| `ontology-builder` | 待定 | ~200h | 2~3 天 | 用户明确「待排期」，可拖到一期之后 |

**一期（让 6 个入口全部 live）的剩余关键路径：KB → repo → test-case → diagnosis → regression-list → test-report ≈ 800h ≈ 100 人日 ≈ 8~10 个日历天**（按当前吞吐）。不含 ontology-builder。

### 当前的真实阻塞

不是工作量，是**决策闭环断了**。三个域同时卡在「文档写了、没人拍板、没人拆任务」：

| 阻塞项 | 卡在哪 | 谁来解决 |
|---|---|---|
| KB tech-tasks 不存在 | tech-design 已确认，任务没拆 | 🔄 已派 Claude Code（hc:t5） |
| repo tech-design 不存在 | tech-arch 只出了 design.md + ADR | 🔄 已派 Claude Code（hc:t6） |
| repo 5 项外部事实未核实 | 云效限流/单文件上限/分页语义、GitHub PAT 过期头、fine-grained 最小权限 | 🔄 同上，要求联网核实，核不到就标未核实 |
| `tasks.md` 状态仍是 draft | core 关闭时没回填 | 顺手改，10 分钟 |
| 4 个下游域未立项 | 没走 intake | **需要你决定优先级顺序** |

## 四、这次接手做了什么

两个 Claude Code 任务已并行派出（工作区 `ai-test-workbench`）：

- **hc:t5** — 补齐 `knowledge-base` 的 `tasks.md`：批次划分、AC → TC → 测试落点表（TC 从 101 起）、迁移钉死 0007、路径对齐（文档写 `frontend/src/` 实际是 `web/src/`）。硬约束：不写业务代码。
- **hc:t6** — 推进 `repo-integration` 到 tech-design：先联网核实 5 项外部事实（核不到就标未核实，禁止编数），再出 change-spec / api-spec / database-schema / component-tree / file-structure / flowchart / test-strategy + tasks.md（TC 从 201 起，迁移钉死 0008）。

两个任务都只写 `specs/` 下的文档，不碰 `src/` `web/` `migrations/`。

## 五、已拍板的三件事（2026-11-20 15:41）

用户原话：「1、A　2、串行　3、后边开」

| # | 事项 | 决定 | 影响 |
|---|------|------|------|
| 1 | `kbId` 类型冲突（OQ-TD-04） | **A** — core 改 `str`，KB 保持 `CHAR(32)` | core 侧 3 个 dataclass + schema + 2 处转换 + 测试断言；KB 的 ADR-103 与 API 契约完全不动 |
| 2 | KB 与 repo 的推进节奏 | **串行，KB 先** | 单线推进：KB 全部批次 → repo 全部批次。避免 `AppShell.tsx` 侧边栏与错误码表撞车 |
| 3 | `test-case` 等 4 个下游域 | **后边开** | 本期只做 KB + repo；6 个入口继续保持 `planned` 占位 |

### 串行排期表

```
第 1 批  core kbId 类型修正（前置，阻塞 KB 批次 D）
           ↓
第 2 批  knowledge-base  A → B → C → D → E（18 任务 / 185h / 关键路径 127h）
           ↓
第 3 批  repo-integration  A → B → C → D → E（32 任务 / 294h / 关键路径 234h）
           ↓
第 4 批  6 个入口 live 验收（等 test-case 等域，后边开）
```

core 的类型修正是**唯一的前置项**，它不阻塞 KB 的 A~C 批次（解析层、导入、浏览都不碰 `kbId`），只阻塞批次 D 的 `/ai/complete` 联调。所以可以并行起手：

```
core 类型修正 ──┐
                 ├──► KB 批次 D 联调
KB 批次 A~C ────┘
```

## 六、平台级扩展能力规划（2026-11-21 决策）

结合 Billing Agent 产品调研与 Vigil 架构边界，确定在后续业务域推进过程中**按需分期引入 4 项平台级横切能力**（完整设计与红线见 `docs/platform-capabilities.md`）：

| 能力 | 定位与核心闭环 | 计划落地阶段 | 前端占位路由 |
|---|---|---|---|
| **QA 技能库**（`qa-skills`） | 人类编写/导入初版（v0），后续通过会话 Chat 让 Agent 协助修改并生成结构化 Diff 提案，**经审批后落盘**，禁止静默新建/覆写 | 随 `test-case` 域起步 | `/extensions/skills` |
| **MCP 工具源**（`mcp-registry`） | 受控接入外部日志、只读数据库、工单、本体服务；按 `projectId` 隔离，凭证走基座 AES-256-GCM 加密与掩码回显，默认只读 | 随 `diagnosis` 域落地 | `/extensions/mcp` |
| **审批中心**（`approvals`） | `pending → approved → executed / failed` 与 `rejected` 统一状态机；承接 Agent 资产 Diff 提案与外部写操作的人工确认 | 轻量版随 `test-case`，完整版随外部回写 / `ontology-builder` | `/extensions/approvals` |
| **变更审计**（`asset-history`） | 补齐 `AiCallRecord` 之外的资产变更流水、Unified Diff 预览与一键 `Rollback`（回滚不抹除历史） | 与 `approvals` 同步分期 | `/extensions/history` |

**明确排除**（不引入）：Agent 运行时自写 Python 工具（`create_tool`）、动态 UI 组件/画布编排/定时任务、插件市场（改用 Git 导入 Markdown Skill 轻入口）、无 `projectId` 隔离的单空间平铺模型。

## 七、底座完工基线与下游业务域方向校准（2026-11-21 更新）

### 1. 三大底座最新状态

| 底座域 | 状态 | 备注 |
|---|---|---|
| `workbench-core` | ✅ 已完成 | 含 `kbId: str` 统一、SPA `/api/**` 404 守卫、4 个平台扩展占位路由 |
| `knowledge-base` | ✅ 已完成（迁移 `0007`） | A~E 全部批次落地（解析、导入覆盖、浏览检索、一跳邻居、`/ai/complete` 注入联调） |
| `repo-integration` | ✅ 已完成（迁移 `0008`） | A~E 全部批次落地 + 云效 Codeup 真实仓库 API 契约修复与端到端 HTTP/DB 实测通过 |

### 2. 基于市场调研与竞品分析的 5 项方向优化

完整调研报告见 `docs/market-and-competitor-analysis.md`（对标 MeterSphere v3、Qase/TestRail AI、Qodo、HolmesGPT、Sentry Seer 与 Billing Agent）：

1. **底座黄金三角自动推荐（Context Recommender）**：在会话输入需求、报错堆栈或选定代码文件时，先做零 LLM 成本的确定性匹配，自动推荐本项目的 `KnowledgeEntry`（含一跳邻居）与 `RepoMetadataSnapshot` 文件供用户一键勾选注入。
2. **`test-case`（用例库）**：「两阶段生成（先确认测试设计检查点矩阵，再展开结构化用例）」+ 强制绑定溯源锚点（`linkedKbCodes` + `linkedCodePaths`，支持本体/代码变更时的失效用例标红）+ 表格/层级树双视图与 CSV/Markdown/XMind 互操作导出。
3. **`diagnosis`（Bug / 日志 / SQL 三合一诊断）**：统一为 `Hypothesis → Evidence → Finding` 结构化收敛引擎，自动结合报错堆栈调用 `repo-integration.read_file` 拉源码、结合 `KB` 拉 `ENT-` 表定义与 `BR-` 业务规则；SQL 诊断专项支持 `SQL + EXPLAIN + DDL/ENT-` 联合分析。
4. **`regression-list`（生成回归清单）**：拒绝黑盒盲猜，采用**「Git Commit 变更路径 → KB `codePaths` 与一跳邻居 → 近期 `Finding` 影响面」三路确定性爆炸半径召回** + LLM 风险分级（P0/P1/P2）+ 漏测盲区提醒（Coverage Gap Alert）。
5. **双工作流节奏**：同时支持**模式 A（人在场单人交互深潜）**与**模式 B（少确认批处理流转，结果一次性汇入 `Approvals` 终审）**。

### 3. 下游立项推荐顺序（机会评分排序）

```
1. test-case + qa-skills 最小闭环（得分 4.9）
     ↓
2. diagnosis 三合一诊断引擎（得分 4.8，V1 先用制品 + Repo + KB，V1.5 接 mcp-registry）
     ↓
3. regression-list 确定性爆炸半径召回 + 风险排序（得分 4.6）
     ↓
4. test-report 全链路可溯源报告（得分 4.5）
     ↓
5. ontology-builder 可视化本体扫描与确认（得分 3.9，压轴）
```


