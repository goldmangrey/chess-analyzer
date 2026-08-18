import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { BentoCard, LocalDateTime, StatusPill } from "@/components/ui";
import type { GameIntelligenceResponse } from "@/lib/api/types";
import { canShowIntelligence, formatAcpl, formatGameResult, formatOccurrenceCount, formatOpening, formatTimeControl, phaseErrorSummary, presentPhases, selectMainWeakness, selectPlayers, selectStrongestPhase, selectWeakestPhase } from "@/lib/game-overview";
import { analysisStatusLabel, analysisStatusTone } from "@/lib/status";

export function GameOverview({ intelligence }: { intelligence: GameIntelligenceResponse }) {
  const { game, analysis, summary } = intelligence;
  const opening = formatOpening(intelligence.opening);
  const showIntelligence = canShowIntelligence(analysis);
  const phases = showIntelligence ? presentPhases(intelligence.phases) : [];
  const strongest = showIntelligence ? selectStrongestPhase(intelligence.phases) : null;
  const weakest = showIntelligence ? selectWeakestPhase(intelligence.phases) : null;
  const weakness = showIntelligence ? selectMainWeakness(intelligence.error_breakdown) : null;
  const players = selectPlayers(game);
  const timeControl = formatTimeControl(game.time_control);

  return (
    <BentoCard as="section" className="overflow-hidden p-0">
      <div className="p-6 sm:p-8">
        <Link href="/games" className="focus-ring inline-flex items-center gap-2 rounded-full text-sm font-semibold text-forest hover:text-forest-light"><ArrowLeft aria-hidden="true" size={16} />Все партии</Link>
        <div className="mt-6 flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0"><div className="flex flex-wrap items-center gap-3"><h1 className="break-words text-3xl font-semibold tracking-[-0.05em] sm:text-5xl">vs {game.opponent}</h1><StatusPill tone={analysisStatusTone(analysis.status)} dot>{analysisStatusLabel(analysis.status)}</StatusPill></div><p className="mt-4 text-sm text-text-secondary">{formatGameResult(game.result)} · {game.user_color === "white" ? "Белые" : "Чёрные"}{timeControl ? <> · {timeControl}</> : null}</p>{game.played_at ? <p className="mt-2 text-xs text-text-muted"><LocalDateTime value={game.played_at} dateOnly /></p> : null}</div>
          {opening ? <div className="max-w-md rounded-2xl border border-[var(--border-subtle)] bg-surface-muted px-4 py-3 sm:text-right"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">Дебют</p><p className="mt-1 font-semibold leading-6 text-forest">{opening.name}</p>{opening.eco ? <p className="technical-number mt-1 text-xs text-text-muted">{opening.eco}</p> : null}</div> : null}
        </div>

        <dl className="mt-6 grid gap-x-6 gap-y-3 border-t border-[var(--border-subtle)] pt-5 text-sm sm:grid-cols-2">
          <div className="flex min-w-0 justify-between gap-3"><dt className="text-text-muted">Вы</dt><dd className="truncate font-semibold">{players.user}{typeof players.userRating === "number" ? <span className="technical-number ml-2 text-text-muted">{players.userRating}</span> : null}</dd></div>
          <div className="flex min-w-0 justify-between gap-3"><dt className="text-text-muted">Соперник</dt><dd className="truncate font-semibold">{players.opponent}{typeof players.opponentRating === "number" ? <span className="technical-number ml-2 text-text-muted">{players.opponentRating}</span> : null}</dd></div>
        </dl>
      </div>

      {showIntelligence && summary ? <div className="border-y border-[var(--border-subtle)] bg-surface-muted/70 px-6 py-5 sm:px-8"><dl className="grid grid-cols-2 gap-5 sm:grid-cols-4"><div><dt className="text-xs text-text-muted">ACPL</dt><dd className="technical-number mt-1 text-2xl font-semibold">{formatAcpl(summary.average_cp_loss)}</dd></div><div><dt className="text-xs text-text-muted">Неточности</dt><dd className="technical-number mt-1 text-2xl font-semibold text-inaccuracy-text">{summary.inaccuracies}</dd></div><div><dt className="text-xs text-text-muted">Ошибки</dt><dd className="technical-number mt-1 text-2xl font-semibold text-mistake">{summary.mistakes}</dd></div><div><dt className="text-xs text-text-muted">Зевки</dt><dd className="technical-number mt-1 text-2xl font-semibold text-blunder-text">{summary.blunders}</dd></div></dl></div> : null}

      {phases.length || weakness ? <div className="p-6 sm:p-8">{phases.length ? <><h2 className="text-sm font-semibold">Игра по фазам</h2><div className="mt-4 grid gap-3 md:grid-cols-3">{phases.map(({ key, label, metrics }) => <article key={key} className="rounded-2xl bg-surface-muted p-4"><h3 className="text-sm font-semibold">{label}</h3><p className="technical-number mt-2 text-xl font-semibold">{formatAcpl(metrics.average_cp_loss)} <span className="text-xs font-normal text-text-muted">ACPL</span></p><p className="mt-1 text-xs text-text-muted">{metrics.user_moves} ходов{phaseErrorSummary(metrics) ? <> · {phaseErrorSummary(metrics)}</> : null}</p></article>)}</div></> : null}
        {(strongest && weakest) || weakness ? <div className={`${phases.length ? "mt-5 border-t border-[var(--border-subtle)] pt-5" : ""} grid gap-3 sm:grid-cols-2 lg:grid-cols-3`}>{strongest ? <div><p className="text-xs text-text-muted">Лучшая фаза</p><p className="mt-1 text-sm font-semibold">{strongest.label} · {formatAcpl(strongest.metrics.average_cp_loss)} ACPL</p></div> : null}{weakest ? <div><p className="text-xs text-text-muted">Слабая фаза</p><p className="mt-1 text-sm font-semibold">{weakest.label} · {formatAcpl(weakest.metrics.average_cp_loss)} ACPL</p></div> : null}{weakness ? <div><p className="text-xs text-text-muted">Главная проблема</p><p className="mt-1 text-sm font-semibold">{weakness.label} · {formatOccurrenceCount(weakness.count)}</p></div> : null}</div> : null}
      </div> : null}
    </BentoCard>
  );
}
