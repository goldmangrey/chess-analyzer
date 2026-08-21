import { AnalyzeGameButton } from "./analyze-game-button";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { LocalDateTime, StatusPill } from "@/components/ui";
import type { ApiGameListItem } from "@/lib/api/types";
import { localizeOpeningName } from "@/lib/opening-localization";
import { analysisStatusLabel, analysisStatusTone, gameResultLabel } from "@/lib/status";

const resultClasses = { win: "text-best", draw: "text-text-secondary", loss: "text-blunder-text" };

export function GameCard({ game }: { game: ApiGameListItem }) {
  return (
    <article className="rounded-[1.5rem] bg-surface p-5 shadow-[var(--shadow-soft)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0"><div className="flex items-center gap-2"><span aria-hidden="true" className={game.user_color === "white" ? "size-3 rounded-sm border border-[var(--border-strong)] bg-white" : "size-3 rounded-sm bg-surface-dark"} /><h2 className="truncate text-lg font-semibold tracking-[-0.025em]"><Link href={`/games/${game.id}`} className="focus-ring group/link inline-flex items-center gap-1 rounded-lg hover:text-forest">vs {game.opponent_username}<ArrowUpRight aria-hidden="true" size={15} className="transition group-hover/link:-translate-y-0.5 group-hover/link:translate-x-0.5" /></Link></h2></div><p className="mt-2 text-xs text-text-muted"><LocalDateTime value={game.played_at} dateOnly /> · {game.time_control ?? "Контроль не указан"}</p></div>
        <strong className={`text-sm ${resultClasses[game.result]}`}>{gameResultLabel(game.result)}</strong>
      </div>
      <div className="mt-4 rounded-2xl bg-surface-muted p-3.5"><p className="text-sm">{localizeOpeningName(game.opening_name) ?? game.opening_code ?? "Дебют не определён"}</p>{game.opening_name && game.opening_code ? <p className="mt-1 text-xs font-bold text-forest-light">{game.opening_code}</p> : null}</div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-center"><div><dt className="text-xs text-text-muted">Ошибки</dt><dd className="technical-number mt-1 font-semibold">{game.mistakes}</dd></div><div><dt className="text-xs text-text-muted">Зевки</dt><dd className="technical-number mt-1 font-semibold text-blunder-text">{game.blunders}</dd></div></dl>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border-subtle)] pt-4"><StatusPill tone={analysisStatusTone(game.analysis_status)} dot className={game.analysis_status === "analyzing" ? "[&>span:first-child]:animate-pulse motion-reduce:[&>span:first-child]:animate-none" : undefined}>{analysisStatusLabel(game.analysis_status)}</StatusPill>{game.analysis_status === "completed" ? <Link href={`/games/${game.id}`} className="focus-ring inline-flex min-h-9 items-center rounded-full bg-forest px-4 text-xs font-semibold text-white">Открыть отчёт</Link> : <AnalyzeGameButton gameId={game.id} status={game.analysis_status} />}</div>
    </article>
  );
}
