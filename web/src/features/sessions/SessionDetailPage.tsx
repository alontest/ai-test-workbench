import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Tabs } from "radix-ui";
import { useParams } from "react-router";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { CallPanel } from "../calls/CallPanel";
import { FileUploader } from "../composer/FileUploader";
import { TextComposer } from "../composer/TextComposer";
import { SessionHeader } from "./SessionHeader";
import { SessionTimeline, useSessionEvents } from "./SessionTimeline";
import type { ArtifactEventPayload, SessionSummary } from "./types";
import styles from "./SessionDetailPage.module.css";

const BACK_LINK = { to: "/sessions", label: "返回会话列表" } as const;

export function SessionDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const validId = Number.isInteger(sessionId) && sessionId > 0;
  const [tab, setTab] = useState("text");
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
    return (
      <PageContainer tier="xl" className={styles.page}>
        <PageHeader
          backLink={BACK_LINK}
          title="会话详情"
          description="会话编号无效。"
        />
        <ErrorState message="会话不存在" retryable={false} />
      </PageContainer>
    );
  }
  if (sessionQuery.isPending) {
    return (
      <PageContainer tier="xl" className={styles.page}>
        <PageHeader
          backLink={BACK_LINK}
          title="会话详情"
          description="正在加载会话上下文…"
        />
        <Spinner label="加载会话" />
      </PageContainer>
    );
  }
  if (sessionQuery.isError || !session) {
    return (
      <PageContainer tier="xl" className={styles.page}>
        <PageHeader
          backLink={BACK_LINK}
          title="会话详情"
          description="会话上下文暂时无法读取。"
        />
        <ErrorState
          message="无法加载会话"
          onRetry={() => void sessionQuery.refetch()}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer tier="xl" className={styles.page}>
      <SessionHeader session={session} />
      {readOnly ? (
        <p className={styles.banner} role="status">
          会话已结束，不再接受新输入
        </p>
      ) : null}
      <div className={styles.layout}>
        <SessionTimeline sessionId={sessionId} readOnly={readOnly} />
        <aside className={styles.panel} aria-label="操控台">
          <Tabs.Root value={tab} onValueChange={setTab}>
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
            {/* forceMount + hidden={false}：三个表单始终挂载，切换 Tab 只改视觉，
                已输入的草稿不会随卸载丢失。隐藏交给 [data-state="inactive"] 规则。 */}
            <Tabs.Content
              value="text"
              forceMount
              hidden={false}
              className={styles.tabContent}
            >
              <TextComposer sessionId={sessionId} readOnly={readOnly} />
            </Tabs.Content>
            <Tabs.Content
              value="upload"
              forceMount
              hidden={false}
              className={styles.tabContent}
            >
              <FileUploader
                sessionId={sessionId}
                existingFileNames={existingFileNames}
                readOnly={readOnly}
              />
            </Tabs.Content>
            <Tabs.Content
              value="call"
              forceMount
              hidden={false}
              className={styles.tabContent}
            >
              <CallPanel session={session} readOnly={readOnly} />
            </Tabs.Content>
          </Tabs.Root>
        </aside>
      </div>
    </PageContainer>
  );
}
