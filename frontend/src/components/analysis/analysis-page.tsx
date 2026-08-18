"use client";

import { useCallback, useState } from "react";

import { ToastProvider } from "@/components/ui";
import { AnalyzeGameButton } from "@/components/games/analyze-game-button";
import { useBackgroundPolling } from "@/hooks/use-background-polling";
import { fetchGameIntelligence, fetchGameMoves } from "@/lib/api";
import type { GameIntelligenceResponse, MoveAnalysis } from "@/lib/api/types";
import { criticalMomentScrollBehavior } from "@/lib/review-board";
import { ANALYSIS_POLL_INTERVAL_MS, shouldPollAnalysis } from "@/lib/polling";

import { AnalysisEmptyState } from "./analysis-empty-state";
import { AnalysisRefreshButton } from "./analysis-refresh-button";
import { AnalysisWorkspace } from "./analysis-workspace";
import { CriticalMomentsCard } from "./critical-moments-card";
import { GameOverview } from "./game-overview";

export function AnalysisPage({ intelligence, moves }: { intelligence: GameIntelligenceResponse; moves: MoveAnalysis[] }) {
  const [liveIntelligence, setLiveIntelligence] = useState(intelligence);
  const [liveMoves, setLiveMoves] = useState(moves);
  const [selectedPly, setSelectedPly] = useState(0);

  const selectPly = useCallback((ply: number) => setSelectedPly(ply), []);
  const selectCriticalMoment = useCallback((ply: number) => {
    setSelectedPly(ply);
    requestAnimationFrame(() => {
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      document.getElementById("review-board")?.scrollIntoView({ behavior: criticalMomentScrollBehavior(reducedMotion), block: "start" });
    });
  }, []);

  const polling = shouldPollAnalysis(liveIntelligence.analysis.status);
  const { isRefreshing } = useBackgroundPolling({
    enabled: polling,
    intervalMs: ANALYSIS_POLL_INTERVAL_MS,
    fetcher: async (signal) => {
      const nextIntelligence = await fetchGameIntelligence(liveIntelligence.game.id, signal);
      const nextMoves = nextIntelligence.analysis.status === "completed"
        ? (await fetchGameMoves(liveIntelligence.game.id, signal)).items
        : liveMoves;
      return { intelligence: nextIntelligence, moves: nextMoves };
    },
    onSuccess: (next) => {
      setLiveIntelligence(next.intelligence);
      setLiveMoves(next.moves);
    },
  });

  const hasUsableAnalysis = liveIntelligence.analysis.intelligence_ready && liveMoves.length > 0;
  return (
    <ToastProvider>
      <GameOverview intelligence={liveIntelligence} />
      <div className="mt-3 flex min-h-9 flex-wrap items-center justify-end gap-2">
        {polling ? <span aria-live="polite" className="text-xs text-text-muted">{isRefreshing ? "Проверяем статус анализа…" : "Статус обновляется автоматически"}</span> : null}
        <AnalysisRefreshButton />
        {hasUsableAnalysis ? <AnalyzeGameButton gameId={liveIntelligence.game.id} status="completed" /> : null}
      </div>
      {hasUsableAnalysis ? <CriticalMomentsCard intelligence={liveIntelligence} selectedPly={selectedPly} onSelectPly={selectCriticalMoment} /> : null}
      {hasUsableAnalysis ? <AnalysisWorkspace intelligence={liveIntelligence} moves={liveMoves} selectedPly={selectedPly} onSelect={selectPly} /> : <AnalysisEmptyState gameId={liveIntelligence.game.id} status={liveIntelligence.analysis.status} />}
    </ToastProvider>
  );
}
