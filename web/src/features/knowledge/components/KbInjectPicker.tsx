import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import { sameRef } from "../api/client";
import type { EntryListItem, EntryType, KbEntryRef } from "../api/types";
import { useInjectionCandidates } from "../hooks/useInjectionCandidates";
import { KbEntryList } from "./KbEntryList";
import { KbSearchBox } from "./KbSearchBox";
import { KbTypeTabs } from "./KbTypeTabs";
import styles from "./knowledge.module.css";

export interface KbInjectPickerProps {
  sessionId: number;
  selection: KbEntryRef[];
  onChange: (selection: KbEntryRef[]) => void;
  disabled?: boolean;
  /** 上一次 409 判定的失效项；保留展示但不可再勾选。 */
  unavailable?: KbEntryRef[];
}

export function KbInjectPicker({
  sessionId,
  selection,
  onChange,
  disabled = false,
  unavailable = [],
}: KbInjectPickerProps) {
  const [q, setQ] = useState("");
  const [type, setType] = useState<EntryType | null>(null);
  const query = useInjectionCandidates(sessionId, {
    q: q || undefined,
    type: type ?? undefined,
    enabled: !disabled,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const counts = query.data?.pages[0]?.countsByType;

  const selectedIds = items
    .filter((item) =>
      selection.some((ref) => sameRef(ref, { kbId: item.kbId, code: item.code })),
    )
    .map((item) => item.entryId);
  const unavailableCodes = unavailable
    .filter((ref) =>
      items.some((item) => item.kbId === ref.kbId && item.code === ref.code),
    )
    .map((ref) => ref.code);

  function toggle(_entryId: string, item: EntryListItem) {
    const ref: KbEntryRef = { kbId: item.kbId, code: item.code };
    const exists = selection.some((current) => sameRef(current, ref));
    onChange(
      exists
        ? selection.filter((current) => !sameRef(current, ref))
        : [...selection, ref],
    );
  }

  return (
    <section className={styles.picker} aria-label="知识库注入选择器">
      <div className={styles.sectionHead}>
        <h3 style={{ margin: 0 }}>知识库注入（按编号勾选）</h3>
        <span className={styles.muted}>已选 {selection.length} 条</span>
      </div>
      <KbSearchBox
        value={q}
        onChange={setQ}
        label="检索可注入条目"
        placeholder="检索：ENT- / ENT-001 / 关键词"
      />
      <KbTypeTabs value={type} counts={counts} onChange={setType} />
      {query.isError ? (
        <p className={styles.muted}>无法加载知识库条目。</p>
      ) : query.isPending ? (
        <p className={styles.muted}>加载可注入条目…</p>
      ) : (
        <div className={styles.pickerList}>
          <KbEntryList
            items={items}
            selected={selectedIds}
            unavailableCodes={unavailableCodes}
            onToggle={toggle}
            showLibrary
            emptyMessage="该项目还没有可注入的知识库条目"
          />
        </div>
      )}
      {query.hasNextPage ? (
        <Button
          type="button"
          variant="ghost"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {query.isFetchingNextPage ? "加载中…" : "加载更多"}
        </Button>
      ) : null}
    </section>
  );
}
