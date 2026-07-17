import { apiFetch } from "./client";
import type { ChessComSyncRequest, ChessComSyncResponse } from "./types";

export function syncChessCom(request: ChessComSyncRequest = {}, signal?: AbortSignal): Promise<ChessComSyncResponse> {
  return apiFetch<ChessComSyncResponse>("/api/sync/chess-com", {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}
