import { useState } from "react";
import { Button } from "../../components/ui/Button";
import type { InputTextPayload } from "./types";

export interface InputEventCardProps {
  payload: InputTextPayload;
}

const PREVIEW_LINES = 3;

export function InputEventCard({ payload }: InputEventCardProps) {
  const [expanded, setExpanded] = useState(false);
  const lines = payload.text.split("\n");
  const collapsible = lines.length > PREVIEW_LINES;
  const shown =
    expanded || !collapsible
      ? payload.text
      : lines.slice(0, PREVIEW_LINES).join("\n");
  return (
    <div style={{ display: "grid", gap: "var(--spacing-2)" }}>
      <strong>{payload.title}</strong>
      <span style={{ color: "var(--color-muted-foreground)", fontSize: "var(--font-size-sm)" }}>
        {payload.charCount.toLocaleString("zh-CN")} 字符
      </span>
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          fontFamily: "var(--font-family-mono)",
          fontSize: "var(--font-size-sm)",
        }}
      >
        {shown.split("\n").map((line, index) => (
          <span key={index} style={{ display: "block" }}>
            {line}
          </span>
        ))}
      </pre>
      {collapsible ? (
        <Button
          type="button"
          variant="ghost"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "收起" : "展开全文"}
        </Button>
      ) : null}
    </div>
  );
}
