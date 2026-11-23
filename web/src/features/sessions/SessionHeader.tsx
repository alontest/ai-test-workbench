import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { PageHeader } from "../../components/ui/PageHeader";
import { apiFetch } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { queryKeys } from "../../lib/api/keys";
import { StatusPill } from "./StatusPill";
import type { SessionSummary } from "./types";
import styles from "./SessionDetailPage.module.css";

export interface SessionHeaderProps {
  session: SessionSummary;
}

interface SessionCompleteButtonProps {
  session: SessionSummary;
}

function SessionCompleteButton({ session }: SessionCompleteButtonProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<SessionSummary>(`/sessions/${session.sessionId}/complete`, {
        method: "POST",
      }),
    onSuccess: async (updated) => {
      setOpen(false);
      queryClient.setQueryData(
        queryKeys.sessionDetail(session.sessionId),
        updated,
      );
      await queryClient.invalidateQueries({
        queryKey: queryKeys.sessionEvents(session.sessionId),
      });
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  if (session.status !== "in_progress") {
    return null;
  }

  const errorMessage = mutation.isError
    ? isApiError(mutation.error)
      ? `${mutation.error.code} ${mutation.error.message}`
      : "session_complete_failed 标记完成失败。"
    : null;

  return (
    <>
      <Button type="button" variant="secondary" onClick={() => setOpen(true)}>
        标记完成
      </Button>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <ConfirmDialog
        open={open}
        title="标记完成"
        confirmLabel="确认完成"
        loading={mutation.isPending}
        onCancel={() => {
          if (!mutation.isPending) {
            setOpen(false);
          }
        }}
        onConfirm={() => mutation.mutate()}
        description={
          <>
            <p>标记完成后会话将转为只读，不再接受新的输入与调用。</p>
            {errorMessage ? <p role="alert">{errorMessage}</p> : null}
          </>
        }
      />
    </>
  );
}

export interface SessionDeleteButtonProps {
  session: SessionSummary;
  redirectToList?: boolean;
}

export function SessionDeleteButton({
  session,
  redirectToList = false,
}: SessionDeleteButtonProps) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      apiFetch(`/sessions/${session.sessionId}`, { method: "DELETE" }),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.calls });
      if (redirectToList) {
        navigate("/sessions");
      }
    },
  });

  const errorMessage = mutation.isError
    ? isApiError(mutation.error)
      ? `${mutation.error.code} ${mutation.error.message}`
      : "session_delete_failed 会话删除失败。"
    : null;

  return (
    <>
      <Button type="button" variant="danger" onClick={() => setOpen(true)}>
        删除会话
      </Button>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <ConfirmDialog
        open={open}
        title="删除会话"
        danger
        loading={mutation.isPending}
        confirmLabel="删除"
        onCancel={() => {
          if (!mutation.isPending) {
            setOpen(false);
          }
        }}
        onConfirm={() => mutation.mutate()}
        description={
          <>
            <p>将删除以下内容，此操作不可恢复：</p>
            <ul>
              <li>会话及其事件</li>
              <li>制品文件（sessions/{session.sessionId}/）</li>
              <li>全部调用记录</li>
            </ul>
            {errorMessage ? <p role="alert">{errorMessage}</p> : null}
          </>
        }
      />
    </>
  );
}

export function SessionHeader({ session }: SessionHeaderProps) {
  return (
    <PageHeader
      backLink={{ to: "/sessions", label: "返回会话列表" }}
      title={session.title}
      badge={<StatusPill status={session.status} />}
      description={
        <span className={styles.sessionMeta}>
          <span className={styles.sessionMetaItem}>#{session.sessionId}</span>
          <span className={styles.sessionMetaItem}>
            {session.project.name}
          </span>
          <span className={styles.sessionMetaItem}>
            {session.model.displayName} · {session.model.providerName}
          </span>
        </span>
      }
      actions={
        <>
          <SessionCompleteButton session={session} />
          <SessionDeleteButton session={session} redirectToList />
        </>
      }
    />
  );
}
