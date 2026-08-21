"use client";

import { useEffect, useMemo, useRef } from "react";

import { BentoCard } from "@/components/ui";
import type { CriticalMoment, MoveAnalysis } from "@/lib/api/types";
import { buildMoveListRows, criticalMomentScrollBehavior, moveListScrollTop } from "@/lib/review-board";

import { MoveListRow } from "./move-list-row";

export function MoveList({ moves, criticalMoments, selectedPly, onSelect }: { moves: MoveAnalysis[]; criticalMoments: CriticalMoment[]; selectedPly: number; onSelect: (ply: number) => void }) {
  const refs = useRef(new Map<number, HTMLButtonElement>());
  const containerRef = useRef<HTMLDivElement>(null);
  const initialRef = useRef<HTMLButtonElement>(null);
  const rows = useMemo(() => buildMoveListRows(moves), [moves]);
  const criticalPlys = useMemo(() => new Set(criticalMoments.map((moment) => moment.ply)), [criticalMoments]);
  useEffect(() => {
    const container = containerRef.current;
    const item = selectedPly === 0 ? initialRef.current : refs.current.get(selectedPly);
    if (!container || !item) return;
    const containerRect = container.getBoundingClientRect();
    const itemRect = item.getBoundingClientRect();
    const top = moveListScrollTop({ scrollTop: container.scrollTop, clientHeight: container.clientHeight, top: containerRect.top }, { top: itemRect.top, bottom: itemRect.bottom });
    if (top !== null) container.scrollTo({ top, behavior: criticalMomentScrollBehavior(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false) });
  }, [selectedPly]);
  return (
    <BentoCard as="section" className="flex h-full min-h-64 w-full min-w-0 flex-col p-4 sm:p-5 xl:min-h-0">
      <div><h2 className="text-lg font-semibold tracking-[-0.025em]">Ходы</h2><p className="mt-0.5 text-xs text-text-muted">Список партии</p></div>
      <div ref={containerRef} className="minimal-scrollbar mt-3 max-h-[20rem] flex-1 space-y-1 overflow-y-auto overscroll-contain pr-1 xl:max-h-none" tabIndex={0} aria-label="Список ходов партии">
        <button ref={initialRef} type="button" aria-current={selectedPly === 0 ? "step" : undefined} onClick={() => onSelect(0)} className={selectedPly === 0 ? "focus-ring mb-2 min-h-10 w-full rounded-xl bg-surface-dark px-3 py-2 text-left text-sm font-semibold text-white" : "focus-ring mb-2 min-h-10 w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-surface-muted"}>Начало</button>
        {rows.map(([number, pair]) => <MoveListRow key={number} moveNumber={number} white={pair.white} black={pair.black} selectedPly={selectedPly} criticalPlys={criticalPlys} onSelect={onSelect} register={(ply, node) => { if (node) refs.current.set(ply, node); else refs.current.delete(ply); }} />)}
      </div>
    </BentoCard>
  );
}
