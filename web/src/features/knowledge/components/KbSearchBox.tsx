import { useEffect, useRef, useState } from "react";
import { Input } from "../../../components/ui/Input";
import styles from "./knowledge.module.css";

const SEARCH_DEBOUNCE_MS = 300;
const SEARCH_MAX_CHARS = 100;

export interface KbSearchBoxProps {
  value: string;
  onChange: (q: string) => void;
  placeholder?: string;
  label?: string;
  debounceMs?: number;
}

export function KbSearchBox({
  value,
  onChange,
  placeholder = "检索：ENT- / ENT-001 / 关键词",
  label = "检索条目",
  debounceMs = SEARCH_DEBOUNCE_MS,
}: KbSearchBoxProps) {
  const [draft, setDraft] = useState(value);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(
    () => () => {
      if (timer.current !== undefined) {
        window.clearTimeout(timer.current);
      }
    },
    [],
  );

  function handleInput(next: string) {
    const limited = Array.from(next).slice(0, SEARCH_MAX_CHARS).join("");
    setDraft(limited);
    if (timer.current !== undefined) {
      window.clearTimeout(timer.current);
    }
    timer.current = window.setTimeout(() => onChange(limited), debounceMs);
  }

  return (
    <Input
      className={styles.search}
      type="search"
      value={draft}
      maxLength={SEARCH_MAX_CHARS}
      placeholder={placeholder}
      aria-label={label}
      onChange={(event) => handleInput(event.target.value)}
    />
  );
}
