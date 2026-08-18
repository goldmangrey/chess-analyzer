"use client";

import { useState } from "react";

import { BentoCard } from "@/components/ui";
import type { CriticalMoment, ErrorClassification, MoveAnalysis, UserColor } from "@/lib/api/types";
import { fullMoveReviewPresentation } from "@/lib/review-board";

const toneClasses = {
  best: "bg-best text-white",
  normal: "bg-forest text-white",
  inaccuracy: "bg-inaccuracy text-text-primary",
  mistake: "bg-mistake text-text-primary",
  blunder: "bg-blunder text-white",
} as const;

export function MoveReviewPanel({ move, error, moment, userColor }: { move: MoveAnalysis | null; error: ErrorClassification | null; moment: CriticalMoment | null; userColor: UserColor }) {
  const [showFullVariation, setShowFullVariation] = useState(false);
  const review = fullMoveReviewPresentation(move, error, moment, userColor);

  if (!review) {
    return <BentoCard as="section" tone="muted" className="p-6"><h2 className="text-xl font-semibold tracking-[-0.035em]">Разбор хода</h2><p className="mt-3 text-sm leading-6 text-text-secondary">Выберите ход в списке или используйте навигацию.</p></BentoCard>;
  }

  const variation = review.principalVariation;
  return (
    <BentoCard as="section" className="overflow-hidden p-0" aria-live="polite">
      <div className="border-b border-[var(--border-subtle)] bg-[linear-gradient(135deg,var(--surface-muted),var(--surface))] p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-forest-light">{move?.is_user_move ? "Ваш ход" : "Ход соперника"}</p><h2 className="technical-number mt-1 text-3xl font-semibold tracking-[-0.045em]">{review.moveLabel}</h2></div>
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-bold shadow-sm ${toneClasses[review.quality.tone]}`}><span aria-hidden="true">{review.quality.symbol}</span>{review.label}</span>
        </div>
        <p className="mt-5 text-base font-medium leading-7 text-text-primary">{review.explanation}</p>
        {review.phaseLabel ? <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">{review.phaseLabel}</p> : null}
      </div>

      <div className="space-y-5 p-5 sm:p-6">
        <div className={`grid gap-3 ${review.bestSan && !review.isBest ? "sm:grid-cols-2" : ""}`}>
          <div className="rounded-2xl border border-[var(--border-subtle)] bg-surface-muted p-4"><p className="text-xs font-semibold text-text-muted">Сыграно</p><p className="technical-number mt-2 text-xl font-semibold">{review.playedSan}</p>{review.isBest ? <p className="mt-2 text-xs font-bold text-best">Лучший ход</p> : null}</div>
          {review.bestSan && !review.isBest ? <div className="rounded-2xl border border-best/30 bg-best/5 p-4"><p className="text-xs font-semibold text-text-muted">Лучше</p><p className="technical-number mt-2 text-xl font-semibold text-best">{review.bestSan}</p></div> : null}
        </div>

        {(review.evaluationBefore !== null || review.evaluationAfter !== null) ? <div><p className="text-xs font-semibold text-text-muted">Оценка с вашей стороны</p><div className="mt-2 flex flex-wrap items-center gap-3" aria-label={`До хода ${review.evaluationBefore ?? "нет данных"}, после хода ${review.evaluationAfter ?? "нет данных"}`}><span className="technical-number text-lg font-semibold">{review.evaluationBefore ?? "—"}</span><span aria-hidden="true" className="text-text-muted">→</span><span className="technical-number text-lg font-semibold">{review.evaluationAfter ?? "—"}</span></div></div> : null}

        {review.centipawnLoss !== null ? <div className="flex items-center justify-between gap-4 border-t border-[var(--border-subtle)] pt-4"><span className="text-sm text-text-secondary">Потеря оценки (CP Loss)</span><strong className="technical-number text-sm">{review.centipawnLoss}</strong></div> : null}

        {variation ? <div className="border-t border-[var(--border-subtle)] pt-4"><div className="flex items-center justify-between gap-3"><p className="text-sm font-semibold">Вариант движка</p>{variation.truncated ? <button type="button" aria-expanded={showFullVariation} onClick={() => setShowFullVariation((value) => !value)} className="rounded-lg px-2 py-1 text-xs font-semibold text-forest hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest">{showFullVariation ? "Скрыть полный вариант" : "Показать весь вариант"}</button> : null}</div><p className="technical-number mt-3 break-words text-sm leading-7 text-text-secondary">{showFullVariation ? variation.full : variation.preview}</p></div> : null}
      </div>
    </BentoCard>
  );
}
