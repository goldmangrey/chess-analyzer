import { Chess } from "chess.js";

import type { MoveAnalysis } from "@/lib/api/types";

export const STANDARD_START_FEN = new Chess().fen();

export function safeFen(fen: string | null | undefined): string {
  if (!fen) return STANDARD_START_FEN;
  try {
    return new Chess(fen).fen();
  } catch {
    return STANDARD_START_FEN;
  }
}

export function fenAfterMove(move: MoveAnalysis): string {
  try {
    const chess = new Chess(move.fen_before);
    const uci = move.played_move_uci;
    chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] });
    return chess.fen();
  } catch {
    return safeFen(move.fen_before);
  }
}

export function fenForSelectedPly(moves: MoveAnalysis[], selectedPly: number): string {
  if (selectedPly <= 0) return safeFen(moves[0]?.fen_before);
  const move = moves.find((item) => item.ply === selectedPly);
  return move ? fenAfterMove(move) : safeFen(moves[0]?.fen_before);
}

/** Smoothly maps white-perspective centipawns to a useful 5–95% visual range. */
export function evaluationWhitePercent(evaluationCp: number | null): number {
  if (evaluationCp === null || !Number.isFinite(evaluationCp)) return 50;
  return Math.max(5, Math.min(95, 50 + 45 * Math.tanh(evaluationCp / 500)));
}
