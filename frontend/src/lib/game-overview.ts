import type { AnalysisStatus, ErrorType, GameIntelligenceResponse, GamePhase, GamePhaseStatistics, GameResult } from "./api/types";
import { taxonomyLabel } from "./chess-labels.ts";
import { localizeOpeningFamily, localizeOpeningName, localizeOpeningVariation } from "./opening-localization.ts";

const PHASE_ORDER: GamePhase[] = ["opening", "middlegame", "endgame"];
const TAXONOMY_PRIORITY: ErrorType[] = [
  "allowed_mate", "missed_mate", "hanging_piece", "missed_capture", "missed_check",
  "king_safety", "fork", "pin", "skewer", "back_rank", "bad_exchange",
  "development", "pawn_structure", "tactical_pattern",
];

const PHASE_LABELS: Record<GamePhase, string> = {
  opening: "Дебют",
  middlegame: "Миттельшпиль",
  endgame: "Эндшпиль",
};

export type OverviewPhase = { key: GamePhase; label: string; metrics: GamePhaseStatistics };

export function formatGameResult(result: GameResult | string): string {
  return ({ win: "Победа", loss: "Поражение", draw: "Ничья" } as Record<string, string>)[result] ?? "Результат не указан";
}

export function formatTimeControl(value: string | null): string | null {
  if (!value) return null;
  const match = /^(\d+)(?:\+(\d+))?$/.exec(value.trim());
  if (!match) return value;
  const baseSeconds = Number(match[1]);
  const minutes = baseSeconds / 60;
  const base = Number.isInteger(minutes) ? String(minutes) : String(Number(minutes.toFixed(1)));
  return `${base}+${Number(match[2] ?? 0)}`;
}

type OpeningInput = Pick<GameIntelligenceResponse["opening"], "eco" | "name"> & Partial<GameIntelligenceResponse["opening"]>;

export function formatOpening(opening: OpeningInput): { name: string; eco: string | null; family: string | null; variation: string | null; subvariation: string | null } | null {
  if (opening.name) return {
    name: localizeOpeningName(opening.name) ?? opening.name,
    eco: opening.eco,
    family: localizeOpeningFamily(opening.family ?? opening.name.split(":", 1)[0]?.trim()) ?? null,
    variation: localizeOpeningVariation(opening.variation) ?? null,
    subvariation: localizeOpeningVariation(opening.subvariation) ?? null,
  };
  if (opening.eco) return { name: opening.eco, eco: null, family: null, variation: null, subvariation: null };
  return null;
}

export function formatPlyMove(ply: number | null | undefined, san: string | null | undefined): string | null {
  if (!ply || ply < 1 || !san) return null;
  const moveNumber = Math.ceil(ply / 2);
  return `${moveNumber}${ply % 2 === 0 ? "..." : "."}${san}`;
}

export function canShowIntelligence(analysis: { status: AnalysisStatus; intelligence_ready: boolean }): boolean {
  return analysis.status === "completed" && analysis.intelligence_ready;
}

export function selectPlayers(game: GameIntelligenceResponse["game"]) {
  return game.user_color === "white"
    ? { user: game.white_username, userRating: game.white_rating, opponent: game.black_username, opponentRating: game.black_rating }
    : { user: game.black_username, userRating: game.black_rating, opponent: game.white_username, opponentRating: game.white_rating };
}

export function formatOccurrenceCount(count: number): string {
  const modulo100 = count % 100;
  const modulo10 = count % 10;
  const word = modulo100 >= 11 && modulo100 <= 14 ? "раз" : modulo10 === 1 ? "раз" : modulo10 >= 2 && modulo10 <= 4 ? "раза" : "раз";
  return `${count} ${word}`;
}

export function presentPhases(phases: GameIntelligenceResponse["phases"]): OverviewPhase[] {
  return PHASE_ORDER.flatMap((key) => {
    const metrics = phases[key];
    return metrics && metrics.user_moves > 0 ? [{ key, label: PHASE_LABELS[key], metrics }] : [];
  });
}

function comparablePhases(phases: GameIntelligenceResponse["phases"]): OverviewPhase[] {
  return presentPhases(phases).filter(({ metrics }) => typeof metrics.accuracy === "number" && Number.isFinite(metrics.accuracy));
}

export function selectStrongestPhase(phases: GameIntelligenceResponse["phases"]): OverviewPhase | null {
  const valid = comparablePhases(phases);
  if (valid.length < 2) return null;
  return [...valid].sort((a, b) => (b.metrics.accuracy ?? 0) - (a.metrics.accuracy ?? 0) || PHASE_ORDER.indexOf(a.key) - PHASE_ORDER.indexOf(b.key))[0];
}

export function selectWeakestPhase(phases: GameIntelligenceResponse["phases"]): OverviewPhase | null {
  const valid = comparablePhases(phases);
  if (valid.length < 2) return null;
  return [...valid].sort((a, b) => (a.metrics.accuracy ?? 0) - (b.metrics.accuracy ?? 0) || PHASE_ORDER.indexOf(b.key) - PHASE_ORDER.indexOf(a.key))[0];
}

export function formatTaxonomyLabel(type: ErrorType): string {
  return taxonomyLabel(type);
}

export function selectMainWeakness(breakdown: GameIntelligenceResponse["error_breakdown"]): { type: ErrorType; label: string; count: number } | null {
  const candidates = TAXONOMY_PRIORITY.flatMap((type) => {
    const count = breakdown[type];
    return typeof count === "number" && Number.isFinite(count) && count > 0 ? [{ type, label: formatTaxonomyLabel(type), count }] : [];
  });
  return candidates.sort((a, b) => b.count - a.count || TAXONOMY_PRIORITY.indexOf(a.type) - TAXONOMY_PRIORITY.indexOf(b.type))[0] ?? null;
}

export function phaseErrorSummary(metrics: GamePhaseStatistics): string | null {
  const parts = [
    metrics.inaccuracies ? `${metrics.inaccuracies} неточн.` : null,
    metrics.mistakes ? `${metrics.mistakes} ошиб.` : null,
    metrics.blunders ? `${metrics.blunders} зевк.` : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : null;
}
