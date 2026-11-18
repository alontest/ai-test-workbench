# Intake

## 需求类型

➕ 功能新增（对应 `--type feature`，与 `spec.json` 的 `type: feature` 一致）

判定依据：仓库已有 bootstrap 工程（`src/workbench/__init__.py` 仅版本号、`tests/conftest.py` 仅注释），需求是在既有工作台上新增「仓库集成」能力（绑定、连通性、同步、浏览、读文件、解绑），不是全新项目，也不是改变既有功能实现方式。

> 需求类型识别为：**➕ 功能新增**
>
> 本次将执行以下路径：
> - ✅ 需求分析：`priority-matrix`（沿用上游 P0/P1，仅复核）、`feature-spec`、`requirements-clarify`、`user-story-writer`、`flowchart-generator`；跳过 `market-research`、`competitor-analysis`（功能新增不走市场/竞品）
> - ✅ 交互设计：执行（在 `workbench-core` 项目上下文页上扩展仓库绑定/同步/浏览/读文件/解绑面板）
> - ✅ 技术方案：`tech-stack-advisor`（仅确认沿用既有栈的增量）、`risk-analysis`、`architecture-confirm`、`api-design`、`database-design`、`component-breakdown`、`file-structure-generator`、`task-breakdown`
> - ✅ 测试验证：`test-case-generator` → `auto-test-runner`
>
> 需求层已由上游 workbench-core 产出 US-017~023 / 36 条 AC / 11 条 EARS 原文，`feature-spec` 与 `user-story-writer` 以「承接、校准一致性、补新歧义」为主，保留原编号不重排、不重写。

## 变更性质

🆕 全新模块（module `repo-integration` 首次建立，`docs/repo-integration/` 尚无任何底稿；但依附 `workbench-core` 的项目上下文页与既有技术架构扩展，不是另起一套）

## 执行路径

- 需求分析：`priority-matrix` → `feature-spec` → `requirements-clarify` → `user-story-writer` → `flowchart-generator`
- 交互设计：执行；复用 `workbench-core` 的 AppShell、「基座管理」分组与 Dark-first 设计基调，在项目上下文页内新增面板（含绑定表单与掩码、四类连通性结果、同步按钮与上次同步时间、仓库/分支选择器、提交与目录树、单文件查看、令牌失效与撤销确认）
- 技术方案：`tech-stack-advisor`（增量确认沿用 FastAPI + Pydantic + SQLAlchemy/Alembic + MySQL/SQLite 双方言、React + Vite + TanStack Query）→ `risk-analysis` → `architecture-confirm` → `api-design` → `database-design` → `component-breakdown` → `file-structure-generator` → `task-breakdown`
- 测试验证：`test-case-generator` → `auto-test-runner`

## 交付形态

Web 应用（浏览器访问的 Web 前后端），沿用上游结论。依据：原 spec `answers.md` 用户原话「3.交付web应用」。

## 本 spec 范围

### In（本 spec 交付）

1. 仓库绑定与令牌：创建绑定（提供商、令牌、仓库标识、可选 API 域名）、更新令牌（只替换令牌与掩码）、查看（掩码与过期时间）、二次确认解绑；令牌服务端加密、掩码回显、只读最小权限提示；同项目同提供商 + 同仓库唯一；数量 0..n 并提示建议 ≤ 5。
2. 连通性测试：一次只读请求、10s 内返回「成功 / 鉴权失败 / 网络失败 / 权限不足」，记录测试时间与结果，不写会话、制品与 AiCallRecord。
3. 手动同步：仓库基本信息 + 全部分支 + 最近 100 条提交；同绑定禁止并发；失败保留上次成功元数据与时间；限流展示可重试时间；展示上次同步时间、耗时与结果；不做定时与后台轮询。
4. 仓库 / 分支选择：按名称或关键词检索、分页、默认选中绑定仓库与默认分支；未同步空态引导；令牌失效时仍可看带时间标记的缓存元数据。
5. 提交与目录树浏览：提交 sha 短号、标题、作者、时间、倒序、翻页；目录树逐级展开（名称、类型、大小）；供应商截断时提示「目录树不完整」。
6. 按需读取单文件：按 ref 读取、≤ 1 MiB（1,048,576 字节）、仅 UTF-8 文本、路径与 ref 前置校验、二进制/非 UTF-8 拒绝预览、读取记录审计（不存正文）。
7. 令牌失效与过期：401/403 鉴权语义标「令牌失效」并统一提示重填；换有效令牌且测试成功恢复「已连接」；供应商提供过期时间时展示，剩余 < 7 天提示「即将过期」。
8. 解绑后元数据只读：标注「已解绑」、删除加密令牌、不再同步或读文件；历史会话、制品与 AiCallRecord 不变；重新绑定生成新 bindingId。
9. 落盘与接口：ENT-C12 ~ ENT-C15 四类数据、对外 REST 接口、跨域只读接口（其他域按 `repoBindingId` 引用元数据与按需文件内容）。
10. 交互与技术设计：在 core 既有线上扩展的项目上下文页仓库集成面板、后端适配器与错误分类、分页/限流读取。

