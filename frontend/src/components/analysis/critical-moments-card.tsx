import { ChevronLeft, ChevronRight } from "lucide-react";

import { BentoCard } from "@/components/ui";
import type { GameIntelligenceResponse } from "@/lib/api/types";
import { adjacentCriticalMomentPly, criticalMomentPresentation } from "@/lib/review-board";

const toneClasses = {
  best: "bg-best text-white",
  normal: "bg-forest text-white",
  inaccuracy: "bg-inaccuracy text-text-primary",
  mistake: "bg-mistake text-text-primary",
  blunder: "bg-blunder text-white",
} as const;

export function CriticalMomentsCard({ intelligence, selectedPly, onSelectPly }: { intelligence: GameIntelligenceResponse; selectedPly: number; onSelectPly: (ply: number) => void }) {
  const moments = intelligence.critical_moments;
  if (moments.length === 0) return null;
  const errors = new Map(intelligence.errors.map((error) => [error.ply, error] as const));
  const previousPly = adjacentCriticalMomentPly(moments, selectedPly, "previous");
  const nextPly = adjacentCriticalMomentPly(moments, selectedPly, "next");

  return (
    <BentoCard as="section" className="p-5 sm:p-6" aria-labelledby="critical-moments-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="text-xs font-bold uppercase tracking-[0.14em] text-forest-light">Ключевые события</p><h2 id="critical-moments-title" className="mt-1 text-xl font-semibold tracking-[-0.035em]">Критические моменты</h2></div>
        {moments.length > 1 ? <div className="flex items-center gap-2"><button type="button" disabled={previousPly === null} onClick={() => previousPly !== null && onSelectPly(previousPly)} aria-label="Предыдущий критический момент" className="focus-ring inline-flex min-h-10 items-center gap-1 rounded-xl border border-[var(--border-subtle)] px-3 text-xs font-semibold text-forest transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft aria-hidden="true" size={16} />Предыдущий</button><button type="button" disabled={nextPly === null} onClick={() => nextPly !== null && onSelectPly(nextPly)} aria-label="Следующий критический момент" className="focus-ring inline-flex min-h-10 items-center gap-1 rounded-xl border border-[var(--border-subtle)] px-3 text-xs font-semibold text-forest transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40">Следующий<ChevronRight aria-hidden="true" size={16} /></button></div> : null}
      </div>
      <ol className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {moments.map((moment, index) => {
          const active = selectedPly === moment.ply;
          const item = criticalMomentPresentation(moment, errors.get(moment.ply) ?? null, index + 1);
          return <li key={`${moment.ply}-${moment.type}`}><button type="button" onClick={() => onSelectPly(moment.ply)} aria-current={active ? "step" : undefined} aria-label={`${item.rank}. ${item.moveLabel}. ${item.typeLabel}. ${item.severityLabel}`} className={`focus-ring group relative h-full min-h-40 w-full rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md ${active ? "border-forest bg-[color-mix(in_srgb,var(--forest)_6%,var(--surface))] shadow-[0_0_0_2px_color-mix(in_srgb,var(--forest)_12%,transparent)]" : "border-[var(--border-subtle)] bg-surface-muted"}`}>
            <div className="flex items-start gap-3"><span aria-hidden="true" className={`grid size-8 shrink-0 place-items-center rounded-full text-xs font-black ${active ? "bg-forest text-white" : "bg-surface text-text-muted"}`}>{item.rank}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-start justify-between gap-2"><p className="technical-number text-lg font-semibold">{item.moveLabel}</p><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${toneClasses[item.severityTone]}`}>{item.severityLabel}</span></div><p className="mt-2 text-xs font-bold uppercase tracking-[0.1em] text-forest-light">{item.typeLabel}</p></div></div>
            <p className="mt-4 text-sm font-semibold text-text-primary">{item.conciseReason}</p>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs"><span className="technical-number text-text-secondary">{item.evaluationBefore ?? "—"} → {item.evaluationAfter ?? "—"}</span>{item.phaseLabel ? <span className="font-semibold text-text-muted">{item.phaseLabel}</span> : null}</div>
            {active ? <p className="mt-3 flex items-center gap-2 text-xs font-bold text-forest"><span aria-hidden="true" className="size-2 rounded-full bg-forest" />Сейчас на доске</p> : null}
          </button></li>;
        })}
      </ol>
    </BentoCard>
  );
}
