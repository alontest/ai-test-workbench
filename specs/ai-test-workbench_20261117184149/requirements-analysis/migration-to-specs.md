# 迁移清单 — workbench-core 收窄（2026-11-17 20:50:31）

- 决策依据：用户 2026-11-17 20:50:31「我点错了。不是拆2个。另外前边的问题我也没确认呢。一并给我弹窗吧」；弹窗结果「拆 3 个」（workbench-core / knowledge-base / repo-integration）。
- 目标 spec：`specs/knowledge-base_20261117205011`（module `knowledge-base`）、`specs/repo-integration_20261117205011`（module `repo-integration`）。
- 编号策略：AC / US / AMB / BR / ENT / BP / TERM 一律保持原编号，不重排；本 spec 仅保留编号占位与迁出说明。
- 逐条原文（用户原话、AMB 口径、US/AC/EARS 原文、实体与规则、流程图、线框、接口核实）：见两份 `_handoff/from-workbench-core.md`。

## 一、迁出条目（按目标 spec 分组）

### A. → `specs/knowledge-base_20261117205011`

| 类别 | 编号 / 条目 | 数量 |
|---|---|---|
| 用户故事 | US-012、US-013、US-014、US-015、US-016 | 5 |
| AC（GIVEN/WHEN/THEN） | AC-012-1 ~ AC-012-7、AC-013-1 ~ AC-013-5、AC-014-1 ~ AC-014-5、AC-015-1 ~ AC-015-4、AC-016-1 ~ AC-016-3 | 24 |
| EARS | AC-REQ-18 ~ AC-REQ-24 | 7 |
| 需求澄清 | AMB-014、AMB-015、AMB-016、AMB-017、AMB-018（AMB-006 的 20:06:58「关联 0..n 知识库」修订部分） | 5 |
| 商业目标 | BG-05 | 1 |
| 假设 | H6 | 1 |
| 核心决策 | 决策 11、决策 12、决策 13、决策 14 | 4 |
| 实体 | ENT-C10（KnowledgeBase）、ENT-C11（KnowledgeEntry）；会话事件载荷 KnowledgeInjection | 2 + 1 |
| 业务规则 | BR-C15 ~ BR-C20 | 6 |
| 业务流程 | BP-C5、BP-C6、BP-C7、BP-C8 | 4 |
| 术语 | TERM-C10、TERM-C11、TERM-C12 | 3 |
| 流程图 | US-012、US-013、US-014、US-015、US-016 五张 mermaid | 5 |
| 交互线框 | 知识库列表页、导入知识库页、知识库浏览页、条目详情页、会话调用面板·知识库注入 | 5 |
| 已核实的格式 / 接口事实 | `index.json` 最小结构、条目字段与前缀映射、解析护栏、正文匹配、检索策略、注入组装、限额默认值、导入原子性 | 1 组（见 handoff 第 7 节） |
| 任务 | TASK-RA-028 ~ TASK-RA-033、TASK-RA-035 ~ TASK-RA-038 | 10 |

### B. → `specs/repo-integration_20261117205011`

| 类别 | 编号 / 条目 | 数量 |
|---|---|---|
| 用户故事 | US-017、US-018、US-019、US-020、US-021、US-022、US-023 | 7 |
| AC（GIVEN/WHEN/THEN） | AC-017-1 ~ AC-017-6、AC-018-1 ~ AC-018-5、AC-019-1 ~ AC-019-6、AC-020-1 ~ AC-020-4、AC-021-1 ~ AC-021-4、AC-022-1 ~ AC-022-5、AC-023-1 ~ AC-023-6 | 36 |
| EARS | AC-REQ-25 ~ AC-REQ-35 | 11 |
| 需求澄清 | AMB-020、AMB-021、AMB-022、AMB-023、AMB-024、AMB-025（AMB-006 的 20:33:31 仓库绑定修订部分；AMB-005 的令牌加密与掩码复用口径） | 6（+2 关联口径） |
| 商业目标 | BG-06 | 1 |
| 假设 | H5（修订版）、H7 | 2 |
| 核心决策 | 决策 15、决策 16、决策 17 | 3 |
| 实体 | ENT-C12（CodeRepoBinding）、ENT-C13（RepoSyncRecord）、ENT-C14（RepoMetadataSnapshot）、ENT-C15（RepoFileReadRecord） | 4 |
| 业务规则 | BR-C21 ~ BR-C27 | 7 |
| 业务流程 | BP-C9、BP-C10、BP-C11 | 3 |
| 术语 | TERM-C14、TERM-C15、TERM-C16 | 3 |
| 流程图 | US-017 ~ US-023 七张 mermaid | 7 |
| 交互线框 | 无（迁出时交互稿未覆盖仓库集成；需目标 spec 重新出稿） | 0 |
| 已核实的接口事实 | GitHub REST（端点、1 MB 边界、5,000 次/小时限流）、云效 Codeup（`x-yunxiao-token`、`/oapi/v1/codeup`、响应头分页）、复用结论 | 1 组（见 handoff 第 7 节） |
| 任务 | TASK-RA-041 ~ TASK-RA-051、TASK-RA-052 | 11 |

