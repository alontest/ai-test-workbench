# Requirements Analysis — Tasks

## 本阶段已完成

> 编号策略：TASK-RA-028 ~ 033、035 ~ 038 为从父 spec 迁入的原编号（按本 spec 范围重述任务内容，原描述见 `_handoff/from-workbench-core.md` §9）；新增任务接续父 spec 已用编号（至 TASK-RA-052），从 TASK-RA-053 起编，避免跨 spec 混淆。

- [x] TASK-RA-028 读取 intake 与原始需求，确认需求类型为 ➕ 功能新增、范围为 `knowledge-base` 单域，按 intake 执行路径裁剪 skill 链
- [x] TASK-RA-029 MoSCoW 优先级矩阵：P0 = US-012 / US-013 / US-014，P1 = US-015 / US-016；Won't 明确排除在线编辑、代码级新鲜度、向量检索、本体生成、自动过期（`design.md`）
- [x] TASK-RA-030 功能规格：问题陈述、目标、非目标、FR-01 ~ FR-08 与成功指标；沿用父 spec 产品级结论，不重跑市场与竞品研究（`requirements.md` / `design.md`）
- [x] TASK-RA-031 需求澄清承接：AMB-006（知识库部分）与 AMB-014 ~ AMB-018 按已确认口径迁入，依据引用父 spec `answers.md` 原话
- [x] TASK-RA-032 用户故事承接：US-012 ~ US-016 与 24 条 AC（AC-012-1 ~ AC-016-3）、7 条 EARS（AC-REQ-18 ~ AC-REQ-24）原编号逐字迁入
- [x] TASK-RA-033 业务流程图：US-012 ~ US-016 五张 mermaid 图迁入 `docs/flowchart.md`，按 AC 原文补齐拒绝、回滚、版本跳转与失效条目分支
- [x] TASK-RA-035 本体补充（首次建立）：TERM-C10 ~ TERM-C13、ENT-C10 / ENT-C11、BR-C15 ~ BR-C20、BP-C5 ~ BP-C8 写入 `_shared/ontology/`，「对应图谱」标「未覆盖」
- [x] TASK-RA-036 编写 `docs/context.md`：需求类型、下游执行路径、In/Out of Scope、US 摘要、AC 完整清单、数据实体、系统集成点与关键约束
- [x] TASK-RA-037 与 workbench-core 的依赖边界对齐：`projectId`、`AiGateway.complete`、`sessions.*`、`artifacts.save`、登录态与设计 token；200,000 常量单点归 core，本 spec 只引用
- [x] TASK-RA-038 跨 spec 口径核对：知识库文件限额（20MB / 10MB / 50 个 / 100MB）与 handoff 原文一致，无冲突；7 项「待技术方案」原样保留标注
- [x] TASK-RA-053 需求澄清新增项：识别 AC-014-4 与 tech-arch §5 / 交互 handoff §3.6 的失效条目口径冲突，登记 AMB-026；登记 AMB-027（单次注入条目数上限）并给出建议默认值（`open-questions.md`）
- [x] TASK-RA-054 阶段自检：`python3 .aw/aw.py check specs/knowledge-base_20261117205011 --phase requirements-analysis`，首轮仅 AMB-026 / AMB-027 待确认，其余产物齐全
- [x] TASK-RA-059 回填用户 2026-11-18 10:44:10 的答复：AMB-026 改为「剔除失效条目 + 阻塞式确认后继续」并据此改写 AC-014-4（保留原编号、记录修正理由），AMB-027 确认不另设条目数上限；同步 `design.md`（决策 18）、`docs/context.md`、`docs/flowchart.md`（US-014）与 `open-questions.md`

## 交接给后续阶段

- [ ] TASK-RA-055 交互设计：复核并落地 5 处知识库页面（列表 / 导入 / 浏览 / 条目详情 / 会话注入面板），复用 core 的 AppShell、设计 token 与登录态；补齐 AC-UX 与组件状态
- [ ] TASK-RA-056 技术方案：复核 `_handoff/from-tech-arch.md` 的表结构、索引、接口签名、解析护栏与检索方案；对 7 项「待技术方案」逐条给出结论（含与 core 的进程内接口归属、存储布局与删除事务边界）
- [ ] TASK-RA-057 技术方案：确认 `index.json` 字段与向下兼容策略、`.md` 与条目匹配规则、注入块最终拼装格式与字符口径（Unicode 码点）
- [ ] TASK-RA-058 测试验证：为 24 条 AC 与 7 条 EARS 生成 TC，重点覆盖导入边界与整体回滚、路径穿越与巨型 JSON、注入预算边界（含标题与分隔符）、失效条目、删除后历史可读、日志与错误体无正文
