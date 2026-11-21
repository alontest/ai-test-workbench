import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import { FormField } from "../../../components/ui/FormField";
import { Input } from "../../../components/ui/Input";
import { isApiError } from "../../../lib/api/errors";
import type {
  RepoBindingCreateInput,
  RepoBindingSummary,
  RepoProvider,
} from "../api/types";
import { DEFAULT_API_BASE_URL, PROVIDER_LABELS } from "../api/types";
import { useCreateRepoBinding } from "../hooks/useRepoBindings";
import { useTestRepoConnection } from "../hooks/useRepoConnectionTest";
import styles from "./repo.module.css";
import { ProviderSegmented } from "./ProviderSegmented";
import { RepoPermissionHint } from "./RepoPermissionHint";
import type { RepoTestSnapshot } from "./TestResultStrip";
import { TestResultStrip } from "./TestResultStrip";
import { TokenField } from "./TokenField";

interface Draft {
  provider: RepoProvider;
  repoIdentifier: string;
  orgId: string;
  apiBaseUrl: string;
  token: string;
}

type DraftErrors = Partial<Record<keyof Draft, string>>;

export interface RepoBindingFormProps {
  projectId: number;
  open: boolean;
  initial?: RepoBindingSummary;
  onClose: () => void;
  onSaved: (binding: RepoBindingSummary) => void;
}

function toDraft(initial?: RepoBindingSummary): Draft {
  return {
    provider: initial?.provider ?? "yunxiao",
    repoIdentifier: initial?.repoName ?? "",
    orgId: initial?.orgId ?? "",
    apiBaseUrl: initial?.apiBaseUrl ?? DEFAULT_API_BASE_URL.yunxiao,
    token: "",
  };
}

export function RepoBindingForm({
  projectId,
  open,
  initial,
  onClose,
  onSaved,
}: RepoBindingFormProps) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(initial));
  const [errors, setErrors] = useState<DraftErrors>({});
  const [last, setLast] = useState<RepoTestSnapshot | null>(null);
  const [stale, setStale] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const test = useTestRepoConnection();
  const create = useCreateRepoBinding(projectId);

  if (!open) {
    return null;
  }

  function patch<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setGeneralError(null);
    if (last) {
      setStale(true);
    }
  }

  function changeProvider(provider: RepoProvider) {
    setDraft((current) => ({
      ...current,
      provider,
      apiBaseUrl: DEFAULT_API_BASE_URL[provider],
    }));
    setGeneralError(null);
    if (last) {
      setStale(true);
    }
  }

  function toInput(): RepoBindingCreateInput {
    return {
      provider: draft.provider,
      repoIdentifier: draft.repoIdentifier.trim(),
      orgId: draft.provider === "yunxiao" ? draft.orgId.trim() || null : null,
      apiBaseUrl: draft.apiBaseUrl.trim() || null,
      token: draft.token,
    };
  }

  function validate(): DraftErrors {
    const next: DraftErrors = {};
    if (!draft.repoIdentifier.trim()) {
      next.repoIdentifier = "请填写仓库标识。";
    }
    if (draft.provider === "yunxiao" && !draft.orgId.trim()) {
      next.orgId = "云效需要组织 ID。";
    }
    if (!draft.token.trim()) {
      next.token = "请填写访问令牌。";
    }
    return next;
  }

  function applyApiFieldErrors(error: unknown): boolean {
    if (!isApiError(error)) {
      return false;
    }
    const next: DraftErrors = {};
    for (const key of [
      "provider",
      "repoIdentifier",
      "orgId",
      "apiBaseUrl",
      "token",
    ] as const) {
      const message = error.fieldError(key);
      if (message) {
        next[key] = message;
      }
    }
    setErrors(next);
    if (Object.keys(next).length === 0) {
      setGeneralError(error.message);
    }
    return true;
  }

  async function onTest() {
    const next = validate();
    setErrors(next);
    setGeneralError(null);
    if (Object.keys(next).length > 0) {
      return;
    }
    setStale(false);
    try {
      const result = await test.mutateAsync({ input: toInput() });
      setLast({
        result: result.result,
        testedAt: result.testedAt,
        message: result.message,
        retryAfterAt: result.retryAfterAt,
      });
    } catch (error) {
      if (!applyApiFieldErrors(error)) {
        setGeneralError("测试连接失败，请检查参数后重试。");
      }
    }
  }

  async function onSave() {
    const next = validate();
    setErrors(next);
    setGeneralError(null);
    if (Object.keys(next).length > 0) {
      return;
    }
    try {
      const binding = await create.mutateAsync(toInput());
      onSaved(binding);
      onClose();
    } catch (error) {
      if (!applyApiFieldErrors(error)) {
        setGeneralError("保存失败，请重试。");
      }
    }
  }

  const github = draft.provider === "github";
  return (
    <div className={styles.formCard} data-testid="binding-form">
      <div className={styles.sectionHead}>
        <div>
          <h3 className={styles.formTitle}>添加仓库绑定</h3>
          <p className={styles.muted}>先测试再保存；保存前测试不落库。</p>
        </div>
        <Button type="button" variant="ghost" onClick={onClose}>
          关闭
        </Button>
      </div>

      <FormField label="提供商" required error={errors.provider}>
        <ProviderSegmented
          value={draft.provider}
          onChange={changeProvider}
          disabled={create.isPending}
        />
      </FormField>

      <FormField
        label="仓库标识"
        required
        error={errors.repoIdentifier}
        hint={
          github
            ? "GitHub：owner/repo"
            : "云效：组织 ID 必填；仓库标识填 group/repo 全路径或数字仓库 ID"
        }
      >
        <Input
          value={draft.repoIdentifier}
          onChange={(event) => patch("repoIdentifier", event.target.value)}
          placeholder={github ? "如 owner/repo" : "如 pay-group/pay-api"}
        />
      </FormField>

      {github ? null : (
        <FormField label="组织 ID" required error={errors.orgId}>
          <Input
            value={draft.orgId}
            onChange={(event) => patch("orgId", event.target.value)}
          />
        </FormField>
      )}

      <FormField
        label="API 域名"
        error={errors.apiBaseUrl}
        hint={
          github
            ? "GitHub 固定 https://api.github.com（只读）"
            : "云效默认 https://openapi-rdc.aliyuncs.com，可填地域域名；必须是 https://"
        }
      >
        <Input
          value={draft.apiBaseUrl}
          onChange={(event) => patch("apiBaseUrl", event.target.value)}
          readOnly={github}
          disabled={github}
        />
      </FormField>

      <TokenField
        value={draft.token}
        onChange={(value) => patch("token", value)}
        mode="create"
        error={errors.token}
      />

      <RepoPermissionHint />

      <TestResultStrip
        testing={test.isPending}
        last={last}
        stale={stale}
        onTest={() => void onTest()}
        disabled={create.isPending}
      />

      {generalError ? (
        <p className={styles.bannerError} role="alert">
          {generalError}
        </p>
      ) : null}

      <div className={styles.formFoot}>
        <span className={styles.muted}>
          {PROVIDER_LABELS[draft.provider]} · 保存后令牌只显示掩码
        </span>
        <div className={styles.actionsInline}>
          <Button type="button" variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button
            type="button"
            onClick={() => void onSave()}
            loading={create.isPending}
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}
