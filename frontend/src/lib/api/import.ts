import { apiFetch } from "./client";
import type { ChessComImportRequest, ChessComImportResponse } from "./types";

export function importChessComGames(
  request: ChessComImportRequest,
  signal?: AbortSignal,
): Promise<ChessComImportResponse> {
  return apiFetch<ChessComImportResponse>("/api/import/chess-com", {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}
