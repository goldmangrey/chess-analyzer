import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { BentoCard } from "@/components/ui";
import type { DashboardProgressViewModel } from "@/lib/dashboard-view-model";
import { formatAccuracy, formatPercentagePointChange } from "@/lib/human-metrics";

const directionClasses = {
  improving: "text-forest", stable: "text-text-secondary", mixed: "text-inaccuracy-strong",
  worsening: "text-mistake", insufficient: "text-text-muted",
} as const;

function DirectionIcon({ direction }: { direction: DashboardProgressViewModel["accuracyDirection"] }) {
  const Icon = direction === "improving" ? ArrowUpRight : direction === "worsening" ? ArrowDownRight : Minus;
  return <Icon aria-hidden="true" size={16} />;
}

export function ProgressComparison({ progress }: { progress: DashboardProgressViewModel }) {
  const delta = progress.hasComparison ? formatPercentagePointChange(progress.delta) : null;
  return <BentoCard as="section" className="h-full p-4 sm:p-5" aria-labelledby="progress-title">
    <div className="flex flex-wrap items-baseline justify-between gap-2"><div><p className="text-xs font-semibold text-text-muted">Динамика игры</p><h2 id="progress-title" className="mt-1 text-lg font-semibold tracking-[-0.025em]">Прогресс</h2></div><p className="text-[11px] text-text-muted">{progress.windowLabel}</p></div>
    {progress.hasCurrent ? <>
      <div className="mt-4 flex items-end justify-between gap-4"><div><p className="text-xs font-semibold text-text-secondary">Точность</p><p className="technical-number mt-1 text-[2rem] font-semibold leading-none tracking-[-0.045em]">{formatAccuracy(progress.current)}</p></div>{progress.hasComparison ? <div className="text-right"><p className="text-xs text-text-muted">Было {formatAccuracy(progress.previous)}</p>{delta ? <p className={`technical-number mt-1 text-sm font-semibold ${directionClasses[progress.accuracyDirection]}`}>{delta}</p> : null}</div> : null}</div>
      {progress.hasComparison ? <div className="mt-4 flex items-center gap-2" aria-label={`Точность изменилась с ${formatAccuracy(progress.previous)} до ${formatAccuracy(progress.current)}`}><span className="technical-number text-xs text-text-muted">{formatAccuracy(progress.previous)}</span><span aria-hidden="true" className="h-px flex-1 bg-[var(--border-strong)]" /><span aria-hidden="true" className="size-2 rounded-full bg-forest" /><span className="technical-number text-xs font-semibold">{formatAccuracy(progress.current)}</span></div> : <p className="mt-4 text-xs text-text-muted">Недостаточно предыдущих данных для сравнения.</p>}
      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[var(--border-subtle)] pt-3"><div><p className="text-[11px] text-text-muted">Тренд точности</p><p className={`mt-1 flex items-center gap-1 text-sm font-semibold ${directionClasses[progress.accuracyDirection]}`}><DirectionIcon direction={progress.accuracyDirection} />{progress.accuracyDirectionLabel}</p></div><div><p className="text-[11px] text-text-muted">Общий тренд</p><p className={`mt-1 text-sm font-semibold ${directionClasses[progress.overallDirection]}`}>{progress.overallDirectionLabel}</p></div></div>
    </> : <p className="mt-4 text-sm text-text-muted">Недостаточно данных о точности.</p>}
  </BentoCard>;
}
