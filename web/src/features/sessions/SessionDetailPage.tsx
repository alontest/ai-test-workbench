import { useQuery } from "@tanstack/react-query";
import { Tabs } from "radix-ui";
import { useParams } from "react-router";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { CallPanel } from "../calls/CallPanel";
import { FileUploader } from "../composer/FileUploader";
import { TextComposer } from "../composer/TextComposer";
import { SessionHeader } from "./SessionHeader";
import { SessionTimeline, useSessionEvents } from "./SessionTimeline";
import type { ArtifactEventPayload, SessionSummary } from "./types";
import styles from "./SessionDetailPage.module.css";

export function SessionDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const validId = Number.isInteger(sessionId) && sessionId > 0;
  const sessionQuery = useQuery({
    queryKey: queryKeys.sessionDetail(sessionId),
    queryFn: () => apiFetch<SessionSummary>(`/sessions/${sessionId}`),
    enabled: validId,
  });
  const eventsQuery = useSessionEvents(validId ? sessionId : 0);
  const session = sessionQuery.data;
  const readOnly = session ? session.status !== "in_progress" : false;
  const existingFileNames =
    eventsQuery.data?.pages.flatMap((page) =>
      page.items.flatMap((event) => {
        if (event.type !== "artifact") {
          return [];
        }
        const fileName = (event.payload as Partial<ArtifactEventPayload>).fileName;
        return fileName ? [fileName] : [];
      }),
    ) ?? [];

  if (!validId) {
    return <ErrorState message="会话不存在" retryable={false} />;
  }
  if (sessionQuery.isPending) {
    return <Spinner label="加载会话" />;
  }
  if (sessionQuery.isError || !session) {
    return (
      <ErrorState
        message="无法加载会话"
        onRetry={() => void sessionQuery.refetch()}
      />
    );
  }

  return (
    <section className={styles.page}>
      <SessionHeader session={session} />
      {readOnly ? (
        <p className={styles.banner} role="status">
          会话已结束，不再接受新输入
        </p>
      ) : null}
      <div className={styles.layout}>
        <SessionTimeline sessionId={sessionId} readOnly={readOnly} />
        <aside className={styles.panel}>
          <Tabs.Root defaultValue="text">
            <Tabs.List className={styles.tabList} aria-label="输入方式">
              <Tabs.Trigger className={styles.tab} value="text">
                文本粘贴
              </Tabs.Trigger>
              <Tabs.Trigger className={styles.tab} value="upload">
                文件上传
              </Tabs.Trigger>
              <Tabs.Trigger className={styles.tab} value="call">
                调用
              </Tabs.Trigger>
            </Tabs.List>
            <div className={styles.tabPanel}>
              <TextComposer sessionId={sessionId} readOnly={readOnly} />
              <FileUploader
                sessionId={sessionId}
                existingFileNames={existingFileNames}
                readOnly={readOnly}
              />
              <CallPanel session={session} readOnly={readOnly} />
            </div>
          </Tabs.Root>
        </aside>
      </div>
    </section>
  );
}
