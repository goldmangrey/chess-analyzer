import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { BentoCard } from "@/components/ui";
import type { StatsPeriodComparison, StatsSummary } from "@/lib/api/types";
import { formatCpLoss } from "@/lib/format";

export function PrimaryMetricCard({ summary, comparison }: { summary: StatsSummary; comparison: StatsPeriodComparison }) {
  const change = comparison.average_cp_loss_change;
  const improved = change !== null && change < 0;
  const worsened = change !== null && change > 0;
  const DeltaIcon = improved ? ArrowDownRight : worsened ? ArrowUpRight : Minus;

  return (
    <BentoCard as="section" tone="dark" className="h-full p-6 sm:p-8">
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="text-sm font-semibold text-white/60">Средний CP Loss</p>
          <p className="technical-number mt-5 text-6xl font-medium tracking-[-0.07em] text-text-on-dark sm:text-7xl">
            {formatCpLoss(summary.average_cp_loss)}
          </p>
        </div>
        <span className="rounded-full bg-white/10 p-3 text-lime"><DeltaIcon aria-hidden="true" size={21} /></span>
      </div>
      <div className="mt-8 border-t border-white/10 pt-5">
        {change === null ? (
          <p className="text-sm text-white/50">Сравнение появится после двух периодов</p>
        ) : (
          <p className={improved ? "text-sm text-mint" : worsened ? "text-sm text-warm-yellow" : "text-sm text-white/60"}>
            {change > 0 ? "+" : ""}{formatCpLoss(change)} к предыдущему периоду
          </p>
        )}
      </div>
    </BentoCard>
  );
}
