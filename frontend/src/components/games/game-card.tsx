import { AnalyzeGameButton } from "./analyze-game-button";

import { StatusPill } from "@/components/ui";
import type { ApiGameListItem } from "@/lib/api/types";
import { formatCpLoss, formatDate } from "@/lib/format";
import { analysisStatusLabel, analysisStatusTone, gameResultLabel } from "@/lib/status";

const resultClasses = { win: "text-best", draw: "text-text-secondary", loss: "text-blunder-text" };

export function GameCard({ game }: { game: ApiGameListItem }) {
  return (
    <article className="rounded-[1.5rem] bg-surface p-5 shadow-[var(--shadow-soft)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0"><div className="flex items-center gap-2"><span aria-hidden="true" className={game.user_color === "white" ? "size-3 rounded-sm border border-[var(--border-strong)] bg-white" : "size-3 rounded-sm bg-surface-dark"} /><h2 className="truncate text-lg font-semibold tracking-[-0.025em]">vs {game.opponent_username}</h2></div><p className="mt-2 text-xs text-text-muted">{formatDate(game.played_at)} · {game.time_control ?? "Контроль не указан"}</p></div>
        <strong className={`text-sm ${resultClasses[game.result]}`}>{gameResultLabel(game.result)}</strong>
      </div>
      <div className="mt-5 rounded-2xl bg-surface-muted p-4"><p className="text-xs font-bold text-forest-light">{game.opening_code ?? "—"}</p><p className="mt-1 text-sm">{game.opening_name ?? "Дебют не определён"}</p></div>
      <dl className="mt-5 grid grid-cols-3 gap-3 text-center"><div><dt className="text-xs text-text-muted">CP Loss</dt><dd className="technical-number mt-1 font-semibold">{formatCpLoss(game.average_cp_loss)}</dd></div><div><dt className="text-xs text-text-muted">Ошибки</dt><dd className="technical-number mt-1 font-semibold">{game.mistakes}</dd></div><div><dt className="text-xs text-text-muted">Зевки</dt><dd className="technical-number mt-1 font-semibold text-blunder-text">{game.blunders}</dd></div></dl>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border-subtle)] pt-4"><StatusPill tone={analysisStatusTone(game.analysis_status)} dot className={game.analysis_status === "analyzing" ? "[&>span:first-child]:animate-pulse motion-reduce:[&>span:first-child]:animate-none" : undefined}>{analysisStatusLabel(game.analysis_status)}</StatusPill><AnalyzeGameButton gameId={game.id} status={game.analysis_status} /></div>
    </article>
  );
}
