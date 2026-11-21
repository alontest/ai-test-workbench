import {
  ConnectionTestBadge,
  type ConnectionTestState,
} from "../../providers/ConnectionTestBadge";
import type { RepoTestResult } from "../api/types";
import { REPO_TEST_RESULT_LABELS } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./repo.module.css";

export interface RepoTestSnapshot {
  result: RepoTestResult;
  testedAt: string;
  message: string;
  retryAfterAt: string | null;
}

export interface TestResultStripProps {
  testing: boolean;
  last: RepoTestSnapshot | null;
  stale: boolean;
  onTest: () => void;
  disabled?: boolean;
}

const NEXT_STEP: Record<RepoTestResult, string> = {
  success: "保存后状态为「已连接」。",
  "auth-error": "请重新填写令牌；保存前测试不落库。",
  "permission-denied":
    "请授予目标仓库 Contents / Metadata 只读权限（GitHub）或代码库读取权限（云效）。",
  unreachable: "请检查域名、DNS 与网络连通性后重试；未写同步记录。",
};

function toState(testing: boolean, last: RepoTestSnapshot | null, stale: boolean): ConnectionTestState {
  if (testing) {
    return "testing";
  }
  if (!last) {
    return "idle";
  }
  if (stale) {
    return "stale";
  }
  return last.result;
}

export function TestResultStrip({
  testing,
  last,
  stale,
  onTest,
  disabled,
}: TestResultStripProps) {
  const state = toState(testing, last, stale);
  const staleLabel =
    last && stale
      ? `已失效（${formatTimestamp(last.testedAt)} · ${REPO_TEST_RESULT_LABELS[last.result]}）`
      : undefined;
  return (
    <div className={styles.testStrip} data-testid="test-result">
      <ConnectionTestBadge
        state={state}
        onTest={onTest}
        disabled={disabled}
        label={staleLabel}
      />
      {testing ? (
        <span className={styles.muted}>正在发起一次只读请求，10s 内返回…</span>
      ) : last ? (
        <span className={styles.testDetail}>
          {formatTimestamp(last.testedAt)}
          {last.message ? ` · ${last.message}` : ""}
          {last.retryAfterAt ? ` · 限流至 ${formatTimestamp(last.retryAfterAt)}` : ""}
          <br />
          <span className={styles.muted}>
            {stale ? "表单字段已修改，请重新测试；上一次结果仅作参考。" : NEXT_STEP[last.result]}
          </span>
        </span>
      ) : (
        <span className={styles.muted}>一次只读请求 · 10s 超时 · 不落库</span>
      )}
    </div>
  );
}
