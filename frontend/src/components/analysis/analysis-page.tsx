import { ToastProvider } from "@/components/ui";
import { AnalyzeGameButton } from "@/components/games/analyze-game-button";
import type { GameDetailResponse, MoveAnalysis } from "@/lib/api/types";

import { AnalysisEmptyState } from "./analysis-empty-state";
import { AnalysisRefreshButton } from "./analysis-refresh-button";
import { AnalysisWorkspace } from "./analysis-workspace";
import { GameHeaderCard } from "./game-header-card";

export function AnalysisPage({ game, moves }: { game: GameDetailResponse; moves: MoveAnalysis[] }) {
  const hasUsableAnalysis = game.analysis_status === "completed" && moves.length > 0;
  return (
    <ToastProvider>
      <GameHeaderCard game={game} />
      <div className="mt-3 flex flex-wrap justify-end gap-2"><AnalysisRefreshButton />{hasUsableAnalysis ? <AnalyzeGameButton gameId={game.id} status="completed" /> : null}</div>
      {hasUsableAnalysis ? <AnalysisWorkspace game={game} moves={moves} /> : <AnalysisEmptyState gameId={game.id} status={game.analysis_status} />}
    </ToastProvider>
  );
}
