import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AnalysisError, AnalysisPage } from "@/components/analysis";
import { AppShell } from "@/components/layout";
import { ApiError, fetchGameDetail, fetchGameMoves, fetchSystemStatus } from "@/lib/api";

export const metadata: Metadata = { title: "Chess AI Teacher — Анализ партии" };
export const dynamic = "force-dynamic";

async function loadAnalysis(gameId: number) {
  try {
    const [game, moves, systemStatus] = await Promise.all([
      fetchGameDetail(gameId),
      fetchGameMoves(gameId),
      fetchSystemStatus(),
    ]);
    return { status: "ready", game, moves: moves.items, systemStatus } as const;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return { status: "not-found" } as const;
    return { status: "unavailable" } as const;
  }
}

export default async function GameAnalysisRoute({ params }: { params: Promise<{ id: string }> }) {
  const rawId = (await params).id;
  const gameId = Number(rawId);
  if (!Number.isSafeInteger(gameId) || gameId < 1) notFound();

  const result = await loadAnalysis(gameId);
  if (result.status === "not-found") notFound();
  if (result.status === "unavailable") return <AppShell activeSection="games" engineStatus="unavailable"><AnalysisError /></AppShell>;
  return <AppShell activeSection="games" engineStatus={result.systemStatus.status}><AnalysisPage key={`${result.game.id}:${result.game.analysis_status}`} game={result.game} moves={result.moves} /></AppShell>;
}
