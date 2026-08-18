"use client";

import { useState } from "react";

import { ToastProvider } from "@/components/ui";
import { AnalyzeGameButton } from "@/components/games/analyze-game-button";
import { useBackgroundPolling } from "@/hooks/use-background-polling";
import { fetchGameDetail, fetchGameMoves } from "@/lib/api";
import type { GameDetailResponse, MoveAnalysis } from "@/lib/api/types";
import { ANALYSIS_POLL_INTERVAL_MS, shouldPollAnalysis } from "@/lib/polling";

import { AnalysisEmptyState } from "./analysis-empty-state";
import { AnalysisRefreshButton } from "./analysis-refresh-button";
import { AnalysisWorkspace } from "./analysis-workspace";
import { GameHeaderCard } from "./game-header-card";

export function AnalysisPage({ game, moves }: { game: GameDetailResponse; moves: MoveAnalysis[] }) {
  const [liveGame, setLiveGame] = useState(game);
  const [liveMoves, setLiveMoves] = useState(moves);

  const polling = shouldPollAnalysis(liveGame.analysis_status);
  const { isRefreshing } = useBackgroundPolling({
    enabled: polling,
    intervalMs: ANALYSIS_POLL_INTERVAL_MS,
    fetcher: async (signal) => {
      const nextGame = await fetchGameDetail(liveGame.id, signal);
      const nextMoves = nextGame.analysis_status === "completed"
        ? (await fetchGameMoves(liveGame.id, signal)).items
        : liveMoves;
      return { game: nextGame, moves: nextMoves };
    },
    onSuccess: (next) => {
      setLiveGame(next.game);
      setLiveMoves(next.moves);
    },
  });

  const hasUsableAnalysis = liveGame.analysis_status === "completed" && liveMoves.length > 0;
  return (
    <ToastProvider>
      <GameHeaderCard game={liveGame} />
      <div className="mt-3 flex min-h-9 flex-wrap items-center justify-end gap-2">
        {polling ? <span aria-live="polite" className="text-xs text-text-muted">{isRefreshing ? "Проверяем статус анализа…" : "Статус обновляется автоматически"}</span> : null}
        <AnalysisRefreshButton />
        {hasUsableAnalysis ? <AnalyzeGameButton gameId={liveGame.id} status="completed" /> : null}
      </div>
      {hasUsableAnalysis ? <AnalysisWorkspace game={liveGame} moves={liveMoves} /> : <AnalysisEmptyState gameId={liveGame.id} status={liveGame.analysis_status} />}
    </ToastProvider>
  );
}
