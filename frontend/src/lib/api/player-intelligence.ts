import { apiFetch } from "./client";
import type { PlayerIntelligenceResponse } from "./types";

export function fetchPlayerIntelligence(window = 30, signal?: AbortSignal): Promise<PlayerIntelligenceResponse> {
  return apiFetch<PlayerIntelligenceResponse>(`/api/player/intelligence?window=${window}`, { cache: "no-store", signal });
}
