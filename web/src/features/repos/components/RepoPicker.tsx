import { useEffect, useState } from "react";
import { FormField } from "../../../components/ui/FormField";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useRepositories } from "../hooks/useRepoBrowse";
import styles from "./browse.module.css";

const SEARCH_DEBOUNCE_MS = 300;

export interface RepoPickerProps {
  bindingId: string;
  value: string | null;
  onChange: (repoId: string) => void;
  disabled?: boolean;
}

export function RepoPicker({
  bindingId,
  value,
  onChange,
  disabled,
}: RepoPickerProps) {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebounced(search.trim()),
      SEARCH_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [search]);

  const query = useRepositories(bindingId, debounced, { enabled: !disabled });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const options = items.map((item) => ({
    value: item.repoId,
    label: item.repoId === value ? `${item.displayName}（当前）` : item.displayName,
  }));
  if (value && !options.some((option) => option.value === value)) {
    options.unshift({ value, label: `${value}（当前）` });
  }

  return (
    <div className={styles.picker}>
      <FormField label="仓库（实时）">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="按名称 / 关键词检索"
          disabled={disabled}
          aria-label="检索仓库"
        />
      </FormField>
      <FormField label="选择仓库">
        <Select
          options={options}
          value={value ?? ""}
          onChange={onChange}
          placeholder={query.isPending ? "加载仓库…" : "选择仓库"}
          disabled={disabled || options.length === 0}
        />
      </FormField>
      <span className={styles.muted}>默认绑定仓库；列表为供应商实时结果。</span>
    </div>
  );
}
