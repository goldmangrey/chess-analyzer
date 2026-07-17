import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { GamesError, GamesPage } from "@/components/games";
import { AppShell } from "@/components/layout";
import { fetchGames, fetchSystemStatus } from "@/lib/api";
import { gamesStateToSearchParams, parseGamesUrlState, toGamesApiQuery } from "@/lib/games-query";

export const metadata: Metadata = { title: "Chess AI Teacher — Партии" };
export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

async function loadGames(searchParams: SearchParams) {
  const state = parseGamesUrlState(await searchParams);
  try {
    const [data, systemStatus] = await Promise.all([
      fetchGames(toGamesApiQuery(state)),
      fetchSystemStatus(),
    ]);
    return { available: true, state, data, systemStatus } as const;
  } catch {
    return { available: false, state, data: null, systemStatus: null } as const;
  }
}

export default async function GamesRoute({ searchParams }: { searchParams: SearchParams }) {
  const result = await loadGames(searchParams);
  if (!result.available) {
    return <AppShell activeSection="games" engineStatus="unavailable"><GamesError /></AppShell>;
  }

  const totalPages = Math.max(1, Math.ceil(result.data.total / result.data.limit));
  if (result.data.total > 0 && result.state.page > totalPages) {
    const params = gamesStateToSearchParams({ ...result.state, page: totalPages });
    redirect(params.size ? `/games?${params}` : "/games");
  }

  return <AppShell activeSection="games" engineStatus={result.systemStatus.status}><GamesPage data={result.data} state={result.state} /></AppShell>;
}
