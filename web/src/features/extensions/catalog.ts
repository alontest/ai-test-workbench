export interface PlannedExtension {
  key: "skills" | "mcp" | "approvals" | "history";
  name: string;
  capabilityId: string;
  description: string;
  targetPhase: string;
  summary: string;
  workflowSteps: readonly string[];
  guardrails: readonly string[];
  docRef: string;
}

export const PLANNED_EXTENSIONS: readonly PlannedExtension[] = [
  {
    key: "skills",
    name: "QA 技能库",
    capabilityId: "qa-skills",
    description:
      "沉淀团队测试方法论（Markdown + frontmatter）：人类编写或导入初版，日常通过会话 Chat 让 Agent 协助迭代，经 Diff 审批后落盘。",
    targetPhase: "随 test-case（用例域）立项起步",
    summary:
      "把用例规范、慢 SQL 排查手册、报告模板从后端硬编码 prompt 中抽离为可演进资产；与知识库分工清晰——知识库存业务事实，技能库存 QA 流程。",
    workflowSteps: [
      "01 人工编写或导入 v0 初版",
      "02 会话内 Chat 让 Agent 提 Diff 提案",
      "03 审批落盘并记录版本历史",
    ],
    guardrails: [
      "支持 global 默认 + projectId 项目覆盖两层作用域，不平铺共享",
      "禁止 Agent 在对话中静默新建或覆写 Skill，必须经过 Diff 确认",
      "迭代优先走 Patch/Edit，新建提案时提示同域相似 Skill 防止多胞胎膨胀",
    ],
    docRef: "docs/platform-capabilities.md",
  },
  {
    key: "mcp",
    name: "MCP 工具源",
    capabilityId: "mcp-registry",
    description:
      "受控接入外部日志库、只读数据库、工单系统与本体执行服务，按项目授权可用工具子集。",
    targetPhase: "随 diagnosis（Bug / 日志 / SQL 诊断域）立项落地",
    summary:
      "用统一 HTTP / SSE MCP 协议替代为每家公司手写私有适配器，让诊断与分析会话安全按需拉取外部上下文。",
    workflowSteps: [
      "01 注册 MCP Server 并加密托管凭证",
      "02 拉取工具清单并按项目授权白名单",
      "03 会话按只读策略调用（写操作进审批）",
    ],
    guardrails: [
      "认证 Header / Token 由 workbench-core 使用 AES-256-GCM 加密存储并掩码回显",
      "按 projectId 隔离与授权绑定，复用 repo-integration 的 SSRF 网络边界校验",
      "默认只读；写操作或服务端返回 AUTH_REQUIRED 时强制转交审批中心",
    ],
    docRef: "docs/platform-capabilities.md",
  },
  {
    key: "approvals",
    name: "审批中心",
    capabilityId: "approvals",
    description:
      "高危外部写操作与平台资产变更的统一人工确认闸门，覆盖 Pending / Executed / Failed / Rejected 全生命周期。",
    targetPhase: "轻量版随 test-case 起步；完整版随外部回写 / ontology-builder 补全",
    summary:
      "无论是 Agent 在对话里提交的 Skill 修订 Diff，还是将用例回写外部平台、诊断提 Bug 单，均先落入审批池展示完整明细，人点通过才执行。",
    workflowSteps: [
      "01 Agent 生成变更 Diff 或外部写请求",
      "02 人工核对上下文与风险级别",
      "03 批准执行或驳回并回流会话",
    ],
    guardrails: [
      "审批单强制关联 sessionId、目标对象、完整 Diff 或请求载荷，杜绝黑盒授权",
      "状态机严格区分 pending / approved / executed / failed / rejected / expired",
      "每次批准执行自动关联写入变更审计流水",
    ],
    docRef: "docs/platform-capabilities.md",
  },
  {
    key: "history",
    name: "变更审计",
    capabilityId: "asset-history",
    description:
      "记录 QA 技能、知识库、用例与本体资产的每次变更流水、Unified Diff 与一键回滚。",
    targetPhase: "与审批中心同步分期落地",
    summary:
      "与基座已有的 AiCallRecord（模型调用审计）互补，专门解决「资产何时被谁改了什么、改坏了怎么一键撤回」。",
    workflowSteps: [
      "01 采集资产创建/修改/删除事件",
      "02 展开 Unified Diff 并跳转关联会话",
      "03 一键 Rollback 追加恢复版本",
    ],
    guardrails: [
      "清晰区分人工直接编辑与 Agent 提案经审批两类操作来源",
      "一键回滚生成类型为 rollback 的新记录，绝不篡改或抹除既有历史",
      "所有审计表严格遵守 MySQL 8.4 + SQLite 双方言纪律",
    ],
    docRef: "docs/platform-capabilities.md",
  },
] as const;

export function findPlannedExtension(
  key: string | undefined,
): PlannedExtension | undefined {
  return PLANNED_EXTENSIONS.find((item) => item.key === key);
}
