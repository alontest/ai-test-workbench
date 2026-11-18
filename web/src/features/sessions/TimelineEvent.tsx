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
