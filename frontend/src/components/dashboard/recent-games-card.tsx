import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { BentoCard, LocalDateTime, StatusPill, ToastProvider } from "@/components/ui";
import type { RecentGameStats } from "@/lib/api/types";
import { localizeOpeningName } from "@/lib/opening-localization";
import { analysisStatusLabel, analysisStatusTone, gameResultLabel } from "@/lib/status";
import { AnalyzeGameButton } from "@/components/games/analyze-game-button";

const resultClasses = { win: "text-best", draw: "text-text-secondary", loss: "text-blunder" };

export function RecentGamesCard({ games }: { games: RecentGameStats[] }) {
  return <ToastProvider>
    <BentoCard as="section" className="h-full p-4 sm:p-5">
      <div className="flex items-center justify-between gap-4">
        <div><h2 className="text-lg font-semibold tracking-[-0.025em]">Последние партии</h2><p className="mt-1 text-xs text-text-secondary">Свежие результаты и статус анализа</p></div>
        <Link href="/games" className="focus-ring rounded-full px-3 py-2 text-sm font-semibold text-forest hover:bg-mint-surface">Все партии</Link>
      </div>
      {games.length === 0 ? (
        <div className="grid min-h-32 place-items-center text-center text-sm text-text-muted">Импортируйте первую партию Chess.com</div>
      ) : (
        <div className="mt-3 divide-y divide-[var(--border-subtle)]">
          {games.map((game) => (
            <div key={game.game_id} className="group grid gap-2 rounded-xl py-3 transition hover:bg-surface-muted sm:grid-cols-[minmax(0,1.4fr)_auto_auto] sm:items-center sm:px-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2"><span aria-hidden="true" className={game.user_color === "white" ? "size-3 rounded-sm border border-[var(--border-strong)] bg-white" : "size-3 rounded-sm bg-surface-dark"} /><Link href={`/games/${game.game_id}`} className="focus-ring truncate rounded-lg text-sm font-semibold hover:text-forest">vs {game.opponent_username}</Link></div>
                <p className="mt-1 truncate text-xs text-text-muted">{game.opening_code ? `${game.opening_code} · ` : ""}{localizeOpeningName(game.opening_name) ?? "Дебют не определён"} · <LocalDateTime value={game.played_at} dateOnly /></p>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <strong className={resultClasses[game.result]}>{gameResultLabel(game.result)}</strong>
                <span className="text-text-muted">{game.mistakes} ош. · {game.blunders} зев.</span>
              </div>
              <div className="flex items-center justify-between gap-2 sm:justify-end">
                <StatusPill tone={analysisStatusTone(game.analysis_status)} dot>{analysisStatusLabel(game.analysis_status)}</StatusPill>
                {game.analysis_status === "completed" ? <Link href={`/games/${game.game_id}`} aria-label="Открыть отчёт" className="focus-ring rounded-full p-2 text-forest"><ArrowUpRight aria-hidden="true" size={16} /></Link> : game.analysis_status === "analyzing" ? null : <AnalyzeGameButton gameId={game.game_id} status={game.analysis_status} />}
              </div>
            </div>
          ))}
        </div>
      )}
    </BentoCard>
  </ToastProvider>;
}
