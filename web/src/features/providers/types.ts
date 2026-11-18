export interface Provider {
  providerId: number;
  name: string;
  protocol: "openai_compatible" | "anthropic" | string;
  baseUrl: string;
  apiKeyMasked: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ProviderDraft {
  name: string;
  protocol: string;
  baseUrl: string;
  apiKey: string;
  enabled: boolean;
}

export interface ConnectionTestResult {
  ok: boolean;
  latencyMs: number;
  modelCount?: number | null;
  errorCode?: string | null;
}
