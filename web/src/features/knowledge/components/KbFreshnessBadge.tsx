import { Badge } from "../../../components/ui/Badge";
import type { FreshnessState } from "../api/types";
import { FRESHNESS_LABELS, formatTimestamp } from "../format";

export interface KbFreshnessBadgeProps {
  state: FreshnessState;
  at?: string | null;
}

export function KbFreshnessBadge({ state, at }: KbFreshnessBadgeProps) {
  const label =
    state === "unknown"
      ? FRESHNESS_LABELS.unknown
      : `${FRESHNESS_LABELS[state]} · ${formatTimestamp(at)}`;
  return <Badge label={label} tone={state === "stale" ? "warning" : "neutral"} />;
}
