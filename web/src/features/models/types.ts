export interface ModelBinding {
  modelId: number;
  providerId: number;
  modelName: string;
  displayName: string;
  defaultTemperature: number;
  defaultMaxTokens: number;
  enabled: boolean;
  createdAt: string;
  provider?: {
    providerId: number;
    name: string;
    enabled: boolean;
  };
}

export interface ModelDraft {
  modelName: string;
  displayName: string;
  defaultTemperature: string;
  defaultMaxTokens: string;
  enabled: boolean;
}
