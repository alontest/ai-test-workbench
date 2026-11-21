import { Button } from "../../../components/ui/Button";
import type { RepoBindingSummary } from "../api/types";
import styles from "./repo.module.css";

export interface TokenInvalidBannerProps {
  bindings: RepoBindingSummary[];
  onRefill: (bindingId: string) => void;
  onViewBaseline: (bindingId: string) => void;
}

/**
 * 页面级唯一聚合横幅：同一绑定只出现一次，
 * 失效不等于删除，基线快照仍可查看。
 */
export function TokenInvalidBanner({
  bindings,
  onRefill,
  onViewBaseline,
}: TokenInvalidBannerProps) {
  const invalid = bindings.filter((binding) => binding.status === "token_invalid");
  if (invalid.length === 0) {
    return null;
  }
  return (
    <div className={styles.bannerError} role="alert" data-testid="token-invalid-banner">
      <strong>令牌失效或权限不足，请重新填写。</strong>
      <ul className={styles.bannerList}>
        {invalid.map((binding) => (
          <li key={binding.bindingId}>
            <span className={styles.mono}>{binding.repoName}</span>
            <span className={styles.actionsInline}>
              <Button
                type="button"
                variant="ghost"
                onClick={() => onRefill(binding.bindingId)}
              >
                重新填写令牌
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => onViewBaseline(binding.bindingId)}
              >
                查看基线快照
              </Button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
