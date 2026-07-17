import { apiFetch } from "./client";
import type { AnalyzeGameResponse, GameDetailResponse, GameMovesResponse, GamesListResponse, GamesQuery } from "./types";

export function fetchGames(
  params: GamesQuery = {},
  signal?: AbortSignal,
): Promise<GamesListResponse> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  if (params.result) search.set("result", params.result);
  if (params.opening?.trim()) search.set("opening", params.opening.trim());
  if (params.analysisStatus) search.set("analysis_status", params.analysisStatus);
  if (params.sort) search.set("sort", params.sort);
  const query = search.size ? `?${search.toString()}` : "";
  return apiFetch<GamesListResponse>(`/api/games${query}`, { cache: "no-store", signal });
}

export function queueGameAnalysis(gameId: number, signal?: AbortSignal): Promise<AnalyzeGameResponse> {
  return apiFetch<AnalyzeGameResponse>(`/api/games/${gameId}/analyze`, { method: "POST", signal });
}

export function fetchGameDetail(gameId: number, signal?: AbortSignal): Promise<GameDetailResponse> {
  return apiFetch<GameDetailResponse>(`/api/games/${gameId}`, { cache: "no-store", signal });
}

export function fetchGameMoves(gameId: number, signal?: AbortSignal): Promise<GameMovesResponse> {
  return apiFetch<GameMovesResponse>(`/api/games/${gameId}/moves`, { cache: "no-store", signal });
}
