import { BentoCard } from "@/components/ui";
import type { OpeningWeakness } from "@/lib/api/types";
import { formatMetric, formatPercentage } from "@/lib/format";

export function WeakestOpeningsCard({ openings }: { openings: OpeningWeakness[] }) {
  const maxScore = Math.max(...openings.map((opening) => opening.weakness_score), 1);
  return (
    <BentoCard as="section" tone="muted" className="h-full p-6 sm:p-8">
      <h2 className="text-2xl font-semibold tracking-[-0.04em]">Слабые дебюты</h2>
      <p className="mt-2 text-sm text-text-secondary">Рейтинг основан только на ваших ходах.</p>
      {openings.length === 0 ? (
        <div className="grid min-h-56 place-items-center text-center text-sm leading-6 text-text-muted">Нужно минимум 3 проанализированные партии в одном дебюте</div>
      ) : (
        <div className="mt-7 space-y-6">
          {openings.map((opening) => {
            const severity = Math.max(4, (opening.weakness_score / maxScore) * 100);
            return (
              <article key={`${opening.opening_code ?? ""}-${opening.opening_name ?? ""}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0"><p className="text-xs font-bold text-forest-light">{opening.opening_code ?? "—"}</p><h3 className="mt-1 truncate text-sm font-semibold">{opening.opening_name ?? "Без названия"}</h3></div>
                  <p className="shrink-0 text-xs text-text-muted">{opening.games_count} партий</p>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-black/[0.06]" aria-label={`Относительная сложность ${Math.round(severity)}%`}>
                  <div className="h-full rounded-full bg-mistake" style={{ width: `${severity}%` }} />
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 text-xs text-text-secondary"><span>Поражения {formatPercentage(opening.loss_rate * 100)}</span><span>Зевки / партия {formatMetric(opening.blunders_per_game, 2)}</span></div>
              </article>
            );
          })}
        </div>
      )}
    </BentoCard>
  );
}
