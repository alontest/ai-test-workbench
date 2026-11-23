export const queryKeys = {
  session: ["auth", "session"] as const,
  projects: ["projects"] as const,
  providers: ["providers"] as const,
  provider: (id: number) => ["providers", id] as const,
  providerModels: (id: number) => ["providers", id, "models"] as const,
  models: (filters?: { enabled?: boolean }) => ["models", filters] as const,
  sessions: (filters?: { projectId?: number; status?: string; limit?: number }) =>
    ["sessions", filters] as const,
  entrances: ["entrances"] as const,
  sessionDetail: (id: number) => ["sessions", id] as const,
  sessionEvents: (id: number) => ["sessions", id, "events"] as const,
  artifact: (id: number) => ["artifacts", id] as const,
  calls: ["calls"] as const,
  skills: (projectId?: number) => ["skills", projectId] as const,
  skill: (skillId: string) => ["skills", "detail", skillId] as const,
  approvals: (status?: string) => ["approvals", status] as const,
  testCases: (projectId: number, filters?: Record<string, unknown>) =>
    ["test-cases", projectId, filters] as const,
};
