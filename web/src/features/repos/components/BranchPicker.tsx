import { FormField } from "../../../components/ui/FormField";
import { Select } from "../../../components/ui/Select";
import { useBranches } from "../hooks/useRepoBrowse";
import styles from "./browse.module.css";

export interface BranchPickerProps {
  bindingId: string;
  repoId: string | null;
  value: string | null;
  onChange: (branch: string) => void;
  disabled?: boolean;
}

export function BranchPicker({
  bindingId,
  repoId,
  value,
  onChange,
  disabled,
}: BranchPickerProps) {
  const query = useBranches(bindingId, repoId, "", { enabled: !disabled });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const options = items.map((branch) => ({
    value: branch.name,
    label: branch.isDefault ? `${branch.name}（默认）` : branch.name,
  }));
  if (value && !options.some((option) => option.value === value)) {
    options.unshift({ value, label: value });
  }

  return (
    <div className={styles.picker}>
      <FormField label="分支（实时，分页）">
        <Select
          options={options}
          value={value ?? ""}
          onChange={onChange}
          placeholder={query.isPending ? "加载分支…" : "选择分支"}
          disabled={disabled || options.length === 0}
        />
      </FormField>
      <span className={styles.muted}>默认选中默认分支；切换后提交与目录树同步切换。</span>
    </div>
  );
}
