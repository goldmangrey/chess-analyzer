import { BentoCard, StatusPill } from "@/components/ui";
import type { MoveAnalysis } from "@/lib/api/types";
import { formatEvaluation, formatMoveLabel } from "@/lib/format";
import { moveClassificationLabel } from "@/lib/status";

const tones = { normal: "neutral", inaccuracy: "warning", mistake: "warning", blunder: "danger" } as const;

export function MoveDetailsCard({ move }: { move: MoveAnalysis | null }) {
  if (!move) {
    return <BentoCard as="section" tone="muted" className="p-6"><h2 className="text-xl font-semibold tracking-[-0.035em]">Начальная позиция</h2><p className="mt-3 text-sm leading-6 text-text-secondary">Выберите ход в списке или используйте навигацию.</p></BentoCard>;
  }
  const details = [
    ["Сыграно", move.played_move_san ?? move.played_move_uci],
    ["Лучший ход", move.best_move_san ?? move.best_move_uci ?? "—"],
    ["Оценка до", formatEvaluation(move.evaluation_before_cp)],
    ["Оценка после", formatEvaluation(move.evaluation_after_cp)],
    ["CP Loss", String(move.centipawn_loss)],
  ];
  return (
    <BentoCard as="section" className="p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-forest-light">{move.is_user_move ? "Ваш ход" : "Ход соперника"}</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">{formatMoveLabel(move)}</h2></div><StatusPill tone={tones[move.classification]} dot>{moveClassificationLabel(move.classification)}</StatusPill></div>
      <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">{details.map(([label, value]) => <div key={label} className="rounded-2xl bg-surface-muted p-3"><dt className="text-xs text-text-muted">{label}</dt><dd className="technical-number mt-2 break-words text-sm font-semibold">{value}</dd></div>)}</dl>
      <div className="mt-5 border-t border-[var(--border-subtle)] pt-5"><p className="text-xs font-semibold text-text-muted">Principal variation</p><p className="technical-number mt-2 break-words text-sm leading-6 text-text-secondary">{move.principal_variation || "—"}</p></div>
    </BentoCard>
  );
}
