# Requirements Analysis — Tasks

## 本阶段已完成

> 编号策略：TASK-RA-041 ~ 051 为从父 spec 迁入的原编号（按本 spec 范围重述任务内容，原始描述见 `_handoff/from-workbench-core.md` §9；迁移清单把 041 ~ 052 合记为 11 项，052 不单列）；新增任务从 TASK-RA-059 起编（父 spec 已用到 052，`knowledge-base` spec 已用到 053 ~ 058，避免跨 spec 混淆）。

- [x] TASK-RA-041 读取 intake 与原始需求，确认需求类型为 ➕ 功能新增、范围为 `repo-integration` 单域，按 intake 执行路径裁剪 skill 链（跳过市场与竞品研究）
- [x] TASK-RA-042 用户故事承接：US-017 ~ US-023 与 36 条 AC（AC-017-1 ~ AC-023-6）原编号逐字迁入 `requirements.md`，不改写、不重排
- [x] TASK-RA-043 EARS 承接：AC-REQ-25 ~ AC-REQ-35（11 条）原编号逐字迁入
- [x] TASK-RA-044 需求澄清承接：AMB-005（仓令牌复用）、AMB-006（仓库绑定修订部分）、AMB-020 ~ AMB-025 按已确认口径迁入，依据引用上游 `answers.md` 原话
- [x] TASK-RA-045 功能规格：问题陈述、目标、非目标、MoSCoW 摘要、令牌与数据边界非功能需求、成功指标（`requirements.md`）
- [x] TASK-RA-046 优先级矩阵：P0 = US-017 ~ US-022，P1 = US-023；Could / Won't 明确排除整库克隆、代码索引、Webhook、定时同步、仓库写操作、令牌自动轮换（`design.md`）
- [x] TASK-RA-047 业务流程图：US-017 ~ US-023 七张 mermaid 写入 `docs/flowchart.md`，含四类测试结果、并发同步、失败保留旧数据、截断提示、路径拒绝与解绑分支
- [x] TASK-RA-048 本体承接（首次建立 `_shared/ontology/`）：ENT-C12 ~ ENT-C15、BR-C21 ~ BR-C27、BP-C9 ~ BP-C11、TERM-C14 ~ TERM-C16，「对应图谱」标「未覆盖」
- [x] TASK-RA-049 令牌安全口径：加密存储、环境变量口令、掩码回显、令牌与鉴权头不落日志、只读最小权限、不发起写操作（`requirements.md` 非功能需求 / BR-C21）
- [x] TASK-RA-050 外部接口研究：GitHub REST 与云效 Codeup 的端点、鉴权头、分页与限流响应头、1 MiB 边界、fine-grained 权限映射（本轮联网核实结果见 `design.md`「外部接口核实」）；未核实项保留「待技术方案」
- [x] TASK-RA-051 与 workbench-core 的依赖边界对齐：`projectId`、项目上下文页与 AppShell、凭证加密与掩码、登录态、200,000 字符常量、错误体与分页约定；跨域只读接口按 `repoBindingId`
- [x] TASK-RA-059 需求澄清新增项：把 intake IQ-1 ~ IQ-6 转为 AMB-026 ~ AMB-031，写入 `requirements.md`「需求澄清」表与 `open-questions.md`，每条给出建议默认值 A 与理由
- [x] TASK-RA-067 用户拍板回填（2026-11-18 10:44:10「全按建议」）：AMB-026 ~ AMB-031 标记已确认并逐条引用 answers.md 原话；按 AMB-027 把分支 / 提交 / 仓库列表改为实时读取（AC-020-4、AC-REQ-29 与 US-019 / US-020 / US-021 口径注）；按 AMB-028 允许保存前用表单当前值测试（AC-018-1）；按 AMB-030 把「仓库地址」定为自由备注（design.md 决策 22）；按 AMB-031 明确解绑后目录树与读文件入口置灰；同步更新 `design.md`、`docs/context.md` 与 `docs/flowchart.md`（US-018 / US-019 / US-020 / US-021 / US-023）
- [x] TASK-RA-060 未核实事实标注：云效限流数值、云效单文件上限、GitHub PAT 过期响应头、地域版域名细节、分支列表权限行等，逐条列出已查地址与结论缺口，禁止实现假设数值
- [x] TASK-RA-061 编写 `docs/context.md`：需求类型、下游执行路径、In / Out of Scope、US 摘要、36 条 AC 清单、数据实体、系统集成点、关键约束与待确认项
- [x] TASK-RA-062 阶段自检：运行 `python3 .aw/aw.py check specs/repo-integration_20261117205011 --phase requirements-analysis`；AMB-026 ~ AMB-031 待用户答复，阶段保持待确认

## 交接给后续阶段

- [ ] TASK-RA-063 交互设计：在项目上下文页内落地仓库集成增量面板（绑定表单与掩码、四类连通性结果、同步按钮与上次同步时间 / 耗时 / 结果、仓库 / 分支选择器、提交与目录树、单文件查看、令牌失效提示、撤销二次确认）；复用 core 的 AppShell、设计 token 与错误 / 分页约定，补 AC-UX 与组件状态
- [ ] TASK-RA-064 技术方案：四类表结构与 Alembic 迁移（MySQL / SQLite 双方言）、五个供应商适配器契约、错误分类映射、响应头读取（分页与限流）、并发同步互斥、目录树 `truncated` 表示、跨域只读接口；对 `design.md` 列出的 8 项「待技术方案」逐条给出结论，不得编造云效限流与文件上限数值
- [ ] TASK-RA-065 技术方案：确认 AMB-029 的密钥方案落地（变量名、派生、轮换、与模型密钥隔离）与 AMB-026 / AMB-027 的读路径（快照 vs 实时）对表结构与缓存的影响
- [ ] TASK-RA-066 测试验证：为 36 条 AC 与 11 条 EARS 生成 TC，重点覆盖令牌不落日志与掩码、四类连通性结果、并发同步、失败保留旧元数据、限流提示、目录树 truncated、1 MiB 上限、二进制 / 非 UTF-8 拒绝、路径穿越、令牌失效恢复、解绑后不再请求、重新绑定新编号