### Out（本 spec 不做）

- 整库克隆、代码索引 / 向量检索、Webhook、定时任务与后台轮询、仓库写操作（建分支 / 提交 / 合并请求 / 评论）
- 令牌自动轮换与代续期、OAuth 授权流、多用户与团队权限（沿用核心单用户登录）
- 文件内容持久化：不落盘、不写会话制品、不写 AiCallRecord 正文
- 分析会话与 AI 调用编排（属 `workbench-core`）；知识库（属 `knowledge-base`）；用例 / 诊断 / 回归 / 报告等业务域
- 令牌加密存储方案本身（沿用 `workbench-core` 的 AMB-005 口径，本 spec 只复用不重定义）

## 承接条目（编号与数量，保持原编号不重排）

| 类别 | 编号 | 数量 |
|---|---|---|
| 用户故事 | US-017、US-018、US-019、US-020、US-021、US-022、US-023 | 7 |
| AC（GIVEN/WHEN/THEN） | AC-017-1~6、AC-018-1~5、AC-019-1~6、AC-020-1~4、AC-021-1~4、AC-022-1~5、AC-023-1~6 | 36 |
| EARS | AC-REQ-25 ~ AC-REQ-35 | 11 |
| 需求澄清 | AMB-020、AMB-021、AMB-022、AMB-023、AMB-024、AMB-025；关联口径 AMB-005（令牌加密与掩码复用）、AMB-006（20:33:31 修订部分） | 6 + 2 |
| 商业目标 | BG-06 | 1 |
| 假设 | H5（修订版）、H7 | 2 |
| 核心决策 | 决策 15（只做元数据 + 按需读文件）、决策 16（仓库令牌与模型密钥同级管理）、决策 17（手动同步、失败不清空旧数据） | 3 |
| 实体 | ENT-C12 CodeRepoBinding、ENT-C13 RepoSyncRecord、ENT-C14 RepoMetadataSnapshot、ENT-C15 RepoFileReadRecord | 4 |
| 业务规则 | BR-C21 ~ BR-C27 | 7 |
| 业务流程 | BP-C9、BP-C10、BP-C11 | 3 |
| 术语 | TERM-C14、TERM-C15、TERM-C16 | 3 |
| 流程图 | US-017 ~ US-023 七张 mermaid | 7 |
| 交互线框 | 无（迁出时交互稿未覆盖仓库集成，本 spec 新出增量稿） | 0（新增） |
| 任务 | TASK-RA-041 ~ TASK-RA-052 | 11 |

AC 合计：6+5+6+4+4+5+6 = **36**；US **7** 个；EARS **11** 条。

## 上下文扫描

- 相关模块：`repo-integration` 在 `docs/` 下不存在（仓库无 `docs/` 目录），知识库**首次建立**；模块已登记在上游域地图（支撑域、P0、🚧 进行中）
- 历史 spec：2 条；`specs/ai-test-workbench_20261117184149`（`workbench-core`，进行中，已收窄为纯基座）、`specs/knowledge-base_20261117205011`（同批拆分，仅有 `_handoff` 与 `spec.json`）
- 本 spec 现状：仅 `spec.json` 与 `_handoff/from-workbench-core.md`（43.3 KB，抽取原文齐全）；无 `requirements-analysis/`、无 `approvals.md`、无 `answers.md`
- kb-inventory：`requirements-analysis/kb-inventory.md` 不存在（本 spec 尚未经 `kb-sync` 带入），本文件代列扫描清单
- 已有 docs：无（`docs/` 未创建；无 `docs/_shared/domain-map.md`）
- 本文件依据（kb-inventory 代列）：`specs/ai-test-workbench_20261117184149/requirements-analysis/{intake,requirements,design,open-questions,answers}.md`、`interaction-design/{requirements,design}.md`、`technical-design/design.md`、`_shared/domain-map.md`、`_shared/ontology/{entities,business-rules,processes,glossary}.md`（迁出条目保留原文并标注「已迁出」）、本 spec `_handoff/from-workbench-core.md`
- 本体参考层：`ontology-work/` 不存在 → 无 `ontology-slices/intake.md`；上游 `_shared/ontology/` 四份文件可作只读核对底稿（迁出条目未物理删除）
- 代码现状：`src/workbench/__init__.py`（仅版本号）、`tests/conftest.py`（仅注释）、`pyproject.toml`（包名 `ai-test-workbench`、Python >=3.10、dev 依赖 `pytest>=8.0`、无运行时依赖）；尚无任何仓库集成实现
- 域地图：位于上游 spec 的 `_shared/domain-map.md`；`docs/_shared/` 尚无。本阶段判定为单域，不新写域地图，用户确认 intake 后由 `kb-sync` 带入

