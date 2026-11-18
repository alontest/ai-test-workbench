import { useInfiniteQuery } from "@tanstack/react-query";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState } from "../../components/ui/Feedback";
import { Skeleton } from "../../components/ui/Loading";
import { apiFetch, queryString } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { TimelineEvent } from "./TimelineEvent";
import type { SessionEvent } from "./types";

export interface SessionTimelineProps {
  sessionId: number;
  readOnly?: boolean;
}

interface EventsPage {
  items: SessionEvent[];
  nextCursor: string | null;
}

export function useSessionEvents(sessionId: number) {
  return useInfiniteQuery({
    queryKey: queryKeys.sessionEvents(sessionId),
    queryFn: ({ pageParam }) =>
      apiFetch<EventsPage>(
        `/sessions/${sessionId}/events${queryString({
          limit: 50,
          cursor: pageParam,
        })}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: sessionId > 0,
  });
}

export function SessionTimeline({ sessionId }: SessionTimelineProps) {
  const query = useSessionEvents(sessionId);
  const events = query.data?.pages.flatMap((page) => page.items) ?? [];

  if (query.isPending) {
    return <Skeleton rows={4} />;
  }
  if (query.isError) {
    return (
      <ErrorState
        message="无法加载时间线"
        onRetry={() => void query.refetch()}
      />
    );
  }
  if (events.length === 0) {
    return <EmptyState title="会话还没有内容" />;
  }

  return (
    <div style={{ display: "grid", gap: "var(--spacing-3)" }}>
      {events.map((event) => (
        <TimelineEvent key={event.eventId} event={event} />
      ))}
      {query.hasNextPage ? (
        <Button
          type="button"
          variant="secondary"
          loading={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          加载更多
        </Button>
      ) : null}
    </div>
  );
}
