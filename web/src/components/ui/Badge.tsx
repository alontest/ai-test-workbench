import styles from "./ui.module.css";

type Status = "in_progress" | "completed" | "failed" | "planned" | "live";

export interface BadgeProps {
  label: string;
  tone?: "neutral" | "success" | "danger" | "info" | "warning";
}

export function Badge({ label, tone = "neutral" }: BadgeProps) {
  const toneClass =
    tone === "success"
      ? styles.badgeSuccess
      : tone === "danger"
        ? styles.badgeDanger
        : tone === "info"
          ? styles.badgeInfo
          : tone === "warning"
            ? styles.badgeWarning
            : "";
  return <span className={[styles.badge, toneClass].filter(Boolean).join(" ")}>{label}</span>;
}

export interface StatusPillProps {
  status: Status;
  size?: "sm" | "md";
}

const STATUS_LABEL: Record<Status, string> = {
  in_progress: "进行中",
  completed: "已完成",
  failed: "失败",
  planned: "规划中",
  live: "已上线",
};

const STATUS_TONE: Record<Status, BadgeProps["tone"]> = {
  in_progress: "info",
  completed: "success",
  failed: "danger",
  planned: "neutral",
  live: "success",
};

export function StatusPill({ status }: StatusPillProps) {
  return <Badge label={STATUS_LABEL[status]} tone={STATUS_TONE[status]} />;
}
