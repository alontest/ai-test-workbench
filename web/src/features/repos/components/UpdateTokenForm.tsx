import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import { isApiError } from "../../../lib/api/errors";
import type { RepoBindingSummary, RepoConnectionTestInput } from "../api/types";
import { PROVIDER_LABELS } from "../api/types";
import { useUpdateRepoToken } from "../hooks/useRepoBindings";
import { useTestRepoConnection } from "../hooks/useRepoConnectionTest";
import styles from "./repo.module.css";
import type { RepoTestSnapshot } from "./TestResultStrip";
import { TestResultStrip } from "./TestResultStrip";
import { TokenField } from "./TokenField";

export interface UpdateTokenFormProps {
  binding: RepoBindingSummary;
  open: boolean;
  onClose: () => void;
  onSaved: (binding: RepoBindingSummary) => void;
}

export function UpdateTokenForm({
  binding,
  open,
  onClose,
  onSaved,
}: UpdateTokenFormProps) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [last, setLast] = useState<RepoTestSnapshot | null>(null);
  const [stale, setStale] = useState(false);
  const test = useTestRepoConnection();
  const update = useUpdateRepoToken(binding.bindingId, binding.projectId);

  if (!open) {
    return null;
  }

  function onChange(next: string) {
    setToken(next);
    setGeneralError(null);
    if (last) {
      setStale(true);
    }
  }

  function toInput(): RepoConnectionTestInput {
    return {
      provider: binding.provider,
      repoIdentifier: binding.repoName,
      orgId: binding.orgId,
      apiBaseUrl: binding.apiBaseUrl,
      token,
    };
  }

  async function onTest() {
    if (!token) {
      setGeneralError("请先填写新令牌再测试。");
      return;
    }
    setStale(false);
    setGeneralError(null);
    try {
      const result = await test.mutateAsync({ input: toInput() });
      setLast({
        result: result.result,
        testedAt: result.testedAt,
        message: result.message,
        retryAfterAt: result.retryAfterAt,
      });
    } catch (caught) {
      setGeneralError(
        isApiError(caught) ? caught.message : "测试连接失败，请稍后重试。",
      );
    }
  }

  async function onSave() {
    setError(null);
    setGeneralError(null);
    try {
      const next = await update.mutateAsync(token);
      onSaved(next);
      onClose();
    } catch (caught) {
      if (isApiError(caught)) {
        setError(caught.fieldError("token") ?? null);
        if (!caught.fieldError("token")) {
          setGeneralError(caught.message);
        }
      } else {
        setGeneralError("保存失败，请重试。");
      }
    }
  }

  return (
    <div className={styles.formCard} data-testid="update-token-form">
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.formTitle}>更新访问令牌</h3>
          <p className={styles.muted}>
            只替换加密令牌与掩码；bindingId、已同步元数据与历史记录不变。
          </p>
        </div>
        <Button type="button" variant="ghost" onClick={onClose}>
          关闭
        </Button>
      </div>

      <p className={styles.rowMeta}>
        <span>{PROVIDER_LABELS[binding.provider]}</span>
        <span className={styles.mono}>{binding.repoName}</span>
        <span className={styles.muted}>
          当前令牌 <span className={styles.mono}>{binding.tokenMasked || "—"}</span>
        </span>
      </p>

      <TokenField
        value={token}
        onChange={onChange}
        mode="update"
        masked={binding.tokenMasked}
        error={error ?? undefined}
      />

      <TestResultStrip
        testing={test.isPending}
        last={last}
        stale={stale}
        onTest={() => void onTest()}
        disabled={update.isPending}
      />

      {generalError ? (
        <p className={styles.bannerError} role="alert">
          {generalError}
        </p>
      ) : null}

      <div className={styles.formFoot}>
        <span className={styles.muted}>留空表示不修改。</span>
        <div className={styles.actionsInline}>
          <Button type="button" variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button
            type="button"
            onClick={() => void onSave()}
            loading={update.isPending}
            disabled={!token}
          >
            保存令牌
          </Button>
        </div>
      </div>
    </div>
  );
}
