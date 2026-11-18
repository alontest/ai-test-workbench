# Intake

## 需求类型

➕ 功能新增（`feature`）

判定依据：本 spec 是同一产品按用户 2026-11-17 20:50:31 「拆 3 个」决策后拆出的第 2 个 spec，从已完成的父 spec `ai-test-workbench_20261117184149`（域 `workbench-core`）迁出知识库能力；仓库虽只有 bootstrap 提交、无业务实现，但产品级调研、用户故事、线框与部分技术结论已存在，属于在既有产品规划内新增一个功能模块，不重跑市场与竞品研究。与 `spec.json` 的 `type: feature` 一致，无需 `retype`。

## 变更性质

🆕 全新模块

`knowledge-base` 模块此前没有任何代码与知识库文档（`docs/` 目录不存在，本 spec 无 `_shared/`、无本体切片）；知识库的实体、业务规则与流程均为首次建立，迁入的 US/AC/BR 是同一产品的既有需求原文，不是既有实现的增量修改。

## 执行路径

- 需求分析：`priority-matrix` → `feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator`（功能新增跳过 `market-research` / `competitor-analysis`；素材以 handoff 第 3~5 节原文为底稿，只做本 spec 的范围裁剪与编号保留）
- 交互设计：执行（`SCOPE: ui=yes`）。复用 workbench-core 已确认的 AppShell、设计 token 与登录态（用户 2026-11-17 约束）；知识库 5 处线框（列表 / 导入 / 浏览 / 详情 / 会话注入面板）可直接沿用 handoff 第 6 节已确认稿，本阶段只需复核与补齐新 spec 边界
- 技术方案：`tech-stack-advisor`（沿用 workbench-core 已定栈，只记录继承约束，不重新选型）→ `risk-analysis` → `architecture-confirm` → `api-design` → `database-design` → `component-breakdown` → `file-structure-generator` → `task-breakdown`
- 测试验证：`test-case-generator` → `auto-test-runner`

## 上下文扫描

- 相关模块：`knowledge-base` 在 `docs/` 下不存在（`docs/` 整个目录尚未创建，无 `docs/_shared/domain-map.md`、无 `docs/knowledge-base/`）
- 历史 spec：
  - 父 spec `specs/ai-test-workbench_20261117184149`（module `ai-test-workbench`，域 `workbench-core`）：知识库 US-012 ~ US-016 的原文来源；其 `requirements-analysis/docs/context.md` 已把知识库整体标注为迁出
  - 兄弟 spec `specs/repo-integration_20261117205011`：只含云效 / GitHub 仓库集成，与知识库无功能重叠，仅共享 core 的项目上下文与凭证能力
  - 本 spec 已有：`spec.json`（type `feature`，7 阶段全走）、`_handoff/from-workbench-core.md`（已抽取原文）
- 已有 docs：无；无 `ontology-work/views/` 本体参考层，因此没有 `ontology-slices/intake.md`；无 `kb-inventory.md`（`kb-sync` 尚未带入）
- 代码现状：仅 bootstrap 提交；`src/workbench/__init__.py` 仅有版本号，`tests/conftest.py` 仅有注释，无任何知识库实现
- 知识库状态：首次建立（用户确认 intake 后由 `kb-sync` 同步到 `docs/knowledge-base/`）

## 类型与变更性质组合

➕ 功能新增 × 🆕 全新模块 → 走全部 7 个阶段，知识库首次建立；不涉及推翻旧 ADR。少见组合说明：仓库本身无业务代码，但同一产品的父 spec 已完成需求与线框，故不改判为 🆕 新产品（避免重跑市场 / 竞品），沿用产品级结论。

## 本 spec 范围边界

### In Scope（承接自 handoff，编号原样保留）

| 能力 | 用户故事 | AC 数 | 要点 |
|---|---|---|---|
| 导入知识库并建立编号索引 | US-012 | 7（AC-012-1 ~ 7） | `.json` / `.md` / `.markdown`，必须含 `index.json`；AMB-014 限额；前缀映射类型；部分条目非法跳过并在报告列行号；失败整体回滚 |
| 浏览与检索条目 | US-013 | 5（AC-013-1 ~ 5） | 按项目 / 知识库 / 类型筛选；编号前缀、完整编号、关键词检索；详情含字段、表、代码路径、一跳邻居、来源文件、新鲜度；正文缺失标「正文缺失」 |
| 会话内按编号注入 | US-014 | 5（AC-014-1 ~ 5） | 选择器实时字数；注入模板「编号 + 标题 + 正文（缺失用摘要）」；合计 ≤200,000 字符，超限拒绝不截断；失效条目阻止；记录知识库、编号、字符数，不记正文 |
| 新鲜度与版本冲突 | US-015 | 4（AC-015-1 ~ 4） | 只读 `index.json` 元数据；缺失「未知」；同编号摘要不同「版本冲突」；超 30 天「可能过期」；只提示不阻断；不克隆仓库、不解析代码 |
| 删除知识库 | US-016 | 3（AC-016-1 ~ 3） | 级联删除知识库 / 条目 / 文件；历史会话与调用记录不变，编号标「知识库已删除」；不自动过期 |
| 项目上下文的 0..n 知识库关联展示 | AC-012-6、AC-REQ-24 | — | 只提供关联区块与跳转，项目上下文页本体属 workbench-core |

