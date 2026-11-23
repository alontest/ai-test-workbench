export interface PlannedExtension {
  key: "mcp" | "history";
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
      "认证 Header / Token 由 vigil-core 使用 AES-256-GCM 加密存储并掩码回显",
      "按 projectId 隔离与授权绑定，复用 repo-integration 的 SSRF 网络边界校验",
      "默认只读；写操作或服务端返回 AUTH_REQUIRED 时强制转交审批中心",
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
