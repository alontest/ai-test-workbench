import { counterState } from "../../composer/CharacterCounter";
import { formatChars } from "../format";
import styles from "./knowledge.module.css";

export interface KbCharBudgetProps {
  itemCount: number;
  promptChars: number;
  injectedChars: number;
  limit: number;
  /** 预览尚未返回时的本地提示，不影响最终判定。 */
  pending?: boolean;
}

export function KbCharBudget({
  itemCount,
  promptChars,
  injectedChars,
  limit,
  pending = false,
}: KbCharBudgetProps) {
  const total = promptChars + injectedChars;
  const state = counterState(total, limit);
  const percent = limit > 0 ? Math.min(100, (total / limit) * 100) : 0;
  return (
    <div className={styles.stack} aria-live="polite">
      <p className={styles.muted}>
        已选 {itemCount} 条 · 注入 {formatChars(injectedChars)} 字符 · 提示{" "}
        {formatChars(promptChars)} 字符
        {pending ? " · 正在预览…" : ""}
      </p>
      <div className={styles.budgetTrack}>
        <div
          className={[
            styles.budgetFill,
            state === "warning" ? styles.budgetFillWarning : "",
            state === "exceeded" ? styles.budgetFillExceeded : "",
          ]
            .filter(Boolean)
            .join(" ")}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className={styles.muted}>
        合计 {formatChars(total)} / {formatChars(limit)} 字符
      </p>
      {state === "warning" ? (
        <p className={styles.bannerWarning} role="status">
          已接近字符上限（{formatChars(limit)}）。
        </p>
      ) : null}
      {state === "exceeded" ? (
        <p className={styles.bannerError} role="alert">
          超出上限 {formatChars(total - limit)} 字符，不会截断；请减少勾选或缩短提示。
        </p>
      ) : null}
    </div>
  );
}
