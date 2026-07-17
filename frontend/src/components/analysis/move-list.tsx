"use client";

import { useEffect, useMemo, useRef } from "react";

import { BentoCard } from "@/components/ui";
import type { MoveAnalysis } from "@/lib/api/types";

import { MoveListRow } from "./move-list-row";

export function MoveList({ moves, selectedPly, onSelect }: { moves: MoveAnalysis[]; selectedPly: number; onSelect: (ply: number) => void }) {
  const refs = useRef(new Map<number, HTMLButtonElement>());
  const rows = useMemo(() => {
    const grouped = new Map<number, { white?: MoveAnalysis; black?: MoveAnalysis }>();
    for (const move of moves) grouped.set(move.move_number, { ...grouped.get(move.move_number), [move.player_color]: move });
    return [...grouped.entries()].sort(([a], [b]) => a - b);
  }, [moves]);
  useEffect(() => { if (selectedPly > 0) refs.current.get(selectedPly)?.scrollIntoView({ block: "nearest" }); }, [selectedPly]);
  return (
    <BentoCard as="section" className="flex min-h-[24rem] min-w-0 flex-col p-5 sm:min-w-[20rem] sm:p-6">
      <div><h2 className="text-xl font-semibold tracking-[-0.035em]">Ходы</h2><p className="mt-1 text-xs text-text-muted">Все полуходы партии</p></div>
      <div className="minimal-scrollbar mt-5 max-h-[34rem] flex-1 space-y-1 overflow-y-auto pr-1" tabIndex={0} aria-label="Список ходов партии">
        <button type="button" aria-pressed={selectedPly === 0} onClick={() => onSelect(0)} className={selectedPly === 0 ? "focus-ring mb-2 w-full rounded-xl bg-surface-dark px-3 py-2 text-left text-sm font-semibold text-white" : "focus-ring mb-2 w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-surface-muted"}>Начальная позиция</button>
        {rows.map(([number, pair]) => <MoveListRow key={number} moveNumber={number} white={pair.white} black={pair.black} selectedPly={selectedPly} onSelect={onSelect} register={(ply, node) => { if (node) refs.current.set(ply, node); else refs.current.delete(ply); }} />)}
      </div>
    </BentoCard>
  );
}
