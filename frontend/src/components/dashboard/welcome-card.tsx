import { BentoCard } from "@/components/ui";
import type { StatsPeriodComparison, StatsSummary } from "@/lib/api/types";
import { formatCpLoss, formatMetric } from "@/lib/format";

function comparisonText(comparison: StatsPeriodComparison): string {
  const change = comparison.average_cp_loss_change;
  if (change === null || comparison.previous_games_count === 0) {
    return "Сыграйте и проанализируйте больше партий, чтобы увидеть динамику";
  }
  if (change < 0) {
    return `За последние ${comparison.recent_games_count} партий средний CP Loss снизился на ${formatCpLoss(Math.abs(change))}`;
  }
  if (change > 0) {
    return `Средний CP Loss вырос на ${formatCpLoss(change)} по сравнению с предыдущим периодом`;
  }
  return "Средний CP Loss не изменился по сравнению с предыдущим периодом";
}

export function WelcomeCard({ summary, comparison }: { summary: StatsSummary; comparison: StatsPeriodComparison }) {
  return (
    <BentoCard as="section" tone="mint" className="relative h-full overflow-hidden p-6 sm:p-8">
      <div aria-hidden="true" className="absolute -right-12 -top-14 size-48 rounded-full bg-lime-surface/80 blur-3xl" />
      <div className="relative">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Ваша шахматная форма</p>
        <h1 className="mt-5 text-3xl font-semibold tracking-[-0.05em] sm:text-5xl">Добро пожаловать, Yeskendir</h1>
        <p className="mt-5 max-w-2xl text-sm leading-7 text-text-secondary">{comparisonText(comparison)}</p>
        <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 border-t border-forest/10 pt-5 text-sm">
          <span><strong className="technical-number text-best">{formatMetric(summary.wins, 0)}</strong> побед</span>
          <span><strong className="technical-number text-text-primary">{formatMetric(summary.draws, 0)}</strong> ничьих</span>
          <span><strong className="technical-number text-blunder">{formatMetric(summary.losses, 0)}</strong> поражений</span>
        </div>
      </div>
    </BentoCard>
  );
}
