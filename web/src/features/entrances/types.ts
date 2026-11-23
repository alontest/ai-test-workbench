type EntranceStatus = "planned" | "live";

export interface Entrance {
  key: string;
  name: string;
  description: string;
  domain: string;
  status: EntranceStatus;
}

export const DOMAIN_LABEL: Record<string, string> = {
  "test-case": "用例域",
  diagnosis: "诊断域",
  "regression-list": "回归清单域",
  "test-report": "测试报告域",
};
