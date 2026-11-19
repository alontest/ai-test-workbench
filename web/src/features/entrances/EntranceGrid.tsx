import { EntranceCard } from "./EntranceCard";
import styles from "./entrances.module.css";
import type { Entrance } from "./types";

export interface EntranceGridProps {
  entrances: Entrance[];
}

export function EntranceGrid({ entrances }: EntranceGridProps) {
  return (
    <div className={styles.grid}>
      {entrances.map((entrance) => (
        <EntranceCard key={entrance.key} entrance={entrance} />
      ))}
    </div>
  );
}
