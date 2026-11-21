import { Badge } from "../../../components/ui/Badge";
import type { RepoBindingStatus } from "../api/types";
import { REPO_BINDING_STATUS_LABELS } from "../api/types";
import styles from "./repo.module.css";

export type RepoStatus = RepoBindingStatus | "syncing";

const STATUS_TONE: Record<
  RepoStatus,
  "neutral" | "success" | "danger" | "info" | "warning"
> = {
  unverified: "neutral",
  connected: "success",
  token_invalid: "danger",
  revoked: "neutral",
  syncing: "info",
};

const STATUS_LABEL: Record<RepoStatus, string> = {
  ...REPO_BINDING_STATUS_LABELS,
  syncing: "同步中",
};

export interface RepoStatusBadgeProps {
  status: RepoStatus;
}

export function RepoStatusBadge({ status }: RepoStatusBadgeProps) {
  return (
    <span
      data-status={status}
      className={status === "revoked" ? styles.revokedBadge : undefined}
    >
      <Badge label={STATUS_LABEL[status]} tone={STATUS_TONE[status]} />
    </span>
  );
}
