import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { Textarea } from "../../components/ui/Input";
import { apiFetch } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { queryKeys } from "../../lib/api/keys";
import { CALL_TIMEOUT_MS, countChars, PROMPT_MAX_CHARS } from "../../lib/limits";
import {
  CharacterCounter,
  counterState,
} from "../composer/CharacterCounter";
import type { SessionSummary } from "../sessions/types";
import { AdvancedParams, type AdvancedParamsValue } from "./AdvancedParams";

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
  const chars = countChars(prompt);
  const state = counterState(chars, maxChars);
  const exceeded = state === "exceeded";
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
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.calls });
    },
    onError: (error) => {
      if (isApiError(error)) {
        setSubmitError(error.code);
        return;
      }
      setSubmitError("ai_timeout");
    },
  });

  const disabled =
    readOnly || exceeded || mutation.isPending || !prompt.trim();

  function onSubmit() {
    if (disabled) {
      return;
    }
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
    mutation.mutate(body);
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      style={{ display: "grid", gap: "var(--spacing-3)" }}
    >
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
    </form>
  );
}
