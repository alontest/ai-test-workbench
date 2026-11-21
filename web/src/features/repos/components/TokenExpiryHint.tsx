import { Badge } from "../../../components/ui/Badge";
import { formatTimestamp } from "../format";

const EXPIRING_DAYS = 7;
const DAY_MS = 24 * 60 * 60 * 1000;

export interface TokenExpiryHintProps {
  expiresAt: string | null;
}

export function TokenExpiryHint({ expiresAt }: TokenExpiryHintProps) {
  if (!expiresAt) {
    return null;
  }
  const expires = new Date(expiresAt);
  if (Number.isNaN(expires.getTime())) {
    return null;
  }
  const remainingMs = expires.getTime() - Date.now();
  if (remainingMs <= 0) {
    return <Badge label={`令牌已于 ${formatTimestamp(expiresAt)} 过期`} tone="danger" />;
  }
  const remainingDays = Math.ceil(remainingMs / DAY_MS);
  if (remainingDays <= EXPIRING_DAYS) {
    return <Badge label={`即将过期 · ${remainingDays} 天`} tone="warning" />;
  }
  return (
    <span data-testid="token-expiry">
      令牌有效期至 {formatTimestamp(expiresAt)}
    </span>
  );
}
