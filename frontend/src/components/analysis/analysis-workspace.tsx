"use client";

import { useEffect, useMemo } from "react";

import type { GameIntelligenceResponse, MoveAnalysis } from "@/lib/api/types";
import { fenForSelectedPly } from "@/lib/chess-position";
import { keyboardNavigationTarget, shouldIgnoreBoardShortcut } from "@/lib/review-board";

import { ChessBoardPanel } from "./chess-board-panel";
import { EvaluationTimeline } from "./evaluation-timeline";
import { MoveReviewPanel } from "./move-review-panel";
import { MoveList } from "./move-list";

export function AnalysisWorkspace({ intelligence, moves, selectedPly, onSelect }: { intelligence: GameIntelligenceResponse; moves: MoveAnalysis[]; selectedPly: number; onSelect: (ply: number) => void }) {
  const total = moves.length;
  const selectedMove = useMemo(() => selectedPly > 0 ? moves.find((move) => move.ply === selectedPly) ?? null : null, [moves, selectedPly]);
  const fen = useMemo(() => fenForSelectedPly(moves, selectedPly), [moves, selectedPly]);
  const evaluation = selectedMove?.evaluation_after_cp ?? (selectedPly === 0 ? moves[0]?.evaluation_before_cp ?? null : null);
  const selectedError = useMemo(() => intelligence.errors.find((error) => error.ply === selectedPly) ?? null, [intelligence.errors, selectedPly]);
  const selectedMoment = useMemo(() => intelligence.critical_moments.find((moment) => moment.ply === selectedPly) ?? null, [intelligence.critical_moments, selectedPly]);

  function selectPly(ply: number) { onSelect(Math.max(0, Math.min(total, ply))); }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (shouldIgnoreBoardShortcut(target)) return;
      const next = keyboardNavigationTarget(event.key, selectedPly, total);
      if (next === null) return;
      onSelect(next);
      event.preventDefault();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onSelect, selectedPly, total]);

  return (
    <div className="mt-6 space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,7fr)_minmax(340px,5fr)] xl:items-start">
        <ChessBoardPanel fen={fen} orientation={intelligence.game.user_color} move={selectedMove} error={selectedError} moment={selectedMoment} evaluation={evaluation} selectedPly={selectedPly} total={total} onSelect={selectPly} />
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-1"><MoveList moves={moves} criticalMoments={intelligence.critical_moments} selectedPly={selectedPly} onSelect={selectPly} /><MoveReviewPanel key={selectedPly} move={selectedMove} error={selectedError} moment={selectedMoment} userColor={intelligence.game.user_color} /></div>
      </div>
      <EvaluationTimeline moves={moves} criticalMoments={intelligence.critical_moments} userColor={intelligence.game.user_color} selectedPly={selectedPly} onSelect={selectPly} />
    </div>
  );
}