### 迁出合计

| 类别 | 迁出数量 |
|---|---|
| US | 12 |
| AC（GIVEN/WHEN/THEN） | 60 |
| EARS | 18 |
| AMB 行 | 11（另 AMB-006 的部分修订、AMB-005 的复用口径随附） |
| 实体 | 6 |
| 业务规则 | 13 |
| 业务流程 | 7 |
| 术语 | 6 |
| 流程图 | 12 |
| 核心决策 | 7 |
| 任务 | 21 |

## 二、保留在 `workbench-core` 的条目与计数

| 类别 | 保留内容 | 数量 |
|---|---|---|
| US | US-001 ~ US-011 | 11 |
| AC（GIVEN/WHEN/THEN） | US-001(3) + US-002(3) + US-003(4) + US-004(3) + US-005(5) + US-006(3) + US-007(3) + US-008(3) + US-009(5) + US-010(3) + US-011(7) | 42 |
| EARS | AC-REQ-1 ~ AC-REQ-17 | 17 |
| AMB | AMB-001 ~ AMB-013、AMB-019（AMB-014 ~ 018、020 ~ 025 行保留编号并注明已迁出） | 14 行有效 + 11 行迁出占位 |
| 实体 | ProjectContext、ProviderConfig、ModelBinding、Session、SessionEvent、Artifact、AiCallRecord、AdminCredential、LoginSession（另有 6 条迁出条目保留原文并标注） | 9 |
| 业务规则 | BR-C1 ~ BR-C14（BR-C5 已被 BR-C11 取代，保留原文；另有 13 条迁出条目保留原文并标注） | 14 |
| 业务流程 | BP-C1 ~ BP-C4（另有 7 条迁出条目保留原文并标注） | 4 |
| 术语 | TERM-C1（已被 TERM-C13 取代）、TERM-C2 ~ TERM-C9、TERM-C13（另有 6 条迁出条目保留原文并标注） | 10 |
| 流程图 | US-001 ~ US-011 | 11 |
| 核心决策 | 决策 1 ~ 决策 10 | 10 |

**收窄后的新总数：US 11 个、AC 42 条、EARS 17 条。**（拆分前：US 23 个、AC 102 条、EARS 35 条。）

## 三、保留但需注意的口径

- **200,000 字符上限（已定）**：作为全局输入上限常量，本 spec 保留并在文中注明「`knowledge-base` 的注入正文与提示正文合计沿用同一常量」；数值只在本 spec 定义一次，不重复定义。
- **`_shared/ontology/*` 的处置（已定）**：迁出条目**未物理删除**，原条目保留并逐条追加 `> 已迁出至 <新 spec 目录>（2026-11-17）`；`kb-sync` 提升时可正常对账。迁移清单中的「迁出」均指「标注迁出」，不是删除。涉及：TERM-C10 ~ C12、C14 ~ C16；ENT-C10 ~ C15；BR-C15 ~ BR-C27；BP-C5 ~ BP-C11。
- **AMB-006**：保留人工填写项目上下文；知识库关联与仓库绑定两个修订版本已随对应 spec 迁出，行内注明。
- **AMB-019（入口更名「用例库」）**：属本 spec，保留。
- **六条核心设计原则**：属本 spec，保留（interaction-design 已确认稿）。仓库集成的原则落点需由 repo-integration 自行补充。
- **`ontology-builder` 域（已定）**：立项顺序暂不决定，域地图状态标「待排期」；依赖 `workbench-core` 的 AI 网关、会话与制品，其「上传导入知识库」的落点属 `knowledge-base` spec。

## 四、归属不清、需用户拍板的条目

1. **AMB-015 的数值归属（已定）**：200,000 作为全局输入上限常量，本 spec 保留并在文中注明由 `knowledge-base` 沿用同一常量，数值不重复定义。
2. **AMB-006 的拆分表述（已定）**：新 spec 自建 AMB 编号，并在条目里引用「源自 workbench-core AMB-006 修订（时间）」，不重编旧号。
3. **`ontology-builder` 域的依赖对象（已定）**：立项顺序暂不决定，域地图状态标「待排期」。
4. **知识库导航/AppShell 归属（已定，用户 AskUserQuestion 2026-11-17 21:00）**：**复用 workbench-core 外壳**——AppShell、设计 token、登录态共用；`knowledge-base` 在侧边栏单独入口，并在会话面板内嵌注入。
5. **仓库集成的交互与技术设计（已定，用户 AskUserQuestion 2026-11-17 21:00）**：**扩展 core 现有线框与架构**——项目上下文页加绑定 / 同步 / 浏览 / 读文件 / 解绑面板；凭证加密存储、错误结构、分页约定沿用 core；不完整重跑。

## 五、验证

- `python3 .aw/aw.py check specs/ai-test-workbench_20261117184149 --phase requirements-analysis`
- 两份 handoff 行数：见本次汇报（`wc -l` 已核对非空）。
