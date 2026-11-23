import { PROMPT_MAX_CHARS } from "../../lib/limits";

export { PROMPT_MAX_CHARS };

export interface CharacterCounterProps {
  value: number;
  max?: number;
}

export function counterState(
  value: number,
  max: number,
): "normal" | "warning" | "exceeded" {
  if (value > max) {
    return "exceeded";
  }
  if (value > max * 0.9) {
    return "warning";
  }
  return "normal";
}

export function CharacterCounter({
  value,
  max = PROMPT_MAX_CHARS,
}: CharacterCounterProps) {
  const state = counterState(value, max);
  const color =
    state === "exceeded"
      ? "var(--color-destructive)"
      : state === "warning"
        ? "var(--color-warning)"
        : "var(--color-muted-foreground)";
  return (
    <p
      role="status"
      aria-label="字数"
      data-state={state}
      style={{
        margin: 0,
        color,
        fontSize: "var(--font-size-sm)",
      }}
    >
      已输入 {value.toLocaleString("zh-CN")} / {max.toLocaleString("zh-CN")}
    </p>
  );
}
