# tech-arch · 跨 spec 扩展确认记录（knowledge-base）

> **状态：全部已拍板**（2026-11-18 11:23:18，用户原话「A101 A、A102 A、A103 B」，完整记录见 `technical-design/answers.md`）。本文件保留选项与影响作为决策留痕；结论已写入 ADR-111 / ADR-112，无待确认项。
> 结论：101 = A（core 落库扩展，迁移 `0006`）、102 = A（`complete` 追加可选 `injection`）、103 = **B**（复用 core 的 `/ai/complete`，不新增 calls 端点；本 spec 提供进程内注入服务）。本 spec 的表迁移从 `0007` 起。

## OQ-ARCH-101：注入留痕的 core 表扩展由谁落地 — ✅ 已确认 A

**背景**：`AC-014-2` / `AC-014-5` 要求「在 AiCallRecord 与 SessionEvent 记录知识库、编号列表与字符数（不记正文）」。core 现有 `ai_call_record` 没有承载知识库快照的列，`session_event.type` 的 CHECK 只允许 `input_text / artifact / call / status_change`。必须做一次 additive 扩展。

**选项**

- **A（推荐）**：由 **core spec 落地**扩展——`ai_call_record` 追加 `knowledge_injection JSON NULL`、`injected_chars`、`prompt_chars`、`total_chars`；`session_event.type` 增加 `knowledge_injection`；core 的 calls / 时间线序列化同步暴露 `knowledgeInjection` 与 `kbDeleted`（按 `kbId` 左连接 `knowledge_base`）。本 spec 只读写，不拥有迁移。
- **B**：由**本 spec 自带** additive 迁移（编号顺延 core 的 `0005` → `0006`；若 core 另有迁移则再顺延），core 只读新列；core 的 database-schema / api-spec 仍需补文档与序列化。
- **C**：不加列，只写 `knowledge_injection` 事件（仍需扩 CHECK），AiCallRecord 不记录知识库字段。**违反 AC-014-2，不推荐**。

**拍板结果：A**（2026-11-18 11:23:18）。表归属清晰，core 的迁移链自然延伸；本 spec 只依赖列存在。core 因占用 `0006`，本 spec 表迁移从 `0007` 起。

**影响**

- A：需要 core 补充确认（其 `change-spec.md` / `database-schema.md` / `api-spec.md` 更新）；本 spec 的实现等待 core 迁移合并后联调。
- B：知识库可独立推进，但同一张表的 DDL 由两个 spec 交付，合并顺序与迁移链（`down_revision`）必须协调；core 读取侧仍要改。
- C：需要在验收记录里明确「AiCallRecord 不含知识库字段」的偏差，由用户接受。

## OQ-ARCH-102：是否允许给冻结的 `AiGateway.complete` 追加可选参数 — ✅ 已确认 A

**背景**：`AiGateway.complete(session_id, model_id, prepared, *, temperature, max_tokens)` 是 core 冻结签名。要让注入快照与 AiCallRecord 在同一事务原子写入，最直接的方式是给网关一个可选的快照入参；否则只能调用后回填。

**选项**

- **A（推荐）**：追加 keyword-only 可选参数 `injection: InjectionSnapshot | None = None`。网关在插入 `running` 记录时写 `knowledge_injection` 等列，并在同事务追加 `knowledge_injection` 事件。原调用方式与语义完全不变，缺省 `None` 时行为与现在一致。
- **B**：不改签名。本 spec 在 `complete` 返回后按 `AIResult.call_id` 回填列并追加事件。满足「签名冻结」，但**非原子**：进程崩溃或回填失败会丢失留痕；「调用发起时记录」退化为「调用结束后回填」。
- **C**：用 `contextvars` 隐式传递快照。网关签名不变，但隐式状态难测试、易被并发请求串扰，不推荐。

**拍板结果：A**（2026-11-18 11:23:18）。

**影响**

- A：core 需做一次向后兼容的签名扩展与契约测试；调用方（core 自身 `/ai/complete`）可继续按旧方式调用，本 spec 通过 `injection` 传快照。
- B：本 spec 无需改动 core 签名，但需在发布说明标注「注入留痕非原子」，并增加补偿任务（按 `call_id` 扫描缺失快照的调用记录）——本期不做补偿任务的话，实际风险由用户接受。
- C：不推荐，仅在 A/B 都被否时作为最后手段。

## OQ-ARCH-103：注入后的「发起调用」入口归属 — ✅ 已确认 B（用户改选）

**背景**：core 已有 `POST /api/v1/sessions/{sessionId}/ai/complete`，请求体是 `{prompt, temperature?, maxTokens?}`。知识库注入需要在发起前做失效条目重校验、阻塞确认、组装与字符预算。入口有两种放法。

