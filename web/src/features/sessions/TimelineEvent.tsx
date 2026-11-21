import type { ReactNode } from "react";
import { ArtifactEventCard } from "./ArtifactEventCard";
import { CallEventCard } from "./CallEventCard";
import { InputEventCard } from "./InputEventCard";
import {
  KnowledgeInjectionEventCard,
  type KnowledgeInjectionPayload,
} from "./KnowledgeInjectionEventCard";
import { StatusChangeEvent } from "./StatusChangeEvent";
import type {
  ArtifactEventPayload,
  CallEventPayload,
  InputTextPayload,
  SessionEvent,
  StatusChangePayload,
} from "./types";

export interface TimelineEventProps {
  event: SessionEvent;
}

function asRecord(payload: Record<string, unknown>): Record<string, unknown> {
  return payload;
}

/** 事件左侧 3px 语义色条：成功/调用绿、失败红、知识注入信息蓝、输入/制品中性。 */
function eventTone(event: SessionEvent): string {
  switch (event.type) {
    case "call": {
      const status = event.payload.status;
      if (status === "failed") {
        return "var(--color-destructive)";
      }
      if (status === "success") {
        return "var(--color-accent)";
      }
      return "var(--color-warning)";
    }
    case "status_change": {
      const to = event.payload.to;
      if (to === "failed") {
        return "var(--color-destructive)";
      }
      if (to === "completed") {
        return "var(--color-accent)";
      }
      return "var(--color-info)";
    }
    case "knowledge_injection":
      return "var(--color-info)";
    case "input_text":
      return "color-mix(in srgb, var(--color-accent) 55%, var(--color-border))";
    default:
      return "color-mix(in srgb, var(--color-muted-foreground) 45%, var(--color-border))";
  }
}

export function TimelineEvent({ event }: TimelineEventProps) {
  const payload = asRecord(event.payload);
  let body: ReactNode;
  switch (event.type) {
    case "input_text":
      body = <InputEventCard payload={payload as unknown as InputTextPayload} />;
      break;
    case "call":
      body = <CallEventCard payload={payload as unknown as CallEventPayload} />;
      break;
    case "artifact":
      body = (
        <ArtifactEventCard payload={payload as unknown as ArtifactEventPayload} />
      );
      break;
    case "status_change":
      body = (
        <StatusChangeEvent payload={payload as unknown as StatusChangePayload} />
      );
      break;
    case "knowledge_injection":
      body = (
        <KnowledgeInjectionEventCard
          payload={payload as unknown as KnowledgeInjectionPayload}
        />
      );
      break;
    default:
      body = null;
  }
  return (
    <article
      data-event-type={event.type}
      style={{
        border: "1px solid var(--color-border)",
        borderLeft: `3px solid ${eventTone(event)}`,
        borderRadius: "var(--radius-md)",
        padding: "var(--spacing-4)",
        background: "var(--color-card)",
        display: "grid",
        gap: "var(--spacing-2)",
      }}
    >
      <time
        dateTime={event.createdAt}
        style={{ color: "var(--color-muted-foreground)", fontSize: "var(--font-size-sm)" }}
      >
        {event.createdAt}
      </time>
      {body}
    </article>
  );
}