- AC 合计：**24 条**（US-012 7 + US-013 5 + US-014 5 + US-015 4 + US-016 3）；EARS **7 条**（AC-REQ-18 ~ AC-REQ-24）。
- 其他承接：AMB-014 ~ AMB-018（AMB-006 的「关联 0..n 知识库」修订部分）、ENT-C10 / ENT-C11 / KnowledgeInjection、BR-C15 ~ BR-C20、BP-C5 ~ BP-C8、TERM-C10 ~ TERM-C12、BG-05、H6、决策 11 ~ 决策 14、流程图 5 张、线框 5 处、任务 10 条（TASK-RA-028 ~ 033、035 ~ 038）。

### Out of Scope（明确排除）

- 本体生成（内嵌 `ontology-builder-native`、人工确认对话框）：独立域 `ontology-builder`，另行 `aw-start`，待排期
- 知识库服务端路径引用、在线编辑条目、代码级新鲜度校验、向量检索 / RAG / 代码索引
- workbench-core 的 AI 网关（`ai.complete`、唯一预算校验点）、会话 / 事件、制品落盘、凭证加密存储、登录与访问控制、AppShell 与设计 token
- 云效 / GitHub 仓库绑定、同步与凭证（repo-integration spec）
- 多用户账号与角色权限：继承 workbench-core 的单用户登录边界
- 检索分页方式、FTS 升级时机、大数据量性能策略：留待技术方案
- 知识库自动过期清理 / 归档压缩

## 与 workbench-core 的依赖点

| 依赖 | 用途 | 边界 |
|---|---|---|
| ProjectContext（`projectId`） | 知识库归属项目（0..n）、同项目名称唯一、按项目筛选 | 项目上下文页与项目实体归 core；本 spec 只引用 `projectId` 与关联展示区块 |
| AI 网关 `ai.complete` | 注入后发起模型调用；**唯一字符预算校验点** | 本 spec 只产出 `PreparedPrompt`（注入块 + 字符数）；200,000 常量由 core 定义，本 spec 引用同值、不重复定义 |
| Session / SessionEvent | 追加注入事件（知识库、编号列表、字符数） | 事件模型归 core；本 spec 不复制正文进事件 |
| AiCallRecord | 记录知识库、编号列表与字符数（不记正文） | 记录写入归 core；错误码 `prompt_budget_exceeded` 及 `promptChars / injectedChars / totalChars / limit` 由 core 返回 |
| 制品 / 文件落盘 | 知识库文件与 `.md` 正文的本地存储 | 知识库使用独立目录与独立校验规则（不与会话上传面板共用白名单与 10MB / 10 个限额） |
| 登录态、AppShell、设计 token | 侧边栏「基座管理」分组入口 `/knowledge-bases` + 会话面板内注入 | 不另建外壳（用户已定） |
| 凭证加密 | 本 spec 不存任何外部凭证 | 仅沿用 core 的「知识库正文可能含密钥」的脱敏规则（BR-C18） |
| 进程内接口归属 | `PreparedPrompt` 交给 `AiGateway` 的接口归属；若知识库独立部署时的边界 | **待技术方案**（handoff 第 8 节原标注，不在 intake 下结论） |

## 保留 handoff 的「待技术方案」项（原标注，不编造结论）

1. 登录 / 多用户 / 权限：当前继承 core 的单用户边界，迁出后是否变化未定。
2. 检索大数据量下的分页方式与 FTS 升级时机（现结论文本：`LIKE` + `limit 50 / 上限 200` + cursor）。
3. 知识库与项目上下文页的耦合：`ProjectContext` 归属仍需与 workbench-core 协商（知识库引用 `projectId`）。
4. 注入字符计数的「提示」部分由 core `ai.complete` 唯一校验；若知识库独立部署，进程内接口归属未定。
5. 上游 `index.json` 尚无条目级新鲜度字段，「可能过期」仅在用户提供 `freshness_at` / `updated_at` 时生效（原样保留）。
6. 导入报告行号为「尽力而为」（定位 `"id": "<code>"` 首次出现的行，找不到回退 `entries[<index>]`）。
7. `index.json` 具体字段与向下兼容策略、检索服务端 / 前端、`.md` 与条目匹配规则、存储布局与删除事务边界、注入块最终拼装格式：handoff 第 7 节已有技术结论但**尚未实现**，需在 tech-arch / tech-design 复核确认，intake 不视为已定。

## 待确认（需用户拍板 / 复核）

| # | 事项 | 建议默认 | 状态 |
|---|---|---|---|
| 1 | 侧边栏入口与会话面板注入是否复用 core 外壳 | 复用 core 的 AppShell / 设计 token / 登录态，不另建外壳 | **用户已定**（2026-11-17 委派约束），不再询问 |
| 2 | `ProjectContext` 页面上的「关联知识库」区块由谁实现 | core 的页面留挂载位，本 spec 提供区块与只读接口；最终归属在 tech-arch 记录 | 待技术方案确认（有默认，不阻塞 intake） |
| 3 | 知识库文件存储是否与 core 的制品目录同根 | 独立 `knowledge-bases/<kbId>/`，与会话制品隔离 | 待技术方案确认（有默认，不阻塞 intake） |
| 4 | 迁入的线框是否直接沿用 | 沿用 handoff 第 6 节已确认稿，交互设计阶段只复核边界与徽标 | 待交互设计阶段复核 |

## 域复杂度评估

多域：否

理由：本 spec 只覆盖 `knowledge-base` 单一域（用户 2026-11-17 20:50:31 已把产品拆为 workbench-core / knowledge-base / repo-integration 三个 spec，域边界已定）；本域核心实体只有 KnowledgeBase 与 KnowledgeEntry，业务规则 BR-C15 ~ BR-C20 同属一个所有权，无进一步拆分必要。不写 `<SPEC_DIR>/_shared/domain-map.md`；跨 spec 依赖按上节依赖表逐条约束。

SCOPE: ui=yes api=yes data=yes
