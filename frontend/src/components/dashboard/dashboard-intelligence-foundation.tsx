import { BentoCard } from "@/components/ui";
import type { DashboardSegmentViewModel, DashboardViewModel } from "@/lib/dashboard-view-model";
import { formatAccuracy } from "@/lib/human-metrics";

import { ChessProfileHero } from "./chess-profile-hero";
import { OpeningIntelligenceCard, PhaseSummaryCard } from "./phase-opening-intelligence";
import { RecurringMistakesCard, WeaknessStrengthCards } from "./weakness-intelligence";

export function DashboardTierOne({ model }: { model: DashboardViewModel }) {
  return <section aria-labelledby="profile-title" data-dashboard-tier="1" className="space-y-3">
    <ChessProfileHero hero={model.hero} />
    <WeaknessStrengthCards model={model} />
    <PhaseSummaryCard model={model} />
  </section>;
}

export function RecurringMistakesFoundation({ model }: { model: DashboardViewModel }) {
  return <RecurringMistakesCard model={model} />;
}

export function OpeningFoundation({ model }: { model: DashboardViewModel }) {
  return <OpeningIntelligenceCard model={model} />;
}

export function SegmentFoundation({ model }: { model: DashboardViewModel }) {
  const hasData = [...model.segments.timeControls, ...model.segments.colors].some((segment) => segment.games > 0);
  return <BentoCard as="section" className="h-full p-4 sm:p-5" aria-labelledby="segments-title"><p className="text-xs font-semibold text-text-muted">Контекст игры</p><h2 id="segments-title" className="mt-1 text-lg font-semibold tracking-[-0.025em]">Сегменты</h2>{hasData ? <div className="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-1"><SegmentGroup title="Контроль времени" segments={model.segments.timeControls} /><SegmentGroup title="По цвету" segments={model.segments.colors} /></div> : <p className="mt-4 text-sm text-text-muted">Недостаточно данных по сегментам.</p>}</BentoCard>;
}

function SegmentGroup({ title, segments }: { title: string; segments: DashboardSegmentViewModel[] }) {
  return <section aria-label={title}><h3 className="text-xs font-semibold text-forest-light">{title}</h3><div className="mt-2 divide-y divide-[var(--border-subtle)]">{segments.map((segment) => <div key={segment.key} className="flex min-h-12 items-center justify-between gap-3 py-2"><div className="min-w-0"><p className="text-sm font-semibold">{segment.label}</p><p className="mt-0.5 text-[11px] text-text-muted">{segment.gameCount}</p></div><div className="shrink-0 text-right"><p className="technical-number text-lg font-semibold leading-none">{segment.isInsufficient ? "—" : formatAccuracy(segment.accuracy)}</p>{segment.isInsufficient ? <p className="mt-1 text-[10px] text-text-muted">Недостаточно данных</p> : segment.qualityLabel ? <p className="mt-1 text-[10px] text-text-muted">{segment.qualityLabel}</p> : null}</div></div>)}</div></section>;
}
