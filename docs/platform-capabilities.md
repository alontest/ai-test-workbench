# 平台级扩展能力规划（路线图与架构约束）

> 决策日期：2026-11-21（Asia/Shanghai）
> 性质：跨业务域的平台级支撑能力规划（尚未正式立项；落地时按对应阶段补全各自 spec 与 ADR）。
> 来源：结合对 Billing Agent 的产品调研（界面与资产结构观察）与 Vigil · 鸮巡「多项目、强约束、可复现、可审计」的基座原则，提炼出的 4 项规划能力与 4 项明确排除项。

## 一、核心原则：为什么这四项是一个闭环

Vigil 是面向多项目的通用 QA 工作台，而非单业务域的开放式自进化 Agent。引入扩展能力必须同时守住两条底线：

1. **体验不僵化**：团队方法论（QA Skill）不可能靠人一直手改 Markdown 维护——人类顶多写初版（v0），后续日常迭代必须支持**在会话里通过 Chat 让 Agent 协助修改、补全与精炼**。
2. **演进不失控**：不允许 Agent 在对话过程中静默新建/覆写资产，也不允许 Agent 运行时直接执行自写 Python 脚本或未经确认的外部写操作。

因此，四项规划能力不是四个孤立页面，而是一套协同闭环：

```
人类编写/导入初版（v0）
        │
        ▼
  会话内 Chat 协作（Agent 提出 Skill / 资产变更提案，或外部写操作请求）
        │
        ▼
  生成结构化 Diff / 请求明细 ──► 审批中心（Approvals）人工确认
        │                                  │
        │ 批准                              │ 驳回（不落盘、不执行）
        ▼                                  ▼
  写入新版本 / 执行受控动作              保留审计记录
        │
        ▼
  变更审计（Asset History）记录操作流水、完整 Diff 与一键 Rollback
```

同时，面向日志库、数据库、工单系统、本体服务等异构外部系统，统一通过 **受控 MCP 工具源** 接入，避免为每家公司重复手写私有适配器。

---

## 二、四项待规划能力

### 1. QA 技能库（`qa-skills`）— 初版人工定型 + 对话式 Agent 迭代

- **定位**：将 6 大 QA 入口的方法论（用例编写规范、接口/UI 测试模板、慢 SQL 排查手册、Bug 定位清单、测试报告格式等）从后端硬编码 prompt 中抽离为可配置、可演进的 Markdown + YAML frontmatter 技能资产。
- **与知识库的分工**：
  - `knowledge-base` 存**业务事实与规则**（术语、实体、状态、业务规则、API 契约）；
  - `qa-skills` 存**QA 执行流程与方法论**（步骤、检查项、输出结构、触发条件）。
- **核心生命周期**：
  1. **v0 初版建立**：人工编写、选用内置模板，或从 Git 仓库导入初版 Skill（含 frontmatter：`name`、`domain`、`scope`、`triggers`、`version`）。
  2. **Chat 对话式迭代**：用户在分析会话中直接提出修订意图（例如「把刚才漏掉的幂等与并发检查补进接口用例 Skill」），Agent 基于当前 Skill 正文与上下文生成**结构化变更提案**（目标 Skill ID、修改理由、Unified Diff、受影响入口）。
  3. **审批落盘**：提案自动进入审批中心（会话内可直接展开 Diff 预览并点击批准/驳回）；审批通过后才生成新版本，**禁止 Agent 静默覆写或后台自动创建新 Skill**。
  4. **版本回滚**：每次生效写入资产变更审计，改坏可一键回退到任意历史版本。
- **防腐化约束**：
  - 迭代已有规范优先走 Patch/Edit，不鼓励因细微差异裂变新文件；
  - 提案新建 Skill 时，系统展示同域已有相似 Skill 提醒，防止出现多胞胎重复技能。
