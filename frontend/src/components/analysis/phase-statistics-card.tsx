import { BentoCard } from "@/components/ui";
import type { GameIntelligenceResponse, GamePhase } from "@/lib/api/types";
import { formatCpLoss } from "@/lib/format";


const phases: { key: GamePhase; label: string }[] = [
  { key: "opening", label: "Opening" },
  { key: "middlegame", label: "Middlegame" },
  { key: "endgame", label: "Endgame" },
];


export function PhaseStatisticsCard({ intelligence }: { intelligence: GameIntelligenceResponse }) {
  const present = phases.flatMap(({ key, label }) => {
    const metrics = intelligence.phases[key];
    return metrics ? [{ key, label, metrics }] : [];
  });
  if (present.length === 0) return null;

  return (
    <BentoCard as="section" className="mt-6 p-5 sm:p-6">
      <h2 className="text-sm font-semibold">Статистика по фазам</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {present.map(({ key, label, metrics }) => (
          <div key={key} className="rounded-2xl bg-surface-muted p-4">
            <p className="text-xs font-semibold text-text-secondary">{label}</p>
            <p className="technical-number mt-2 text-xl font-semibold">{formatCpLoss(metrics.average_cp_loss)} <span className="text-xs font-normal text-text-muted">ACPL</span></p>
            <p className="mt-1 text-xs text-text-muted">{metrics.user_moves} ходов · ply {metrics.start_ply}–{metrics.end_ply}</p>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}
