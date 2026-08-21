import { AnalyzeGameButton } from "./analyze-game-button";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { LocalDateTime, StatusPill } from "@/components/ui";
import type { ApiGameListItem } from "@/lib/api/types";
import { localizeOpeningName } from "@/lib/opening-localization";
import { analysisStatusLabel, analysisStatusTone, gameResultLabel } from "@/lib/status";

const resultClasses = {
  win: "bg-best-surface text-best",
  draw: "bg-black/[0.055] text-text-secondary",
  loss: "bg-blunder-surface text-blunder-text",
};

function ratings(game: ApiGameListItem): string | null {
  const own = game.user_color === "white" ? game.white_rating : game.black_rating;
  const opponent = game.user_color === "white" ? game.black_rating : game.white_rating;
  if (own === null && opponent === null) return null;
  return `${own ?? "—"} / ${opponent ?? "—"}`;
}

export function GameRow({ game }: { game: ApiGameListItem }) {
  const ratingText = ratings(game);
  return (
    <tr className="group transition hover:bg-surface-muted/70">
      <td className="rounded-l-2xl py-4 pl-4 pr-3">
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className={game.user_color === "white" ? "size-3 rounded-sm border border-[var(--border-strong)] bg-white" : "size-3 rounded-sm bg-surface-dark"} />
          <div className="min-w-0"><Link href={`/games/${game.id}`} className="focus-ring group/link inline-flex max-w-full items-center gap-1 rounded-lg text-sm font-semibold hover:text-forest"><span className="truncate">{game.opponent_username}</span><ArrowUpRight aria-hidden="true" size={14} className="shrink-0 transition group-hover/link:-translate-y-0.5 group-hover/link:translate-x-0.5" /></Link>{ratingText ? <p className="technical-number mt-1 text-xs text-text-muted">мой / соп. {ratingText}</p> : null}</div>
        </div>
      </td>
      <td className="px-3 py-4"><p className="whitespace-nowrap text-sm"><LocalDateTime value={game.played_at} dateOnly /></p><p className="technical-number mt-1 text-xs text-text-muted">{game.time_control ?? "—"}</p></td>
      <td className="max-w-64 px-3 py-4"><p className="truncate text-sm">{localizeOpeningName(game.opening_name) ?? game.opening_code ?? "Дебют не определён"}</p>{game.opening_name && game.opening_code ? <p className="mt-1 text-xs font-bold text-forest-light">{game.opening_code}</p> : null}</td>
      <td className="px-3 py-4"><span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${resultClasses[game.result]}`}>{gameResultLabel(game.result)}</span></td>
      <td className="technical-number px-3 py-4 text-sm">{game.mistakes}</td>
      <td className="technical-number px-3 py-4 text-sm text-blunder-text">{game.blunders}</td>
      <td className="px-3 py-4"><StatusPill tone={analysisStatusTone(game.analysis_status)} dot className={game.analysis_status === "analyzing" ? "[&>span:first-child]:animate-pulse motion-reduce:[&>span:first-child]:animate-none" : undefined}>{analysisStatusLabel(game.analysis_status)}</StatusPill></td>
      <td className="rounded-r-2xl py-4 pl-3 pr-4 text-right">{game.analysis_status === "completed" ? <Link href={`/games/${game.id}`} className="focus-ring inline-flex min-h-9 items-center rounded-full bg-forest px-4 text-xs font-semibold text-white">Открыть отчёт</Link> : <AnalyzeGameButton gameId={game.id} status={game.analysis_status} />}</td>
    </tr>
  );
}
