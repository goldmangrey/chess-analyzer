import { apiFetch } from "./client";
import type { GamesListResponse } from "./types";

export function fetchGames(
  params: { limit?: number; offset?: number } = {},
  signal?: AbortSignal,
): Promise<GamesListResponse> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.size ? `?${search.toString()}` : "";
  return apiFetch<GamesListResponse>(`/api/games${query}`, { cache: "no-store", signal });
}
