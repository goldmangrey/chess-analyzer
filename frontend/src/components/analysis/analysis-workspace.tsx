"use client";

import { useEffect, useMemo } from "react";

import type { GameIntelligenceResponse, MoveAnalysis } from "@/lib/api/types";
import { fenForSelectedPly } from "@/lib/chess-position";
import { criticalMomentScrollBehavior, keyboardNavigationTarget, shouldIgnoreBoardShortcut } from "@/lib/review-board";

import { ChessBoardPanel } from "./chess-board-panel";
import { CriticalMomentsCard } from "./critical-moments-card";
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
  const selectedReview = useMemo(() => intelligence.move_reviews?.find((review) => review.ply === selectedPly) ?? null, [intelligence.move_reviews, selectedPly]);

  function selectPly(ply: number) { onSelect(Math.max(0, Math.min(total, ply))); }
  function selectCriticalPly(ply: number) {
    selectPly(ply);
    requestAnimationFrame(() => {
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      document.getElementById("review-board")?.scrollIntoView({ behavior: criticalMomentScrollBehavior(reducedMotion), block: "start" });
    });
  }

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
    <div className="mt-4 grid min-w-0 gap-4 sm:mt-5 xl:grid-cols-[minmax(0,7fr)_minmax(350px,5fr)] xl:items-stretch">
      <div className="min-w-0 xl:row-span-2"><ChessBoardPanel fen={fen} orientation={intelligence.game.user_color} move={selectedMove} evaluation={evaluation} selectedPly={selectedPly} total={total} onSelect={selectPly} /></div>
      <div className="min-w-0 xl:col-start-2 xl:row-start-1"><MoveReviewPanel key={selectedPly} move={selectedMove} error={selectedError} moment={selectedMoment} userColor={intelligence.game.user_color} commentary={selectedReview?.commentary ?? null} openingStatus={selectedReview?.opening_status ?? null} humanMetrics={selectedReview?.human_metrics ?? null} /></div>
      <div className="min-w-0 xl:col-start-1 xl:row-start-3"><CriticalMomentsCard intelligence={intelligence} selectedPly={selectedPly} onSelectPly={selectCriticalPly} /></div>
      <div className="min-w-0 xl:col-start-2 xl:row-start-3"><EvaluationTimeline moves={moves} criticalMoments={intelligence.critical_moments} userColor={intelligence.game.user_color} selectedPly={selectedPly} onSelect={selectPly} /></div>
      <div className="min-h-0 min-w-0 xl:col-start-2 xl:row-start-2"><MoveList moves={moves} criticalMoments={intelligence.critical_moments} selectedPly={selectedPly} onSelect={selectPly} /></div>
    </div>
  );
}
