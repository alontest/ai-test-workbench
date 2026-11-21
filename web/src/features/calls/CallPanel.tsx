import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Mascot, type MascotState } from "../../components/mascot/Mascot";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { Textarea } from "../../components/ui/Input";
import { apiFetch } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { queryKeys } from "../../lib/api/keys";
import { CALL_TIMEOUT_MS, countChars, PROMPT_MAX_CHARS } from "../../lib/limits";
import {
  invalidItemsOf,
  sameRef,
  toKnowledgeRefs,
} from "../knowledge/api/client";
import type { InvalidItem, KbEntryRef } from "../knowledge/api/types";
import { KbCharBudget } from "../knowledge/components/KbCharBudget";
import { KbInjectPicker } from "../knowledge/components/KbInjectPicker";
import { KbInvalidEntryDialog } from "../knowledge/components/KbInvalidEntryDialog";
import { useInjectionPreview } from "../knowledge/hooks/useInjectionPreview";
import {
  CharacterCounter,
  counterState,
} from "../composer/CharacterCounter";
import type { SessionSummary } from "../sessions/types";
import { AdvancedParams, type AdvancedParamsValue } from "./AdvancedParams";
import styles from "./CallPanel.module.css";

export interface CallPanelProps {
  session: SessionSummary;
  readOnly?: boolean;
  maxChars?: number;
}

const EMPTY_PARAMS: AdvancedParamsValue = { temperature: "", maxTokens: "" };

function parseOptionalNumber(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : undefined;
}

function mergeUnavailable(
  current: KbEntryRef[],
  incoming: InvalidItem[],
): KbEntryRef[] {
  const merged = [...current];
  for (const item of incoming) {
    const ref = { kbId: item.kbId, code: item.code };
    if (!merged.some((existing) => sameRef(existing, ref))) {
      merged.push(ref);
    }
  }
  return merged;
}

