import { Select } from "../../../components/ui/Select";
import type { KbVersionItem } from "../api/types";

export interface KbVersionSelectorProps {
  versions: KbVersionItem[];
  currentKbId: string;
  onChange: (kbId: string) => void;
}

export function KbVersionSelector({
  versions,
  currentKbId,
  onChange,
}: KbVersionSelectorProps) {
  const ordered = [...versions].sort((a, b) => b.version - a.version);
  return (
    <Select
      aria-label="知识库版本"
      value={currentKbId}
      onChange={onChange}
      options={ordered.map((item) => ({
        value: item.kbId,
        label: `v${item.version}${item.current ? "（最新）" : "（只读）"}`,
      }))}
    />
  );
}
