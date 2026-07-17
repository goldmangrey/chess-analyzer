import { ShieldCheck } from "lucide-react";

import { BentoCard } from "@/components/ui";
import { formatPercentage } from "@/lib/format";

export function BlunderFreeCard({ percentage, games }: { percentage: number | null; games: number }) {
  return (
    <BentoCard as="section" tone="yellow" className="h-full p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-text-secondary">Без зевков</p>
          <p className="technical-number mt-3 text-5xl font-semibold tracking-[-0.06em]">{formatPercentage(percentage)}</p>
        </div>
        <span className="rounded-2xl bg-white/60 p-3 text-forest"><ShieldCheck aria-hidden="true" size={22} /></span>
      </div>
      <p className="mt-5 text-sm text-text-secondary">
        {percentage === null ? "Недостаточно данных" : `${games} партий без зевков`}
      </p>
    </BentoCard>
  );
}
