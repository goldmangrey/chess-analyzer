"use client";

import { useMemo } from "react";
import { Chessboard, type ChessboardOptions } from "react-chessboard";

import { BentoCard } from "@/components/ui";
import type { MoveAnalysis, UserColor } from "@/lib/api/types";

import { BoardNavigation } from "./board-navigation";
import { EvaluationBar } from "./evaluation-bar";

function highlightedSquares(move: MoveAnalysis | null): ChessboardOptions["squareStyles"] {
  if (!move) return {};
  const styles: NonNullable<ChessboardOptions["squareStyles"]> = {};
  for (const square of [move.played_move_uci.slice(0, 2), move.played_move_uci.slice(2, 4)]) {
    styles[square] = { background: "color-mix(in srgb, var(--warm-yellow) 62%, transparent)" };
  }
  if (move.best_move_uci && move.best_move_uci !== move.played_move_uci) {
    for (const square of [move.best_move_uci.slice(0, 2), move.best_move_uci.slice(2, 4)]) {
      if (!styles[square]) styles[square] = { boxShadow: "inset 0 0 0 4px var(--best)" };
    }
  }
  return styles;
}

export function ChessBoardPanel({ fen, orientation, move, evaluation, selectedPly, total, onSelect }: { fen: string; orientation: UserColor; move: MoveAnalysis | null; evaluation: number | null; selectedPly: number; total: number; onSelect: (ply: number) => void }) {
  const options = useMemo<ChessboardOptions>(() => ({
    id: "analysis-board",
    position: fen,
    boardOrientation: orientation,
    allowDragging: false,
    allowDrawingArrows: false,
    showAnimations: false,
    lightSquareStyle: { backgroundColor: "#e8e8dd" },
    darkSquareStyle: { backgroundColor: "#667760" },
    boardStyle: { borderRadius: "20px", overflow: "hidden", boxShadow: "var(--shadow-soft)" },
    squareStyles: highlightedSquares(move),
  }), [fen, move, orientation]);

  return (
    <BentoCard as="section" className="p-4 sm:p-6">
      <div role="img" className="flex aspect-[1.08/1] w-full gap-2 sm:gap-3" aria-label={`Шахматная доска, ориентация: ${orientation === "white" ? "белые" : "чёрные"}`}>
        <EvaluationBar evaluation={evaluation} />
        <div className="min-w-0 flex-1"><Chessboard options={options} /></div>
      </div>
      <div className="mt-5"><BoardNavigation selectedPly={selectedPly} total={total} onSelect={onSelect} /></div>
    </BentoCard>
  );
}
