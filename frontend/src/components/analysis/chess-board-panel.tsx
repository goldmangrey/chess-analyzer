"use client";

import { useMemo } from "react";
import { Chessboard, defaultPieces, type ChessboardOptions, type PieceRenderObject } from "react-chessboard";

import { BentoCard } from "@/components/ui";
import type { CriticalMoment, ErrorClassification, MoveAnalysis, UserColor } from "@/lib/api/types";
import { buildReviewBoardModel, moveReviewPresentation } from "@/lib/review-board";

import { BoardNavigation } from "./board-navigation";
import { EvaluationBar } from "./evaluation-bar";

function highlightedSquares(move: MoveAnalysis | null, model: ReturnType<typeof buildReviewBoardModel>): NonNullable<ChessboardOptions["squareStyles"]> {
  if (!move || !model.played) return {};
  const styles: NonNullable<ChessboardOptions["squareStyles"]> = {};
  styles[model.played.from] = { background: "var(--board-last-move)" };
  const severity = move.classification === "blunder" ? "var(--board-blunder)" : move.classification === "mistake" ? "var(--board-mistake)" : "var(--board-last-move)";
  styles[model.played.to] = {
    background: `radial-gradient(circle at 50% 50%, transparent 45%, ${severity} 100%), var(--board-last-move)`,
  };
  if (model.best) {
    for (const square of [model.best.from, model.best.to]) {
      if (!styles[square]) styles[square] = { boxShadow: "inset 0 0 0 clamp(2px, 0.5vw, 4px) var(--board-best-move)" };
    }
  }
  return styles;
}

const badgeClasses = {
  best: "bg-best text-white",
  normal: "bg-forest text-white",
  inaccuracy: "bg-inaccuracy text-text-primary",
  mistake: "bg-mistake text-text-primary",
  blunder: "bg-blunder text-white",
} as const;

const reviewPieces = Object.fromEntries(
  Object.entries(defaultPieces).map(([pieceType, Piece]) => [
    pieceType,
    (props) => <Piece {...props} fill={pieceType.startsWith("w") ? "var(--board-piece-white)" : "var(--board-piece-black)"} />,
  ]),
) as PieceRenderObject;

export function ChessBoardPanel({ fen, orientation, move, error, moment, evaluation, selectedPly, total, onSelect }: { fen: string; orientation: UserColor; move: MoveAnalysis | null; error: ErrorClassification | null; moment: CriticalMoment | null; evaluation: number | null; selectedPly: number; total: number; onSelect: (ply: number) => void }) {
  const model = useMemo(() => buildReviewBoardModel(move, orientation), [move, orientation]);
  const review = useMemo(() => moveReviewPresentation(move, error, moment), [error, moment, move]);
  const squareStyles = useMemo(() => highlightedSquares(move, model), [model, move]);
  const options = useMemo<ChessboardOptions>(() => ({
    id: "analysis-board",
    position: fen,
    pieces: reviewPieces,
    boardOrientation: orientation,
    allowDragging: false,
    allowDrawingArrows: false,
    showAnimations: false,
    arrows: model.arrows,
    arrowOptions: { color: "var(--board-arrow-played)", secondaryColor: "var(--board-arrow-best)", tertiaryColor: "var(--board-blunder)", arrowLengthReducerDenominator: 5, sameTargetArrowLengthReducerDenominator: 3, arrowWidthDenominator: 7, activeArrowWidthMultiplier: 0.9, opacity: 0.76, activeOpacity: 0.76, arrowStartOffset: 0.12 },
    lightSquareStyle: { backgroundColor: "var(--board-light)" },
    darkSquareStyle: { backgroundColor: "var(--board-dark)" },
    lightSquareNotationStyle: { color: "var(--board-coordinate-light)", fontSize: "clamp(8px, 1.5vw, 12px)", fontWeight: 700 },
    darkSquareNotationStyle: { color: "var(--board-coordinate-dark)", fontSize: "clamp(8px, 1.5vw, 12px)", fontWeight: 700 },
    boardStyle: { borderRadius: "22px", overflow: "hidden", boxShadow: "0 18px 42px rgba(25, 64, 42, 0.18), 0 2px 8px rgba(15, 35, 23, 0.12)", border: "1px solid rgba(24, 92, 59, 0.2)" },
    squareStyles,
    squareRenderer: ({ square, children }) => <div style={{ width: "100%", height: "100%", position: "relative", ...squareStyles[square] }}>{children}{model.badge?.square === square ? <span aria-label={`Оценка хода: ${model.badge.label}`} title={model.badge.label} className={`absolute right-[4%] top-[4%] z-30 grid size-[clamp(18px,4.2vw,30px)] place-items-center rounded-full border border-white/80 text-[clamp(9px,1.8vw,13px)] font-black leading-none shadow-md ${badgeClasses[model.badge.tone]}`}>{model.badge.symbol}</span> : null}</div>,
  }), [fen, model, orientation, squareStyles]);

  return (
    <BentoCard as="section" id="review-board" className="scroll-mt-6 p-4 sm:p-6 lg:p-7">
      {review ? <div className="mb-4 rounded-2xl border border-[var(--border-subtle)] bg-surface-muted p-4" aria-live="polite"><div className="flex flex-wrap items-center gap-x-3 gap-y-1"><strong className="text-lg">{review.moveLabel}</strong><span className="rounded-full bg-surface px-2.5 py-1 text-xs font-bold text-forest shadow-sm">{review.label}</span></div>{review.explanation ? <p className="mt-2 text-sm leading-6 text-text-secondary">{review.explanation}</p> : null}<p className="mt-2 text-xs text-text-muted">Сыграно: <strong>{review.playedSan}</strong>{review.bestSan ? <> · Лучше: <strong className="text-best">{review.bestSan}</strong></> : null}</p></div> : null}
      <div role="img" className="review-board flex w-full items-stretch gap-2 sm:gap-3" aria-label={`Шахматная доска после выбранного хода, ориентация: ${orientation === "white" ? "белые" : "чёрные"}`}>
        <EvaluationBar evaluation={evaluation} />
        <div className="aspect-square min-w-0 flex-1"><Chessboard options={options} /></div>
      </div>
      <div className="mt-5"><BoardNavigation selectedPly={selectedPly} total={total} onSelect={onSelect} /></div>
    </BentoCard>
  );
}
