import { evaluationWhitePercent } from "@/lib/chess-position";
import { formatEvaluation } from "@/lib/format";

export function EvaluationBar({ evaluation }: { evaluation: number | null }) {
  // Keep the server-rendered style byte-for-byte stable during hydration.
  const white = evaluationWhitePercent(evaluation).toFixed(4);
  return (
    <div className="flex w-8 shrink-0 flex-col overflow-hidden rounded-full bg-surface-dark shadow-[var(--shadow-soft)] sm:w-10" role="img" aria-label={`Оценка позиции ${formatEvaluation(evaluation)}`}>
      <div className="relative bg-white transition-[height] duration-300 motion-reduce:transition-none" style={{ height: `${white}%` }}><span className="technical-number absolute left-1/2 top-2 -translate-x-1/2 text-[10px] font-bold text-text-primary">{formatEvaluation(evaluation)}</span></div>
      <div className="flex-1 bg-surface-dark" />
    </div>
  );
}
