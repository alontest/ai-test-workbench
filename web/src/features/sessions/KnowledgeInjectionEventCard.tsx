interface KnowledgeInjectionItemPayload {
  kbId: number;
  kbName: string;
  kbVersion: number;
  entryCodes: string[];
  injectedChars: number;
  kbDeleted?: boolean;
}

export interface KnowledgeInjectionPayload {
  items: KnowledgeInjectionItemPayload[];
  promptChars: number;
  injectedChars: number;
  totalChars: number;
  excludedCodes?: string[];
}

export interface KnowledgeInjectionEventCardProps {
  payload: KnowledgeInjectionPayload;
}

export function KnowledgeInjectionEventCard({
  payload,
}: KnowledgeInjectionEventCardProps) {
  if (!payload.items?.length) {
    return null;
  }
  const excluded = payload.excludedCodes ?? [];
  return (
    <div style={{ display: "grid", gap: "var(--spacing-2)" }}>
      <strong>知识库注入</strong>
      <span
        style={{
          color: "var(--color-muted-foreground)",
          fontSize: "var(--font-size-sm)",
        }}
      >
        提示 {payload.promptChars.toLocaleString("zh-CN")} · 注入{" "}
        {payload.injectedChars.toLocaleString("zh-CN")} · 合计{" "}
        {payload.totalChars.toLocaleString("zh-CN")}
      </span>
      <ul style={{ margin: 0, paddingLeft: "var(--spacing-5)" }}>
        {payload.items.map((item) => (
          <li key={item.kbId}>
            {item.kbName} v{item.kbVersion}
            {item.entryCodes.length > 0 ? ` · ${item.entryCodes.join("、")}` : ""}
            {` · ${item.injectedChars.toLocaleString("zh-CN")} 字`}
            {item.kbDeleted ? " 知识库已删除" : ""}
          </li>
        ))}
      </ul>
      {excluded.length > 0 ? (
        <span
          style={{
            color: "var(--color-muted-foreground)",
            fontSize: "var(--font-size-sm)",
          }}
        >
          排除 {excluded.join("、")}
        </span>
      ) : null}
    </div>
  );
}
