import { BentoCard } from "@/components/ui";

export function AnalyzedGamesCard({ analyzed, total }: { analyzed: number; total: number }) {
  const percentage = total > 0 ? Math.min(100, Math.round((analyzed / total) * 100)) : 0;
  const circumference = 2 * Math.PI * 42;
  const offset = circumference * (1 - percentage / 100);

  return (
    <BentoCard as="section" tone="lime" className="flex h-full items-center justify-between gap-5 p-6 sm:p-8">
      <div>
        <p className="text-sm font-semibold text-text-secondary">Готово отчётов</p>
        <p className="technical-number mt-3 text-4xl font-semibold tracking-[-0.055em]">{analyzed} / {total}</p>
        <p className="mt-2 text-xs text-text-muted">из всей истории</p>
      </div>
      <div className="relative size-28 shrink-0" role="img" aria-label={`Готово отчётов для ${percentage}% партий`}>
        <svg viewBox="0 0 100 100" className="-rotate-90" aria-hidden="true">
          <circle cx="50" cy="50" r="42" fill="none" stroke="var(--surface)" strokeWidth="9" />
          <circle cx="50" cy="50" r="42" fill="none" stroke="var(--forest)" strokeWidth="9" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <span className="technical-number absolute inset-0 grid place-items-center text-sm font-bold">{percentage}%</span>
      </div>
    </BentoCard>
  );
}
