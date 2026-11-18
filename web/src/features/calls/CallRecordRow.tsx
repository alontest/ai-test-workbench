import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch } from "../../lib/api/client";
import { formatLatency } from "../../lib/limits";
import styles from "./calls.module.css";
import type { CallDetail, CallRecord, CallStatus } from "./types";

const STATUS_LABEL: Record<CallStatus, string> = {
  success: "成功",
  failed: "失败",
  timeout: "超时",
  running: "进行中",
};

const STATUS_TONE: Record<CallStatus, "success" | "danger" | "warning" | "info"> =
  {
    success: "success",
    failed: "danger",
    timeout: "warning",
    running: "info",
  };

export interface CallRecordRowProps {
  call: CallRecord;
}

export function CallRecordRow({ call }: CallRecordRowProps) {
  const [expanded, setExpanded] = useState(false);
  const detailQuery = useQuery({
    queryKey: ["calls", call.callId],
    queryFn: () => apiFetch<CallDetail>(`/calls/${call.callId}`),
    enabled: expanded,
  });
  const detail = detailQuery.data;
  const injection = detail?.knowledgeInjection ?? call.knowledgeInjection;

  return (
    <>
      <tr>
        <td>{call.model.displayName}</td>
        <td>
          <Badge
            label={STATUS_LABEL[call.status]}
            tone={STATUS_TONE[call.status]}
          />
        </td>
        <td>{call.latencyMs == null ? "—" : formatLatency(call.latencyMs)}</td>
        <td>{call.retryCount}</td>
        <td>{call.createdAt}</td>
        <td>
          <Button
            type="button"
            variant="ghost"
            onClick={() => setExpanded((open) => !open)}
          >
            {expanded ? "收起" : "展开核对"}
          </Button>
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={6}>
            {detailQuery.isPending ? (
              <Spinner label="加载调用详情" />
            ) : detailQuery.isError ? (
              <ErrorState
                message="无法加载调用详情"
                onRetry={() => void detailQuery.refetch()}
              />
            ) : (
              <div className={styles.detail}>
                <p>提示摘要（{call.promptCharCount} 字）</p>
                <pre className={styles.preview}>{call.promptPreview}</pre>
                {detail?.errorCode || call.errorCode ? (
                  <p>{detail?.errorCode ?? call.errorCode}</p>
                ) : null}
                <p>重试 {detail?.retryCount ?? call.retryCount}</p>
                {detail?.errorMessage || call.errorMessage ? (
                  <p>{detail?.errorMessage ?? call.errorMessage}</p>
                ) : null}
                {detail?.resultText ? (
                  <pre className={styles.preview}>{detail.resultText}</pre>
                ) : null}
                {injection && injection.length > 0 ? (
                  <ul>
                    {injection.map((item) => (
                      <li key={item.kbId}>
                        {item.kbName} v{item.kbVersion}
                        {item.kbDeleted ? " 知识库已删除" : ""}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            )}
          </td>
        </tr>
      ) : null}
    </>
  );
}
