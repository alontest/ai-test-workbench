import { Badge } from "../../../components/ui/Badge";

export interface KbDeletedBadgeProps {
  kbName?: string;
}

export function KbDeletedBadge({ kbName }: KbDeletedBadgeProps) {
  return <Badge label={kbName ? `${kbName} · 知识库已删除` : "知识库已删除"} />;
}
