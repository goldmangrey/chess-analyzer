import { BentoCard } from "@/components/ui";
import type { CriticalMomentType, ErrorType, GameIntelligenceResponse, GamePhase, MoveClassification } from "@/lib/api/types";
import { formatEvaluation } from "@/lib/format";


const typeLabels: Record<CriticalMomentType, string> = {
  turning_point: "Turning point",
  blunder: "Blunder",
  missed_opportunity: "Missed opportunity",
  missed_mate: "Missed mate",
  allowed_mate: "Allowed mate",
  best_move: "Best moment",
};

const phaseLabels: Record<GamePhase, string> = {
  opening: "Opening",
  middlegame: "Middlegame",
  endgame: "Endgame",
};

const annotations: Record<MoveClassification, string> = {
  normal: "",
  inaccuracy: "?!",
  mistake: "?",
  blunder: "??",
};

const errorLabels: Record<ErrorType, string> = {
  hanging_piece: "Hanging piece",
  missed_capture: "Missed capture",
  missed_check: "Missed check",
  missed_mate: "Missed mate",
  allowed_mate: "Allowed mate",
  king_safety: "King safety",
  development: "Development",
  bad_exchange: "Bad exchange",
  pawn_structure: "Pawn structure",
  tactical_pattern: "Tactical pattern",
  fork: "Fork",
  pin: "Pin",
  skewer: "Skewer",
  back_rank: "Back rank",
};


export function CriticalMomentsCard({ intelligence }: { intelligence: GameIntelligenceResponse }) {
  if (intelligence.critical_moments.length === 0) return null;
  const visibleErrors = new Map(
    intelligence.errors
      .filter((error) => error.primary_type !== null && error.confidence !== "low")
      .map((error) => [error.ply, error] as const),
  );
  return (
    <BentoCard as="section" className="mt-6 p-5 sm:p-6">
      <h2 className="text-sm font-semibold">Critical moments</h2>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {intelligence.critical_moments.map((moment) => {
          const error = visibleErrors.get(moment.ply);
          return <article key={`${moment.ply}-${moment.type}`} className="rounded-2xl bg-surface-muted p-4">
            <div className="flex items-start justify-between gap-3">
              <div><p className="font-semibold">{moment.move_number}{moment.ply % 2 === 0 ? "..." : "."}{moment.move_san ?? moment.move_uci}{moment.type === "best_move" ? "!" : annotations[moment.severity]}</p><p className="mt-1 text-xs text-text-secondary">{typeLabels[moment.type]}</p></div>
              {moment.phase ? <span className="text-xs font-semibold text-forest-light">{phaseLabels[moment.phase]}</span> : null}
            </div>
            <p className="technical-number mt-3 text-sm text-text-secondary">{formatEvaluation(moment.evaluation_before_user_pov)} → {formatEvaluation(moment.evaluation_after_user_pov)}</p>
            {error?.primary_type ? <p className="mt-2 text-xs font-medium text-coral">{errorLabels[error.primary_type]}</p> : null}
          </article>;
        })}
      </div>
    </BentoCard>
  );
}
