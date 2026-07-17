"use client";

import { useEffect, useMemo, useState } from "react";

import type { GameDetailResponse, MoveAnalysis } from "@/lib/api/types";
import { fenForSelectedPly } from "@/lib/chess-position";

import { ChessBoardPanel } from "./chess-board-panel";
import { EvaluationTimeline } from "./evaluation-timeline";
import { MoveDetailsCard } from "./move-details-card";
import { MoveList } from "./move-list";

export function AnalysisWorkspace({ game, moves }: { game: GameDetailResponse; moves: MoveAnalysis[] }) {
  const [selectedPly, setSelectedPly] = useState(0);
  const total = moves.length;
  const selectedMove = useMemo(() => selectedPly > 0 ? moves.find((move) => move.ply === selectedPly) ?? null : null, [moves, selectedPly]);
  const fen = useMemo(() => fenForSelectedPly(moves, selectedPly), [moves, selectedPly]);
  const evaluation = selectedMove?.evaluation_after_cp ?? (selectedPly === 0 ? moves[0]?.evaluation_before_cp ?? null : null);

  function selectPly(ply: number) { setSelectedPly(Math.max(0, Math.min(total, ply))); }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, textarea, select, button, [contenteditable='true']")) return;
      if (event.key === "ArrowLeft") setSelectedPly((current) => Math.max(0, current - 1));
      else if (event.key === "ArrowRight") setSelectedPly((current) => Math.min(total, current + 1));
      else if (event.key === "Home") setSelectedPly(0);
      else if (event.key === "End") setSelectedPly(total);
      else return;
      event.preventDefault();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [total]);

  return (
    <div className="mt-6 space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,7fr)_minmax(340px,5fr)] xl:items-start">
        <ChessBoardPanel fen={fen} orientation={game.user_color} move={selectedMove} evaluation={evaluation} selectedPly={selectedPly} total={total} onSelect={selectPly} />
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-1"><MoveList moves={moves} selectedPly={selectedPly} onSelect={selectPly} /><MoveDetailsCard move={selectedMove} /></div>
      </div>
      <EvaluationTimeline moves={moves} selectedPly={selectedPly} onSelect={selectPly} />
    </div>
  );
}
