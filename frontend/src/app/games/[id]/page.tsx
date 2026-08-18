import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AnalysisError, AnalysisPage } from "@/components/analysis";
import { AppShell } from "@/components/layout";
import { ApiError, fetchGameIntelligence, fetchGameMoves, fetchSystemStatus } from "@/lib/api";

export const metadata: Metadata = { title: "Chess AI Teacher — Анализ партии" };
export const dynamic = "force-dynamic";

async function loadAnalysis(gameId: number) {
  try {
    const [intelligence, moves, systemStatus] = await Promise.all([
      fetchGameIntelligence(gameId),
      fetchGameMoves(gameId),
      fetchSystemStatus(),
    ]);
    return { status: "ready", intelligence, moves: moves.items, systemStatus } as const;
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
  return <AppShell activeSection="games" engineStatus={result.systemStatus.status}><AnalysisPage key={`${result.intelligence.game.id}:${result.intelligence.analysis.status}`} intelligence={result.intelligence} moves={result.moves} /></AppShell>;
}
