import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { FormField } from "../../components/ui/FormField";
import { Textarea } from "../../components/ui/Input";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { Select } from "../../components/ui/Select";
import { apiFetch, queryString } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { queryKeys } from "../../lib/api/keys";
import styles from "./extensions.module.css";

interface Page<T> {
  items: T[];
}

interface Approval {
  approvalId: string;
  projectId: number | null;
  sessionId: number | null;
  callId: number | null;
  targetTitle: string;
  targetType: string;
  actionType: string;
  baseVersion: number;
  unifiedDiff: string;
  rationale: string;
  status: "pending" | "approved" | "rejected";
  decisionNote: string | null;
  appliedVersion: number | null;
  createdAt: string;
  decidedAt: string | null;
}

const STATUS_OPTIONS = [
  { value: "", label: "全部" },
  { value: "pending", label: "待审批" },
  { value: "approved", label: "已批准" },
  { value: "rejected", label: "已驳回" },
];

const STATUS_LABEL: Record<string, string> = {
  pending: "待审批",
  approved: "已批准",
  rejected: "已驳回",
};

const STATUS_TONE: Record<string, "info" | "success" | "danger"> = {
  pending: "info",
  approved: "success",
  rejected: "danger",
};

function errorMessage(error: unknown, fallback: string): string {
  return isApiError(error) ? error.message : fallback;
}

function DiffView({ diff }: { diff: string }) {
  return (
    <pre className={styles.diff} aria-label="Unified Diff">
      {diff.split("\n").map((line, index) => {
        const tone = line.startsWith("+")
          ? styles.diffAdd
          : line.startsWith("-")
            ? styles.diffRemove
            : line.startsWith("@@")
              ? styles.diffHunk
              : undefined;
        return (
          <span key={`${index}-${line}`} className={tone}>
            {line || " "}
            {"\n"}
          </span>
        );
      })}
    </pre>
  );
}

export function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [decision, setDecision] = useState<{ tone: "success" | "danger"; text: string } | null>(
    null,
  );

  const approvalsQuery = useQuery({
    queryKey: queryKeys.approvals(status),
    queryFn: () =>
      apiFetch<Page<Approval>>(`/approvals${queryString({ status: status || undefined })}`),
  });

  const items = approvalsQuery.data?.items ?? [];
  const active = items.find((item) => item.approvalId === selectedId) ?? items[0];

  const decide = useMutation({
    mutationFn: (kind: "approve" | "reject") => {
      if (!active) {
        throw new Error("no approval selected");
      }
      return apiFetch<Approval>(`/approvals/${active.approvalId}/${kind}`, {
        method: "POST",
        body: JSON.stringify({ decisionNote: note.trim() || null }),
      });
    },
    onSuccess: (result, kind) => {
      setNote("");
      setDecision({
        tone: kind === "approve" ? "success" : "danger",
        text:
          kind === "approve"
            ? `已批准并落盘，技能当前版本 v${result.appliedVersion ?? "?"}。`
            : "已驳回，技能正文保持不变。",
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.approvals() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.skills() });
    },
  });

  return (
    <PageContainer tier="lg" className={styles.section}>
      <PageHeader
        title="审批中心"
        description="AI 提交的资产变更先进入审批池，核对完整 Diff 后由人批准落盘或驳回保留。"
      />

      <section className={styles.toolbar} aria-label="审批筛选">
        <FormField label="状态筛选">
          <Select
            aria-label="状态筛选"
            value={status}
            options={STATUS_OPTIONS}
            onChange={(value) => {
              setStatus(value);
              setSelectedId(null);
              setDecision(null);
            }}
          />
        </FormField>
      </section>

      {approvalsQuery.isPending ? (
        <Spinner label="加载审批单" />
      ) : approvalsQuery.isError ? (
        <ErrorState
          message="无法加载审批单"
          onRetry={() => void approvalsQuery.refetch()}
        />
      ) : items.length === 0 ? (
        <p className={styles.meta}>当前筛选下没有审批单。</p>
      ) : (
        <div className={styles.split}>
          <aside className={styles.list} aria-label="审批单列表">
            {items.map((item) => (
              <button
                key={item.approvalId}
                type="button"
                className={[
                  styles.listItem,
                  item.approvalId === active?.approvalId ? styles.listItemActive : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                aria-pressed={item.approvalId === active?.approvalId}
                onClick={() => {
                  setSelectedId(item.approvalId);
                  setDecision(null);
                }}
              >
                <span className={styles.listTitle}>{item.targetTitle}</span>
                <span className={styles.listMeta}>
                  <Badge
                    label={STATUS_LABEL[item.status] ?? item.status}
                    tone={STATUS_TONE[item.status] ?? "neutral"}
                  />
                  <code>{item.actionType}</code>
                </span>
              </button>
            ))}
          </aside>

          {active ? (
            <section className={styles.detail} aria-label="审批详情">
              <header className={styles.detailHead}>
                <h2>{active.targetTitle}</h2>
                <p className={styles.meta}>
                  动作 {active.actionType} · 基线 v{active.baseVersion} · 会话{" "}
                  {active.sessionId ?? "—"} · 调用 {active.callId ?? "—"}
                </p>
              </header>

              <section className={styles.subsection} aria-label="修改理由">
                <h3>修改理由</h3>
                <p className={styles.callout}>{active.rationale}</p>
              </section>

              <section className={styles.subsection} aria-label="变更 Diff">
                <h3>Unified Diff</h3>
                <DiffView diff={active.unifiedDiff} />
              </section>

              {active.status === "pending" ? (
                <section className={styles.subsection} aria-label="裁决">
                  <FormField label="审批备注">
                    <Textarea
                      aria-label="审批备注"
                      rows={2}
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                    />
                  </FormField>
                  {decide.isError ? (
                    <ErrorState
                      message={errorMessage(decide.error, "审批失败")}
                      retryable={false}
                    />
                  ) : null}
                  <div className={styles.actions}>
                    <Button
                      type="button"
                      loading={decide.isPending}
                      onClick={() => decide.mutate("approve")}
                    >
                      批准并落盘
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      loading={decide.isPending}
                      onClick={() => decide.mutate("reject")}
                    >
                      驳回
                    </Button>
                  </div>
                </section>
              ) : (
                <section className={styles.subsection} aria-label="裁决结果">
                  <p className={styles.meta}>
                    裁决：{STATUS_LABEL[active.status] ?? active.status}
                    {active.decisionNote ? ` · ${active.decisionNote}` : ""}
                  </p>
                </section>
              )}

              {decision ? (
                <p role="status" className={styles.callout}>
                  {decision.text}
                </p>
              ) : null}
            </section>
          ) : null}
        </div>
      )}
    </PageContainer>
  );
}
