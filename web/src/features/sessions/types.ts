export interface SessionSummary {
  sessionId: number;
  project: { projectId: number; name: string };
  entranceKey: string;
  title: string;
  status: "in_progress" | "completed" | "failed";
  model: {
    modelId: number;
    modelName: string;
    displayName: string;
    providerId: number;
    providerName: string;
  };
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
}

export interface EnabledModel {
  modelId: number;
  modelName: string;
  displayName: string;
  enabled: boolean;
  provider: { providerId: number; name: string; enabled: boolean };
}

export type SessionEventType =
  | "input_text"
  | "artifact"
  | "call"
  | "status_change"
  | "knowledge_injection";

export interface SessionEvent {
  eventId: number;
  sessionId: number;
  type: SessionEventType;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface InputTextPayload {
  title: string;
  text: string;
  charCount: number;
}

export interface CallEventPayload {
  callId: number;
  modelId: number;
  modelDisplayName: string;
  status: string;
  latencyMs: number;
  retryCount: number;
  promptPreview: string;
  errorCode: string | null;
}

export interface ArtifactEventPayload {
  artifactId: number;
  fileName: string;
  byteSize: number;
  mimeType: string;
  kind: string;
}

export interface StatusChangePayload {
  from: string;
  to: string;
  actor: string;
  at: string;
  reason: string | null;
}

export interface KnowledgeInjectionEventPayload {
  items: Array<{
    kbId: number;
    kbName: string;
    kbVersion: number;
    entryCodes: string[];
    injectedChars: number;
    kbDeleted?: boolean;
  }>;
  promptChars: number;
  injectedChars: number;
  totalChars: number;
  excludedCodes?: string[];
}