export function CallPanel({
  session,
  readOnly = false,
  maxChars = PROMPT_MAX_CHARS,
}: CallPanelProps) {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [params, setParams] = useState<AdvancedParamsValue>(EMPTY_PARAMS);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [selection, setSelection] = useState<KbEntryRef[]>([]);
  const [unavailable, setUnavailable] = useState<KbEntryRef[]>([]);
  const [invalidItems, setInvalidItems] = useState<InvalidItem[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [retryBody, setRetryBody] = useState<Record<string, unknown> | null>(
    null,
  );
  const chars = countChars(prompt);
  const state = counterState(chars, maxChars);
  const exceeded = state === "exceeded";
  const preview = useInjectionPreview(session.sessionId, {
    refs: selection,
    userPrompt: prompt,
  });
  const overLimit = preview.data?.overLimit ?? false;
  const mutation = useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), CALL_TIMEOUT_MS);
      try {
        return await apiFetch(`/sessions/${session.sessionId}/ai/complete`, {
          method: "POST",
          body: JSON.stringify(body),
          signal: controller.signal,
        });
      } finally {
        window.clearTimeout(timer);
      }
    },
    onSuccess: async () => {
      setSubmitError(null);
      setRetryBody(null);
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.calls });
    },
    onError: (error, variables) => {
      if (!isApiError(error)) {
        setSubmitError("ai_timeout");
        return;
      }
      if (error.code === "knowledge_invalid_entries") {
        const items = invalidItemsOf(error);
        if (items.length > 0) {
          setInvalidItems(items);
          setUnavailable((current) => mergeUnavailable(current, items));
          setSelection((current) =>
            current.filter(
              (ref) =>
                !items.some(
                  (item) =>
                    item.kbId === ref.kbId && item.code === ref.code,
                ),
            ),
          );
          setRetryBody(variables);
          setConfirmOpen(true);
          setSubmitError(null);
          return;
        }
      }
      setSubmitError(error.code);
    },
  });

  const disabled =
    readOnly ||
    exceeded ||
    overLimit ||
    mutation.isPending ||
    !prompt.trim();

  // 鸮鸮随调用面板的真实状态换姿态，不用额外的假状态字段。
  const mascotState: MascotState = mutation.isPending
    ? "analyzing"
    : exceeded || overLimit || submitError
      ? "warning"
      : prompt.trim()
        ? "watching"
        : "idle";
  const assistantHint = mutation.isPending
    ? "正在扫描模型返回，请稍候…"
    : exceeded || overLimit
      ? "字符预算已超限，先删减再发起。"
      : submitError
        ? "调用失败，核对错误码后重试。"
        : prompt.trim()
          ? "提示词已就位，随时可以发起调用。"
          : "等待提示词，输入后即可发起调用。";

  function baseBody(): Record<string, unknown> {
    const body: Record<string, unknown> = { prompt };
    if (advancedOpen) {
      const temperature = parseOptionalNumber(params.temperature);
      const maxTokens = parseOptionalNumber(params.maxTokens);
      if (temperature !== undefined) {
        body.temperature = temperature;
      }
      if (maxTokens !== undefined) {
        body.maxTokens = maxTokens;
      }
    }
    if (selection.length > 0) {
      body.knowledgeRefs = toKnowledgeRefs(selection);
    }
    return body;
  }

  function onSubmit() {
    if (disabled) {
      return;
    }
    setRetryBody(null);
    mutation.mutate(baseBody());
  }

  function onConfirmInvalid() {
    setConfirmOpen(false);
    if (!retryBody) {
      return;
    }
    mutation.mutate({
      ...retryBody,
      confirmInvalidCodes: invalidItems.map(({ kbId, code }) => ({ kbId, code })),
    });
  }

  return (
    <form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className={styles.assistant}>
        <Mascot size={40} state={mascotState} label="鸮鸮" />
        <div className={styles.assistantText}>
          <strong className={styles.assistantTitle}>调用操控台</strong>
          <span className={styles.assistantHint}>{assistantHint}</span>
        </div>
      </div>
      <FormField
        label="提示"
        required
        error={
          exceeded
            ? `已超出上限：当前 ${chars.toLocaleString("zh-CN")} 字符，上限 ${maxChars.toLocaleString("zh-CN")} 字符，请删减后再发起`
            : submitError
              ? submitError
              : undefined
        }
      >
        <Textarea
          value={prompt}
          disabled={readOnly || mutation.isPending}
          rows={8}
          onChange={(event) => {
            setPrompt(event.target.value);
            if (submitError) {
              setSubmitError(null);
            }
          }}
        />
      </FormField>
      <CharacterCounter value={chars} max={maxChars} />
      <KbInjectPicker
        sessionId={session.sessionId}
        selection={selection}
        onChange={setSelection}
        disabled={readOnly || mutation.isPending}
        unavailable={unavailable}
      />
      <KbCharBudget
        itemCount={selection.length}
        promptChars={preview.data?.promptChars ?? chars}
        injectedChars={preview.data?.injectedChars ?? 0}
        limit={preview.data?.limit ?? maxChars}
        pending={preview.isFetching}
      />
      <Button
        type="button"
        variant="ghost"
        disabled={readOnly || mutation.isPending}
        aria-expanded={advancedOpen}
        onClick={() => {
          setAdvancedOpen((open) => {
            if (open) {
              setParams(EMPTY_PARAMS);
            }
            return !open;
          });
        }}
      >
        高级参数
      </Button>
      {advancedOpen ? (
        <AdvancedParams
          value={params}
          onChange={setParams}
          disabled={readOnly || mutation.isPending}
        />
      ) : null}
      <Button
        type="submit"
        disabled={disabled}
        loading={mutation.isPending}
      >
        {mutation.isPending ? "调用中…" : "发起调用"}
      </Button>
      <KbInvalidEntryDialog
        open={confirmOpen}
        invalidItems={invalidItems}
        validCount={selection.length}
        loading={mutation.isPending}
        onConfirm={onConfirmInvalid}
        onCancel={() => {
          setConfirmOpen(false);
          setRetryBody(null);
        }}
      />
    </form>
  );
}
