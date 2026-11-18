# Requirements Analysis — Tasks

## 本阶段已完成

> 2026-11-17 20:50:31 收窄：TASK-RA-028 ~ 033、035 ~ 038、040（知识库）与 TASK-RA-041 ~ 052（仓库集成）已随需求迁出，原任务描述与结论见两份 `_handoff/from-workbench-core.md`；本文件只保留 workbench-core 基座相关任务。

- [x] TASK-RA-001 读取 intake 与原始需求，确认需求类型为 🆕 新产品、范围为 `workbench-core` 域
- [x] TASK-RA-002 用户研究综合：无原始数据，输出 5 条假设 H1–H5 与待验证问题（`design.md`）
- [x] TASK-RA-003 竞品分析：完成 4 次联网检索，输出市场分层、六入口覆盖对照与待验证项（`design.md` / `competitor-research.md`）
- [x] TASK-RA-004 MoSCoW 优先级矩阵：9 项 P0、4 项 P1、3 项 P2、5 项 Won't
- [x] TASK-RA-005 功能规格：问题陈述、目标、非目标、成功指标、时间考虑
- [x] TASK-RA-006 需求澄清：AMB-001 ~ AMB-009 已确认（引用 answers.md 原话），新增 AMB-010 待用户答复
- [x] TASK-RA-007 用户故事：US-001 ~ US-010，共 35 条 GIVEN/WHEN/THEN 验收标准
- [x] TASK-RA-008 业务流程图：10 张 mermaid 图（`docs/flowchart.md`），已按 AMB-008 / AMB-009 更新重试与删除分支
- [x] TASK-RA-009 本体补充：术语 8 条、实体 7 条、业务规则 4 条、业务流程 3 条（`_shared/ontology/`）
- [x] TASK-RA-010 将用户对 AMB-003 ~ AMB-009 的答复回填「需求澄清」表并同步受影响的 AC（003-1、005-2、005-5、007-2、007-3、009-5 与 EARS AC-REQ-3/6/9）
- [x] TASK-RA-011 AMB-004 确认单用户自托管、无登录；Out of Scope 与 `docs/context.md` 已同步（**该结论后被用户 2026-11-17 19:52:50 推翻，见 TASK-RA-022 ~ 026**）
- [x] TASK-RA-012 AMB-007 确认白名单、10MB、10 个上限与同名自动改名；AC-007-2 / AC-007-3 已回填
- [x] TASK-RA-013 AMB-008 确认 120s 超时与 1 次重试；AC-005-5 与 US-005 流程图已回填
- [x] TASK-RA-014 AMB-009 确认永久保留与手动级联删除；AC-009-5 与 US-009 流程图已回填
- [x] TASK-RA-015 将竞品联网核实结论合并进 `design.md` 的「竞品分析」，替换未联网核实的方向性判断并保留待验证标注
- [x] TASK-RA-016 追加用户确认的业务规则到 `_shared/ontology/business-rules.md`（BR-C5 ~ BR-C9）

- [x] TASK-RA-017 AMB-010 确认上限 200,000 字符；AC-006-3、AC-REQ-8、US-006 流程图与 `docs/context.md` 已回填

- [x] TASK-RA-022 回填单用户登录需求（用户 2026-11-17 19:52:50 推翻 AMB-004 A）：新增 US-011 与 7 条 AC（AC-011-1 ~ 7）、EARS AC-REQ-13 ~ 16、非功能需求（口令哈希、令牌安全属性、凭据不落日志）与 BG-04
- [x] TASK-RA-023 修正受影响的既有条目：AMB-004 状态改为「已忽略」并引用 answers.md 原话；Out of Scope、功能范围、成功指标、`design.md` 的 H4 / 优先级矩阵 / 决策 6 同步改为单用户登录
- [x] TASK-RA-024 更新 `docs/flowchart.md`：US-001 加入登录前置校验，新增 US-011 登录流程图；`docs/context.md` 同步 In Scope、US 摘要、AC 清单、数据实体与关键约束
- [x] TASK-RA-025 本体补充：ENT-C8 管理员凭据、ENT-C9 登录会话、BR-C11 ~ BR-C13（BR-C11 取代 BR-C5）、BP-C4 单用户登录、TERM-C9 登录会话
- [x] TASK-RA-026 登录凭据来源 / 会话有效期 / 失败锁定阈值未从现有材料确定，按最小风险给出建议默认值并记入 `open-questions.md`（OQ-RA-01 ~ OQ-RA-03）
- [x] TASK-RA-027 用户 2026-11-17 19:58:08 对 OQ-RA-01 ~ OQ-RA-03 全选 A：转为 AMB-011 / AMB-012 / AMB-013 回填「需求澄清」表，并更新 AC-011-2/4/5、AC-REQ-14/15 与新增 AC-REQ-17（凭据来源）、非功能需求、`design.md` 决策 6、`docs/context.md` 与 `open-questions.md`
- [x] TASK-RA-034 更新 `_shared/domain-map.md`：新增 `ontology-builder` 域（未开始，依赖 workbench-core 的 AI 网关 / 会话 / 制品 / 人工确认）与共享数据约定
- [x] TASK-RA-039 入口更名回填（AMB-019）：六入口之一「生成测试用例」更名为「用例库」，生成能力作为入口内部功能；同步 In Scope 入口清单、AC-001-1、US-001/US-002 相关表述、`design.md` 竞品对照、`docs/context.md` 入口摘要、`docs/flowchart.md` 入口命名说明与 `_shared/ontology/glossary.md`（TERM-C13 取代 TERM-C1）


## 交接给后续阶段

- [ ] TASK-RA-018 交互设计：首页入口 + 最近会话、占位页、提供商配置、会话详情时间线、上传交互、调用记录页
- [ ] TASK-RA-019 技术方案：`ai.complete` 接口契约、密钥加密与掩码、会话/制品持久化选型、文件落盘与路径安全（含同名改名与批次数上限）
- [ ] TASK-RA-020 技术方案：确认 `ai.complete` 与制品写入接口的向后兼容扩展方式（后续 4 域共用）
- [ ] TASK-RA-021 测试验证：为本 spec 的 42 条 AC 生成用例（拆分前为 66 条），重点覆盖登录前置校验、未认证访问、口令错误与连续失败锁定、会话过期与登出、令牌 Cookie 属性、凭据不落日志、密钥掩码、路径穿越、超限上传、同名改名、120s 超时与 1 次重试、级联删除
