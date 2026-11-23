export type CallStatus = "success" | "failed" | "timeout" | "running";

interface KnowledgeInjectionItem {
  kbId: number;
  kbName: string;
  kbVersion: number;
  entryCodes: string[];
  injectedChars: number;
  kbDeleted: boolean;
}

export interface CallRecord {
  callId: number;
  sessionId: number;
  project: { projectId: number; name: string };
  model: { modelId: number; displayName: string; providerName: string };
  status: CallStatus;
  promptPreview: string;
  promptCharCount: number;
  knowledgeInjection: KnowledgeInjectionItem[] | null;
  latencyMs: number | null;
  retryCount: number;
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
  finishedAt: string | null;
}

export interface CallDetail extends CallRecord {
  resultText: string | null;
}

export interface CallFiltersValue {
  projectId: string;
  sessionId: string;
  status: string;
  from: string;
  to: string;
}