- **作用域**：两层模型——`global`（工作台默认方法论）+ `project`（按 `projectId` 覆盖或扩展，禁止单空间平铺）。
- **数据模型草案**（立项时细化）：`qa_skill`（id、project_id 可空、slug、domain、title、current_version、status）、`qa_skill_version`（id、skill_id、version、frontmatter_json、body_md、source_type[human/agent_proposal/git_import/rollback]、approval_id、created_at）。
- **计划落地阶段**：随 `test-case` 域立项一起落地最小闭环（先支撑用例生成规范，再复用到其余 5 个入口）。

### 2. 受控 MCP 工具源（`mcp-registry`）— 外部数据与工具接入层

- **定位**：Vigil 对接外部日志平台、只读数据库、需求/缺陷工单系统（Jira / 飞书 / 云效项目等）与本体执行服务的统一扩展协议层。
- **核心能力**：
  - 支持 HTTP / SSE MCP Server 注册、编辑、启停、连通性测试；
  - 一键拉取并缓存工具清单（`tools/list`），展示工具说明、入参 Schema 与读写属性标签；
  - 按 `projectId` 绑定可用 Server 与工具白名单，在对应入口或会话中受控调用。
- **架构与安全红线**：
  - **多项目隔离**：支持全局托管 + 项目级授权绑定，不允许跨项目隐式共享敏感连接；
  - **凭证集中加密**：自定义 Header（如 `Authorization`、`X-Token`）与认证密钥只能由 `workbench-core` 使用 **AES-256-GCM** 加密存储，接口响应与前端页面一律掩码脱敏，绝不明文展示；
  - **默认只读**：工具默认按只读策略执行；标记为写操作或服务端返回 `AUTH_REQUIRED` 授权挑战的调用，必须拦截并路由至审批中心；
  - **SSRF 防护**：复用 `repo-integration` 的网络边界策略（公网解析校验或显式配置的内部白名单，禁止任意内网探测）。
- **计划落地阶段**：随 `diagnosis` 域（Bug 分析 / 日志排查 / SQL 分析）立项落地。

### 3. 审批中心（`approvals`）— 高危动作与资产变更确认闸门

- **定位**：所有「会改写平台核心资产」或「会对外部系统产生副作用」的操作的统一人工审批池。
- **统一状态机**：
  - `pending` → `approved` → `executed` / `failed`
  - `pending` → `rejected` / `expired`
- **覆盖两类动作**：
  1. **平台资产变更**：Agent 对话中提交的 QA Skill 新建/修改提案、知识库批量修订提案、本体草稿确认落盘；
  2. **外部写操作**：将 AI 生成的用例回写到团队用例库、将诊断结论提成 Bug 单、执行带写权限的 MCP 工具或测试环境写请求。
- **详情与体验要求**：
  - 审批单必须展示完整上下文：关联 `sessionId`、触发来源、目标对象、风险等级、**完整 Unified Diff（资产类）或完整请求明细（外部调用类）**；
  - 支持在会话内直接完成快捷确认（底部卡片/抽屉），同时在独立审批中心提供待办筛选、批量查看与历史回溯；
  - 驳回可填写意见并回流当前会话，方便 Agent 按反馈重拟方案。
- **计划落地阶段**：
  - **第一期（轻量版）**：随 `test-case` 域起步，承接 QA Skill 的 Chat Diff 审批；
  - **第二期（完整版）**：随外部写操作回写 / `ontology-builder` 补齐外部请求执行器与失败重试审计。

### 4. 变更审计（`asset-history`）— 资产变更流水、Diff 与一键回滚

- **定位**：与基座已有的 `AiCallRecord`（记录模型怎么调）、`SessionEvent`（记录会话过程）互补，专门回答**「平台资产何时被谁改了什么、改坏了怎么一键恢复」**。
- **记录要素**：
  - `opId`、项目 `projectId`、操作类型（`create` / `modify` / `delete` / `rollback`）；
  - 资产类型（`qa_skill` / `knowledge_entry` / `test_case` / `ontology` / `mcp_server`）与目标标识；
  - 关联 `sessionId` 与 `approvalId`、操作来源（人工直接编辑 / Agent 提案经审批）；
  - 变更前后内容快照或 Unified Diff、字节数、时间戳。