**选项**

- **A（子代理原推荐，未采纳）**：本 spec 新增 `POST /api/v1/sessions/{sessionId}/knowledge-injection/calls`；core 会话页在已勾选知识库条目时改调该端点。被否：会话页出现两条调用路径。
- **B（采纳）**：扩展 core 的 `/ai/complete` 请求体（`knowledgeRefs`、`confirmInvalidCodes`），由 core 在调用前调用本 spec 的进程内服务 `KnowledgeInjectionService.prepare_for_call(...)` 完成失效重校验、组装与字符预算；调用入口唯一。core 的请求 schema、错误码与前端调用路径同步扩展。
- **C**：知识库只提供 preview，前端把拼好的文本作为 `prompt` 传给 core `/ai/complete`。削弱服务端收口，不推荐。

**拍板结果：B**（2026-11-18 11:23:18，用户原话「A103 B」）。

**落地**

- **不新增** `/knowledge-injection/calls` 端点；`GET .../knowledge-injection/candidates` 与 `POST .../knowledge-injection/preview` 保留为只读/预览接口。
- core 的 `/ai/complete` 在调用 `AiGateway` 前调用 `prepare_for_call`，域错误 `knowledge_invalid_entries` / `knowledge_injection_empty` / `prompt_budget_exceeded` 由 core 映射为 HTTP。
- core 的前端从「勾选时切端点」改为「始终调 `/ai/complete`，附带 `knowledgeRefs`」。

---

## 拍板结果汇总

| OQ | 结果 | 一句话 |
|----|------|--------|
| OQ-ARCH-101 | **A** | core 的迁移 `0006` 落地 `ai_call_record` 扩展列与 `knowledge_injection` 事件类型；本 spec 只读写 |
| OQ-ARCH-102 | **A** | 给 `AiGateway.complete` 追加可选 `injection` 参数，原子写留痕 |
| OQ-ARCH-103 | **B** | 不新增 calls 端点；扩展 core 的 `/ai/complete`，由其调用本 spec 的进程内注入服务 |

---

## tech-design 对齐与待确认项（2026-11-18）

> 本节记录 tech-design 展开时发现的跨 spec 字段级差异与路径对齐。已有 ADR 原文未改动；下面只补字段级落地口径。

### OQ-TD-01：`knowledgeRefs` 的请求形状（待用户确认，默认 A）

**背景**：ADR-112（已锁定）写的是 `knowledgeRefs: [{kbId, code}]`（扁平）；core spec 的 `docs/api-spec.md` 与 `/ai/complete` 请求 schema 写的是 `knowledgeRefs: [{kbId, entryCodes: string[]}]`（按知识库分组）。端点归 core 所有，两种形状不能同时成立。

- **A（默认，推荐）**：采用 core 的分组形状 `[{kbId, entryCodes[]}]`，`confirmInvalidCodes` 保持扁平 `[{kbId, code}]`。core 无需改；本 spec 在 `change-spec.md` / `api-spec.md` 记录「按 core 端点 schema 对齐」，`prepare_for_call` 入参仍是扁平 `KbEntryRef`，由 core 展平。
- **B**：坚持 ADR-112 的扁平形状，要求 core 改其 api-spec、请求 schema 与前端调用（core 的 tech-design 目前是 draft，改动成本低，但需 core spec 重新确认）。

**建议**：A。字段级归属随端点，core 拥有 `/ai/complete` 的 schema，知识库侧只消费展平后的引用。

### OQ-TD-02：前端目录前缀（已按默认写入，如无异议随阶段确认）

ADR-113 写 `frontend/src/knowledge/`，core 既有前端根是 `web/src/`、页面按 `web/src/features/<域>/` 组织。

- **A（默认，已执行）**：落到 `web/src/features/knowledge/`，复用 core 的 `lib/api`、`components/ui`、`styles/tokens.css`。
- **B**：新建 `frontend/` 根——会与 core 构建链（Vite 根、TS 配置、静态托管）脱节，不推荐。

### OQ-TD-03：注入候选是否分页（已按默认写入，不阻塞）

`GET .../knowledge-injection/candidates` 在 handoff 中没有分页，但单库可达 20,000 条，全量返回会让选择器不可用。

- **A（默认，已执行）**：`limit` 默认 50 / 上限 200 + `cursor`，并支持 `q` / `type` 过滤与 `countsByType`，与条目浏览同一实现。
- **B**：只返回前 200 条、不提供翻页——会静默隐藏条目，不推荐。