## 与 workbench-core 的依赖点

1. **项目主数据**：`ProjectContext` / `projectId` 属 core；ENT-C12 以 `projectId` 关联，只按 ID 引用，不跨域读写项目表（域地图「共享数据约定」）。
2. **交互基线**：AppShell、侧边栏「基座管理」分组（项目上下文 / AI 提供商与模型 / 调用记录 / 知识库）与项目上下文页线框（US-008）属 core；本 spec 只产出该页的**仓库集成增量面板**，不重画整页。core 交互稿正处「先返工再确认」，需避免两份稿冲突。
3. **技术架构**：后端 FastAPI + Pydantic + SQLAlchemy 2.x + Alembic，MySQL 8.4 生产 / SQLite 开发测试；前端 React + Vite + TanStack Query；单进程 Uvicorn 托管前端 `dist`。本 spec 沿用，不引入新框架。
4. **密钥加密与掩码（AMB-005 / core 决策 5）**：cryptography AES-256-GCM，加密码来自环境变量，接口只回显掩码；仓库令牌与其同级管理（决策 16），本 spec 不重定义方案，只接线。
5. **AI 调用与输入上限**：文件内容若被引用进分析，按文本输入口径走 core 的 `ai.complete` 并计入 200,000 字符上限（AMB-010）；本 spec 不写会话、制品与 AiCallRecord。
6. **登录与鉴权**：仓库绑定接口受 core 单用户登录会话（AdminCredential / LoginSession）保护，不新建账号体系。
7. **数据库迁移**：四张新表须接入 core 的 Alembic 迁移链并保持 MySQL / SQLite 双方言。
8. **跨域只读接口**：域地图已约定其他域按 `repoBindingId` 只读引用元数据与文件内容、不得持有令牌或直连供应商；接口名与签名由本 spec 技术方案定，后续业务域据此接入。
9. **HTTP 客户端要求**：两侧供应商都要读响应头（分页 `x-total`/`x-page`、限流 `X-RateLimit-*`），core 现有客户端若只返回 body，需在本 spec 中扩展。

## 类型与变更性质组合

➕ 功能新增 × 🆕 全新模块 → 走全部 7 个阶段，知识库首次建立。不是「推翻旧 ADR」场景：本 spec 新增 ADR 需注明与 core 既有决策（密钥、AI 网关、数据库、前端栈）的关系，冲突时在 tech-arch 单独说明。

## 域复杂度评估

多域：否

理由：本需求只覆盖一个支撑域 `repo-integration`（域地图已登记，职责与四类实体清晰、数据所有权单一）。拆分触发条件不成立：业务实体 4 个但同属一条「绑定 → 同步 → 浏览 → 读文件」链路；无多团队并行或独立数据主权边界；跨域接口已在域地图固定为「其他域按 `repoBindingId` 只读」。因此不写 `<SPEC_DIR>/_shared/domain-map.md`，也不建议继续拆分（仓库绑定与元数据浏览共享令牌与同步控制权，拆开会制造令牌跨域）。

## 未核实项清单（保留「待技术方案」，本阶段不编造）