- **核心能力**：
  - 按项目、资产类型、操作类型、关联会话筛选；
  - 行内展开查看 Diff，并与 `AiCallRecord` / `Session` 双向跳转；
  - **一键 Rollback**：生成一条类型为 `rollback` 的新变更记录恢复目标版本，绝不篡改或抹除既有历史。
- **计划落地阶段**：与 `approvals` 同步分期落地（先接 QA Skill 与用例变更，后续接入知识库更新、MCP 配置与本体修订）。

---

## 三、明确不做（反模式备忘）

以下能力经评估与 Vigil 定位冲突或投入产出比过低，**现阶段明确不引入**，后续若要重开必须走正式架构评审：

| 排除项 | 排除原因 | 替代方案 |
|---|---|---|
| Agent 运行时自写/执行任意 Python 工具（`create_tool`） | 开源通用平台难以守住代码执行与数据库访问安全边界；且极易产生重复工具腐化（同类工具多胞胎并存） | 固定核心域 + 受控 MCP 工具源 + 经审批迭代的 QA Skill |
| 动态 UI 组件生成器（Components）、画布工作流（Workflows）、定时任务（Schedules） | 建设与维护成本高，实际使用率低；与 Vigil 强场景化 QA 工作台定位不符 | 聚焦打磨 6 大核心 QA 入口的结构化交互 |
| 插件市场（Marketplace） | 核心业务域尚未全部 live，过早抽象无实际生态支撑 | 后续仅在 `qa-skills` 提供「从 Git 仓库导入 Markdown Skill」轻入口 |
| 单空间全局平铺模型 | 无法隔离多项目的知识库、凭证、MCP 连接与团队规范 | 所有扩展资产一律显式归属 `global` 或 `projectId` |

---

## 四、分期落地节奏与前端占位

| 阶段 | 主线业务域 | 同步落地的平台能力 | 前端占位路由 |
|---|---|---|---|
| **当前** | `repo-integration` 验收与收尾 | 仅保留文档规划与前端「规划中」占位页，不改核心表结构 | `/extensions/skills`、`/extensions/mcp`、`/extensions/approvals`、`/extensions/history` |
| **阶段 1** | `test-case`（用例域） | `qa-skills`（v0 + Chat 提案 Diff）+ `approvals` 轻量版 + `asset-history` 轻量版 | `/extensions/skills`、`/extensions/approvals`、`/extensions/history` 逐步转 live |
| **阶段 2** | `diagnosis`（Bug / 日志 / SQL 诊断） | `mcp-registry`（受控外部数据源 + 凭证加密 + 只读/写分级） | `/extensions/mcp` 转 live |
| **阶段 3** | 外部回写 / `ontology-builder` | `approvals` 完整外部写执行器 + `asset-history` 覆盖知识库与本体修订 | 全部平台扩展能力闭环 |

## 五、立项前需守住的基座不变量

以上 4 项能力后续立项写 spec 时，必须继承 `AGENTS.md` 中的全部基座不变量：
- **模型出口唯一**：Chat 迭代 Skill 时仍只走 `AiGateway.complete`，遵守 120s 超时、200,000 字符预算与 `AiCallRecord` 审计；
- **凭证集中加密**：MCP Server 认证头与密钥只能由 `workbench-core` 加密托管并掩码回显；
- **双方言纪律**：任何新增表（Skill、MCP、Approval、AssetHistory）必须同时兼容 MySQL 8.4 与 SQLite，大文本用 `Text().with_variant(MEDIUMTEXT, "mysql")`，迁移按版本号顺序追加。
