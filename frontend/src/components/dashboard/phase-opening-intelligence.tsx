import { BentoCard } from "@/components/ui";
import type { DashboardOpeningRowViewModel, DashboardViewModel } from "@/lib/dashboard-view-model";
import { formatAccuracy } from "@/lib/human-metrics";

export function PhaseSummaryCard({ model }: { model: DashboardViewModel }) {
  return <BentoCard as="section" className="p-4 sm:p-5" aria-labelledby="phase-summary-title">
    <div className="flex items-baseline justify-between gap-3"><h2 id="phase-summary-title" className="text-sm font-semibold">Игра по фазам</h2><p className="text-[11px] text-text-muted">Точность</p></div>
    <div className="mt-3 grid grid-cols-3 divide-x divide-[var(--border-subtle)]">{model.phases.map((phase) => <div key={phase.phase} className={`min-w-0 px-2 first:pl-0 last:pr-0 sm:px-4 ${phase.isWeakest ? "rounded-xl bg-mistake-surface/45 py-2" : "py-2"}`}>
      <p className="text-xs font-semibold leading-4 text-text-secondary sm:text-sm">{phase.label}</p>
      <p className={`technical-number mt-1 text-[1.35rem] font-semibold leading-none sm:text-2xl ${phase.isWeakest ? "text-mistake" : "text-text-primary"}`}>{phase.isInsufficient ? "—" : formatAccuracy(phase.accuracy)}</p>
      <p className={`mt-1.5 text-[11px] leading-4 ${phase.isWeakest ? "font-semibold text-mistake" : "text-text-muted"}`}>{phase.isWeakest ? "Слабейшая фаза" : phase.qualityLabel ?? phase.support}</p>
      {!phase.isInsufficient && !phase.isWeakest ? <p className="mt-0.5 text-[10px] text-text-muted">{phase.support}</p> : null}
    </div>)}</div>
  </BentoCard>;
}

export function OpeningIntelligenceCard({ model }: { model: DashboardViewModel }) {
  const openings = model.openings;
  return <BentoCard as="section" className="h-full p-4 sm:p-5" aria-labelledby="openings-title">
    <div className="flex flex-wrap items-baseline justify-between gap-2"><div><p className="text-xs font-semibold text-text-muted">Дебютный репертуар</p><h2 id="openings-title" className="mt-1 text-lg font-semibold tracking-[-0.025em]">Ваши дебюты</h2></div>{openings.coverageLabel ? <p className="text-[11px] text-text-muted">{openings.coverageLabel}</p> : null}</div>
    {openings.hasData ? <div className="mt-4 grid gap-4 sm:grid-cols-2"><OpeningColorGroup title="Белыми" rows={openings.white} /><OpeningColorGroup title="Чёрными" rows={openings.black} /></div> : <p className="mt-4 text-sm text-text-muted">Дебюты пока не определены.</p>}
  </BentoCard>;
}

function OpeningColorGroup({ title, rows }: { title: string; rows: DashboardOpeningRowViewModel[] }) {
  return <section aria-label={title}><h3 className="text-xs font-semibold text-forest-light">{title}</h3>{rows.length ? <div className="mt-2 divide-y divide-[var(--border-subtle)]">{rows.map((opening) => <div key={opening.key} className="flex min-h-14 min-w-0 items-start justify-between gap-3 py-2.5">
    <div className="min-w-0"><p className="text-sm font-semibold leading-5 [overflow-wrap:anywhere]">{opening.name}</p>{opening.variation ? <p className="mt-0.5 text-xs leading-4 text-text-secondary [overflow-wrap:anywhere]">{opening.variation}</p> : null}<p className="mt-1 text-[11px] text-text-muted">{opening.eco ?? "Без ECO"} · {opening.record}</p></div>
    <span className="technical-number shrink-0 pt-0.5 text-xs font-semibold text-text-secondary">{opening.gameCount}</span>
  </div>)}</div> : <p className="mt-2 text-xs text-text-muted">Недостаточно распознанных дебютов.</p>}</section>;
}
