import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { previewInjection, refsKey } from "../api/client";
import { kbKeys } from "../api/keys";
import type { KbEntryRef } from "../api/types";

const PREVIEW_DEBOUNCE_MS = 250;

export interface InjectionPreviewInput {
  refs: KbEntryRef[];
  userPrompt: string;
}

interface DebouncedInput {
  refs: KbEntryRef[];
  prompt: string;
}

/**
 * 预览按 250ms 防抖；勾选变化不重取候选，只触发本次预览。
 * 请求体里的 `userPrompt` 由服务端计字，前端只作即时提示。
 */
export function useInjectionPreview(
  sessionId: number,
  input: InjectionPreviewInput,
) {
  const key = refsKey(input.refs);
  const prompt = input.userPrompt;
  const refsRef = useRef(input.refs);
  refsRef.current = input.refs;
  const [debounced, setDebounced] = useState<DebouncedInput>({
    refs: input.refs,
    prompt: input.userPrompt,
  });

  const active =
    sessionId > 0 && input.refs.length > 0 && prompt.trim().length > 0;
  useEffect(() => {
    if (!active) {
      return;
    }
    const timer = window.setTimeout(() => {
      setDebounced({ refs: refsRef.current, prompt });
    }, PREVIEW_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [active, key, prompt]);

  const settled =
    debounced.prompt === prompt && refsKey(debounced.refs) === key;
  const query = useQuery({
    queryKey: kbKeys.preview(
      sessionId,
      refsKey(debounced.refs),
      debounced.prompt,
    ),
    queryFn: () =>
      previewInjection(sessionId, {
        refs: debounced.refs,
        userPrompt: debounced.prompt,
      }),
    enabled: active && settled,
    placeholderData: keepPreviousData,
  });

  return {
    ...query,
    data: active && settled ? query.data : undefined,
  };
}
