import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";

export type ConnectionTestState =
  | "idle"
  | "testing"
  | "success"
  | "auth-error"
  | "unreachable"
  | "timeout"
  | "credential-unavailable";

export interface ConnectionTestBadgeProps {
  state: ConnectionTestState;
  result?: {
    ok: boolean;
    latencyMs: number;
    modelCount?: number | null;
    errorCode?: string | null;
  };
  onTest: () => void;
  disabled?: boolean;
}

const STATE_LABEL: Record<ConnectionTestState, string> = {
  idle: "测试连接",
  testing: "测试中",
  success: "连接成功",
  "auth-error": "鉴权失败",
  unreachable: "网络不可达",
  timeout: "超时",
  "credential-unavailable": "凭据不可用",
};

export function mapConnectionState(
  result: ConnectionTestBadgeProps["result"] | undefined,
): ConnectionTestState {
  if (!result) {
    return "idle";
  }
  if (result.ok) {
    return "success";
  }
  switch (result.errorCode) {
    case "auth":
      return "auth-error";
    case "unreachable":
      return "unreachable";
    case "timeout":
      return "timeout";
    case "credential_unavailable":
      return "credential-unavailable";
    default:
      return "auth-error";
  }
}

export function ConnectionTestBadge({
  state,
  result,
  onTest,
  disabled,
}: ConnectionTestBadgeProps) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <Button
        type="button"
        variant="secondary"
        onClick={onTest}
        disabled={disabled || state === "testing"}
      >
        测试连接
      </Button>
      {state !== "idle" ? (
        <Badge
          label={
            state === "success" && result?.latencyMs != null
              ? `${STATE_LABEL[state]} ${result.latencyMs}ms`
              : STATE_LABEL[state]
          }
          tone={
            state === "success"
              ? "success"
              : state === "testing"
                ? "info"
                : "danger"
          }
        />
      ) : null}
    </div>
  );
}