1. 云效官方速率限制数值、单文件大小上限、令牌最小权限的官方表述（官方帮助页脚本渲染，未取到正文）——实现不得假设具体数值。
2. GitHub 令牌过期时间响应头的具体名称与语义；fine-grained PAT 对 Contents / Metadata 权限的精确映射。
3. 云效地域版实例的域名形态与路径差异细节（仅知「路径不带 `organizations/{orgId}` 段」）。
4. 仓库 / 分支 / 提交 / 目录树 / 单文件五个适配器接口契约、错误分类映射、分页游标与限流读取实现（原 TASK-RA-050）。
5. 元数据快照表结构与保留策略（含目录树 `truncated` 的表示）、并发同步互斥实现。
6. 仓库令牌与模型密钥是否共用同一加密口令 / 密钥（AMB-005 只定了「口令来自环境变量」）。
7. 交互设计：仓库集成整套界面尚未出稿（用户 20:50:31「交互层先返工再确认」）。
8. 测试：仓库集成 AC 用例（令牌不落日志与掩码、四类连通性结果、并发同步、失败保留旧元数据、限流提示、目录树 truncated、1 MiB 上限、二进制/非 UTF-8 拒绝、路径穿越、令牌失效恢复、撤销后不再请求）尚未生成（原 TASK-RA-051）。

已核实可直接沿用（勿重复研究）：GitHub Bearer 鉴权、六类端点、1 MB contents API 边界、5,000 次/小时限流；云效 `x-yunxiao-token`、默认域名与 `/oapi/v1/codeup` 前缀、响应头分页、`text` / `base64` 编码。

## 待用户拍板的歧义

| ID | 歧义 | 建议默认（A） | 影响 |
|---|---|---|---|
| IQ-1 | 目录树的获取时机：AC-019-1 的同步范围只含仓库信息 + 全部分支 + 最近 100 条提交，但 AC-019-6 / ENT-C14 说快照含「目录树路径与文件大小」，AC-021-2 又要求按供应商分页按页加载 | 浏览时实时按需拉目录树（逐级、分页），同步不拉全树；快照的「目录树路径」只指按需读取时的路径元数据 | 同步耗时、快照表结构、解绑后能否浏览目录树 |
| IQ-2 | 分支 / 提交列表读快照还是实时：AC-020-2 要求分页与检索、AC-021-1 要求翻页，而 AMB-023 只保留最近 100 条提交 | 列表读快照（分支全量、提交最多 100 条，翻页在本快照内）；浏览时不再请求供应商 | 是否与「完整浏览」预期不符；限流压力 |
| IQ-3 | 保存前能否测试连接：US-018 标题写「保存前后测试」，AC-018-1 只覆盖「绑定已保存」 | 仅已保存绑定可测；未保存凭证不发起请求、不落库（与 AC-018-1、AC-018-5 一致） | 表单交互与接口形态 |
| IQ-4 | 仓库令牌与模型密钥是否共用同一加密口令 / 密钥 | 不共用：为仓库令牌单设环境变量密钥，避免轮换模型密钥时全部仓库令牌失效 | 环境变量清单、迁移与回滚 |
| IQ-5 | core 项目上下文页的「仓库地址」人工文本框（US-008）与绑定列表的关系 | 两者并存：「仓库地址」保留为人工备注文本，绑定列表独立展示；不互相改写 | 交互稿与 core 页面字段归属 |
| IQ-6 | 已解绑绑定的元数据「只读可查」边界：读文件明确禁止；目录树若为实时拉取则解绑后不可查 | 解绑后只可查仓库 / 分支 / 提交快照；目录树与文件读取入口置灰 | 与 AMB-022、AC-023-4 的解释 |

未回答的条目将在需求分析阶段写入 `open-questions.md` 并返回 `need_user`；已确认的 AMB-020 ~ AMB-025 直接按 `_handoff` 第 2 节原文沿用，不重新问。

## 已确认（依据 answers.md / 上游 answers.md）

| 事项 | 结论 | 依据 |
|---|---|---|
| 需求类型 | ➕ 功能新增（feature） | 本次委派 `PROFILE=feature`；`spec.json` type=feature |
| 范围拆出 | 从 workbench-core 拆出仓库集成，独立 spec | 用户 2026-11-17 20:50:31「拆 3 个」+ 本次委派需求原文 |
| 交付形态 | Web 应用 | 上游 answers.md：「3.交付web应用」 |
| 令牌存储与回显 | 服务端加密、口令来自环境变量、只回显掩码 | 上游 answers.md：「AMB-005 A」 |
| AMB-020 ~ AMB-025 | 六条口径 | 上游 answers.md 2026-11-17 20:46:07：「AMB-020~025 全 A」 |
| 交互与技术设计 | 扩展 core 现有线框与架构，不完整重跑 | 本次委派「用户已定约束」 |

SCOPE: ui=yes api=yes data=yes
