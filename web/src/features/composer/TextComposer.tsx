import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { Input, Textarea } from "../../components/ui/Input";
import { apiFetch } from "../../lib/api/client";
import { countChars, PROMPT_MAX_CHARS } from "../../lib/limits";
import { CharacterCounter, counterState } from "./CharacterCounter";

export interface TextComposerProps {
  sessionId: number;
  readOnly?: boolean;
  maxChars?: number;
}

export function TextComposer({
  sessionId,
  readOnly = false,
  maxChars = PROMPT_MAX_CHARS,
}: TextComposerProps) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [emptyError, setEmptyError] = useState(false);
  const chars = countChars(text);
  const state = counterState(chars, maxChars);
  const exceeded = state === "exceeded";
  const mutation = useMutation({
    mutationFn: (payload: { title: string; text: string }) =>
      apiFetch(`/sessions/${sessionId}/inputs/text`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      setTitle("");
      setText("");
      setEmptyError(false);
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  function onSubmit() {
    if (readOnly || exceeded || mutation.isPending) {
      return;
    }
    if (!text.trim()) {
      setEmptyError(true);
      return;
    }
    mutation.mutate({
      title: title.trim() || "文本",
      text,
    });
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      style={{ display: "grid", gap: "var(--spacing-3)" }}
    >
      <FormField label="标题">
        <Input
          value={title}
          maxLength={200}
          disabled={readOnly}
          onChange={(event) => setTitle(event.target.value)}
        />
      </FormField>
      <FormField
        label="正文"
        required
        error={
          emptyError
            ? "正文必填"
            : exceeded
              ? `已超出上限：当前 ${chars.toLocaleString("zh-CN")} 字符，上限 ${maxChars.toLocaleString("zh-CN")} 字符，请删减后再提交`
              : undefined
        }
      >
        <Textarea
          value={text}
          disabled={readOnly}
          rows={8}
          onChange={(event) => {
            setText(event.target.value);
            if (emptyError) {
              setEmptyError(false);
            }
          }}
        />
      </FormField>
      <CharacterCounter value={chars} max={maxChars} />
      <Button
        type="submit"
        disabled={readOnly || exceeded || mutation.isPending}
        loading={mutation.isPending}
      >
        添加到时间线
      </Button>
    </form>
  );
}
