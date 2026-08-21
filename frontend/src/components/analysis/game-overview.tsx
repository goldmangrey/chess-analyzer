import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { BentoCard, LocalDateTime, StatusPill } from "@/components/ui";
import type { GameIntelligenceResponse } from "@/lib/api/types";
import { canShowIntelligence, formatGameResult, formatOccurrenceCount, formatOpening, formatPlyMove, formatTimeControl, phaseErrorSummary, presentPhases, selectMainWeakness, selectPlayers, selectStrongestPhase, selectWeakestPhase } from "@/lib/game-overview";
import { formatAccuracy } from "@/lib/human-metrics";
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
  const lastNamedMove = formatPlyMove(intelligence.opening.last_named_match_ply, intelligence.opening.last_named_match_move_san);
  const deviationMove = formatPlyMove(intelligence.opening.first_deviation_ply, intelligence.opening.first_deviation_move_san);

  return (
    <BentoCard as="section" className="overflow-hidden p-0">
      <details>
        <summary className="focus-ring flex min-h-16 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 marker:content-none sm:px-5 [&::-webkit-details-marker]:hidden">
          <div className="min-w-0"><p className="text-xs font-semibold text-forest-light">Обзор партии</p><p className="mt-0.5 truncate text-lg font-semibold">vs {game.opponent}</p></div>
          <div className="flex min-w-0 flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs text-text-secondary"><span>{formatGameResult(game.result)}</span>{summary?.accuracy !== null && summary?.accuracy !== undefined ? <span className="technical-number font-semibold">Точность {formatAccuracy(summary.accuracy)}</span> : null}{opening ? <span className="max-w-64 truncate text-forest">{opening.family ?? opening.name}{opening.eco ? ` · ${opening.eco}` : ""}</span> : null}<span className="font-semibold text-forest">Подробнее</span></div>
        </summary>
        <div className="border-t border-[var(--border-subtle)]">
      <div className="p-4 sm:p-5">
        <Link href="/games" className="focus-ring inline-flex items-center gap-2 rounded-full text-sm font-semibold text-forest hover:text-forest-light"><ArrowLeft aria-hidden="true" size={16} />Все партии</Link>
        <div className="mt-3 flex min-w-0 flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1"><div className="flex min-w-0 flex-wrap items-center gap-2.5"><h1 className="min-w-0 break-words text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">vs {game.opponent}</h1><StatusPill tone={analysisStatusTone(analysis.status)} dot>{analysisStatusLabel(analysis.status)}</StatusPill></div><p className="mt-2 text-sm text-text-secondary">{formatGameResult(game.result)} · {game.user_color === "white" ? "Белые" : "Чёрные"}{timeControl ? <> · {timeControl}</> : null}</p>{game.played_at ? <p className="mt-1 text-xs text-text-muted"><LocalDateTime value={game.played_at} dateOnly /></p> : null}</div>
          {opening ? <div className="w-full min-w-0 rounded-2xl border border-[var(--border-subtle)] bg-surface-muted px-4 py-3 sm:w-auto sm:max-w-md sm:text-right">
            <p className="text-[11px] font-semibold text-text-muted">Дебют</p>
            <div className="mt-1 min-w-0">
              {opening.family ? <p className="break-words text-sm font-semibold leading-5 text-forest">{opening.family}</p> : <p className="break-words text-sm font-semibold leading-5 text-forest">{opening.name}</p>}
              {opening.variation ? <p className="mt-0.5 break-words text-xs font-semibold text-text-secondary">{opening.variation}</p> : null}
              {opening.subvariation ? <p className="mt-0.5 break-words text-xs text-text-muted">{opening.subvariation}</p> : null}
              {opening.eco ? <p className="technical-number mt-1 text-xs text-text-muted">{opening.eco}</p> : null}
            </div>
            {(lastNamedMove || deviationMove || intelligence.opening.transposition_reentry) ? <dl className="mt-3 space-y-1.5 border-t border-[var(--border-subtle)] pt-3 text-xs text-text-muted">
              {lastNamedMove ? <div className="flex min-w-0 flex-wrap justify-between gap-x-3 gap-y-0.5"><dt>Последняя распознанная позиция</dt><dd className="technical-number font-semibold text-text-secondary">{lastNamedMove}</dd></div> : null}
              {deviationMove ? <div className="flex min-w-0 flex-wrap justify-between gap-x-3 gap-y-0.5"><dt>Первое отклонение от базы</dt><dd className="technical-number font-semibold text-text-secondary">{deviationMove}</dd></div> : null}
              {intelligence.opening.transposition_reentry ? <div className="text-left sm:text-right">Позже партия снова пришла к известной дебютной позиции.</div> : null}
            </dl> : null}
          </div> : null}
        </div>

        <dl className="mt-3 grid gap-x-6 gap-y-2 border-t border-[var(--border-subtle)] pt-3 text-sm sm:grid-cols-2">
          <div className="flex min-w-0 justify-between gap-3"><dt className="shrink-0 text-text-muted">Вы</dt><dd className="min-w-0 truncate font-semibold">{players.user}{typeof players.userRating === "number" ? <span className="technical-number ml-2 text-text-muted">{players.userRating}</span> : null}</dd></div>
          <div className="flex min-w-0 justify-between gap-3"><dt className="shrink-0 text-text-muted">Соперник</dt><dd className="min-w-0 truncate font-semibold">{players.opponent}{typeof players.opponentRating === "number" ? <span className="technical-number ml-2 text-text-muted">{players.opponentRating}</span> : null}</dd></div>
        </dl>
      </div>

      {showIntelligence && summary ? <div className="border-y border-[var(--border-subtle)] bg-surface-muted/70 px-4 py-3 sm:px-5"><dl className="grid grid-cols-2 gap-3 sm:grid-cols-4"><div><dt className="text-xs text-text-muted">Точность</dt><dd className="technical-number mt-1 text-xl font-semibold">{formatAccuracy(summary.accuracy)}</dd></div><div><dt className="text-xs text-text-muted">Неточности</dt><dd className="technical-number mt-1 text-xl font-semibold text-inaccuracy-text">{summary.inaccuracies}</dd></div><div><dt className="text-xs text-text-muted">Ошибки</dt><dd className="technical-number mt-1 text-xl font-semibold text-mistake">{summary.mistakes}</dd></div><div><dt className="text-xs text-text-muted">Зевки</dt><dd className="technical-number mt-1 text-xl font-semibold text-blunder-text">{summary.blunders}</dd></div></dl></div> : null}

      {phases.length || weakness ? <div className="p-4 sm:p-5">{phases.length ? <><h2 className="text-sm font-semibold">Игра по фазам</h2><div className="mt-2 grid gap-2 sm:grid-cols-3">{phases.map(({ key, label, metrics }) => <article key={key} className="rounded-xl bg-surface-muted p-3"><div className="flex items-baseline justify-between gap-2"><h3 className="text-sm font-semibold">{label}</h3><p className="technical-number text-base font-semibold">{formatAccuracy(metrics.accuracy)}</p></div><p className="mt-1 text-xs text-text-muted">{metrics.user_moves} ходов{phaseErrorSummary(metrics) ? <> · {phaseErrorSummary(metrics)}</> : null}</p></article>)}</div></> : null}
        {(strongest && weakest) || weakness ? <div className={`${phases.length ? "mt-3 border-t border-[var(--border-subtle)] pt-3" : ""} grid gap-2 sm:grid-cols-3`}>{strongest ? <div><p className="text-xs text-text-muted">Лучшая фаза</p><p className="mt-0.5 text-sm font-semibold">{strongest.label} · {formatAccuracy(strongest.metrics.accuracy)}</p></div> : null}{weakest ? <div><p className="text-xs text-text-muted">Слабая фаза</p><p className="mt-0.5 text-sm font-semibold">{weakest.label} · {formatAccuracy(weakest.metrics.accuracy)}</p></div> : null}{weakness ? <div><p className="text-xs text-text-muted">Главная проблема</p><p className="mt-0.5 text-sm font-semibold">{weakness.label} · {formatOccurrenceCount(weakness.count)}</p></div> : null}</div> : null}
      </div> : null}
        </div>
      </details>
    </BentoCard>
  );
}
