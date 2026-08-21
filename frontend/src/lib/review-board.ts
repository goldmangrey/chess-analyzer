import { Chess } from "chess.js";

import type { CriticalMoment, CriticalMomentType, ErrorClassification, GamePhase, MoveAnalysis, MoveClassification, MoveCommentary, UserColor } from "./api/types";

export type ReviewArrow = { startSquare: string; endSquare: string; color: string };
export type MoveBadgeTone = "best" | MoveClassification;
export type MoveQualityPresentation = { symbol: string; label: string; tone: MoveBadgeTone };
export const TIMELINE_EVALUATION_LIMIT = 800;

export type EvaluationTimelinePoint = {
  ply: number;
  moveLabel: string;
  qualityLabel: string;
  qualitySymbol: string;
  evaluationBefore: number | null;
  evaluationAfter: number | null;
  evaluationBeforeLabel: string | null;
  evaluationAfterLabel: string | null;
  displayEvaluation: number | null;
  classification: MoveClassification | "initial";
  isCritical: boolean;
  criticalType: CriticalMomentType | null;
  isSelected: boolean;
};

export type ReviewBoardModel = {
  orientation: UserColor;
  played: { from: string; to: string } | null;
  best: { from: string; to: string } | null;
  arrows: ReviewArrow[];
  badge: { symbol: string; label: string; tone: MoveBadgeTone; square: string } | null;
};

const quality = {
  normal: { symbol: "✓", label: "Хороший" },
  inaccuracy: { symbol: "?!", label: "Неточность" },
  mistake: { symbol: "?", label: "Ошибка" },
  blunder: { symbol: "??", label: "Зевок" },
} as const;

const MATE_EVALUATION_THRESHOLD = 90_000;
const PV_PREVIEW_PLIES = 8;

const criticalTypeLabels: Record<CriticalMomentType, string> = { turning_point: "Переломный момент", blunder: "Ключевой зевок", missed_opportunity: "Упущенный шанс", missed_mate: "Упущенный мат", allowed_mate: "Допущенный мат", best_move: "Сильный момент" };
const criticalReasonLabels: Record<CriticalMomentType, string> = { turning_point: "Резкая смена оценки", blunder: "Существенная потеря оценки", missed_opportunity: "Преимущество упущено", missed_mate: "Форсированный мат упущен", allowed_mate: "Соперник получил форсированный мат", best_move: "Позиция заметно улучшена" };
const severityLabels: Record<MoveClassification, string> = { normal: "Лучший", inaccuracy: "Неточность", mistake: "Ошибка", blunder: "Зевок" };
const phaseLabels: Record<GamePhase, string> = { opening: "Дебют", middlegame: "Миттельшпиль", endgame: "Эндшпиль" };
const conciseTaxonomyLabels: Record<NonNullable<ErrorClassification["primary_type"]>, string> = { hanging_piece: "Потеря фигуры", missed_capture: "Упущенное взятие", missed_check: "Упущенный шах", missed_mate: "Упущенный мат", allowed_mate: "Допущенный мат", king_safety: "Безопасность короля", development: "Развитие фигур", bad_exchange: "Неудачный размен", pawn_structure: "Пешечная структура", tactical_pattern: "Тактическая ошибка", fork: "Вилка", pin: "Связка", skewer: "Линейный удар", back_rank: "Слабость последней горизонтали" };
const annotations: Record<MoveClassification, string> = { normal: "", inaccuracy: "?!", mistake: "?", blunder: "??" };

function legalUci(fen: string | null | undefined, uci: string | null | undefined) {
  if (!fen || !uci || !/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(uci)) return null;
  try {
    const chess = new Chess(fen);
    const move = chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] });
    return move ? { from: uci.slice(0, 2), to: uci.slice(2, 4) } : null;
  } catch {
    return null;
  }
}

export function moveQualityPresentation(move: MoveAnalysis): MoveQualityPresentation {
  const isBest = move.best_move_uci !== null && move.best_move_uci === move.played_move_uci;
  return isBest
    ? { symbol: "★", label: "Лучший", tone: "best" }
    : { ...quality[move.classification], tone: move.classification };
}

export function sanFromUci(fen: string | null | undefined, uci: string | null | undefined): string | null {
  const parsed = legalUci(fen, uci);
  if (!parsed || !fen) return null;
  try {
    const chess = new Chess(fen);
    return chess.move({ ...parsed, promotion: uci?.[4] })?.san ?? null;
  } catch {
    return null;
  }
}

export function evaluationToUserPov(value: number | null, userColor: UserColor): number | null {
  if (value === null || !Number.isFinite(value)) return null;
  return userColor === "white" ? value : -value;
}

export function formatReviewEvaluation(value: number | null, userColor: UserColor): string | null {
  const userValue = evaluationToUserPov(value, userColor);
  return formatUserPovEvaluation(userValue);
}

export function formatUserPovEvaluation(userValue: number | null): string | null {
  if (userValue === null) return null;
  if (Math.abs(userValue) >= MATE_EVALUATION_THRESHOLD) {
    return userValue > 0 ? "Мат за вас" : "Мат против вас";
  }
  const pawns = userValue / 100;
  return `${pawns >= 0 ? "+" : ""}${pawns.toFixed(2)}`;
}

export function principalVariationPresentation(value: string | null, fen?: string | null): { preview: string; full: string; truncated: boolean } | null {
  if (!value || !fen) return null;
  const tokens = value.trim().split(/\s+/).filter(Boolean);
  if (!tokens.length || tokens.some((token) => token.length > 24 || /[{}[\]<>]/.test(token))) return null;
  try {
    const chess = new Chess(fen);
    const sanTokens = tokens.map((token) => {
      const uci = /^[a-h][1-8][a-h][1-8][qrbn]?$/.test(token);
      const played = uci
        ? chess.move({ from: token.slice(0, 2), to: token.slice(2, 4), promotion: token[4] })
        : chess.move(token);
      if (!played) throw new Error("Illegal PV move");
      return played.san;
    });
    const full = sanTokens.join(" ");
    return { preview: sanTokens.slice(0, PV_PREVIEW_PLIES).join(" "), full, truncated: sanTokens.length > PV_PREVIEW_PLIES };
  } catch {
    return null;
  }
}

export function buildReviewBoardModel(move: MoveAnalysis | null, orientation: UserColor): ReviewBoardModel {
  if (!move) return { orientation, played: null, best: null, arrows: [], badge: null };
  const played = legalUci(move.fen_before, move.played_move_uci);
  const bestCandidate = played && move.best_move_uci !== move.played_move_uci
    ? legalUci(move.fen_before, move.best_move_uci)
    : null;
  const badgeQuality = moveQualityPresentation(move);
  return {
    orientation,
    played,
    best: bestCandidate,
    arrows: [
      ...(played ? [{ startSquare: played.from, endSquare: played.to, color: "var(--board-arrow-played)" }] : []),
      ...(bestCandidate ? [{ startSquare: bestCandidate.from, endSquare: bestCandidate.to, color: "var(--board-arrow-best)" }] : []),
    ],
    badge: played ? { ...badgeQuality, square: played.to } : null,
  };
}

export function moveReviewPresentation(
  move: MoveAnalysis | null,
  _error: ErrorClassification | null,
  _moment: CriticalMoment | null,
  commentary: MoveCommentary | null = null,
) {
  if (!move) return null;
  const isBest = move.best_move_uci !== null && move.best_move_uci === move.played_move_uci;
  const moveQuality = moveQualityPresentation(move);
  const explanation = commentary?.summary ?? "Комментарий к этому ходу недоступен.";
  const suffix = move.classification === "blunder" ? "??" : move.classification === "mistake" ? "?" : move.classification === "inaccuracy" ? "?!" : "";
  const playedSan = move.played_move_san ?? move.played_move_uci;
  return {
    moveLabel: `${move.move_number}${move.player_color === "black" ? "..." : "."}${playedSan}${suffix}`,
    label: moveQuality.label,
    quality: moveQuality,
    explanation,
    commentary,
    playedSan,
    bestSan: move.best_move_san ?? sanFromUci(move.fen_before, move.best_move_uci),
    isBest,
  };
}

export function fullMoveReviewPresentation(
  move: MoveAnalysis | null,
  error: ErrorClassification | null,
  moment: CriticalMoment | null,
  userColor: UserColor,
  commentary: MoveCommentary | null = null,
) {
  const review = moveReviewPresentation(move, error, moment, commentary);
  if (!move || !review) return null;
  return {
    ...review,
    evaluationBefore: formatReviewEvaluation(move.evaluation_before_cp, userColor),
    evaluationAfter: formatReviewEvaluation(move.evaluation_after_cp, userColor),
    centipawnLoss: Number.isFinite(move.centipawn_loss) ? Math.max(0, move.centipawn_loss) : null,
    phaseLabel: move.phase === "opening" ? "Дебют" : move.phase === "middlegame" ? "Миттельшпиль" : move.phase === "endgame" ? "Эндшпиль" : null,
    principalVariation: principalVariationPresentation(move.principal_variation, move.fen_before),
  };
}

export function criticalMomentPresentation(moment: CriticalMoment, error: ErrorClassification | null, rank: number, commentary: MoveCommentary | null = null) {
  const visibleError = error?.confidence !== "low" && error?.primary_type ? error : null;
  return {
    rank,
    moveLabel: `${moment.move_number}${moment.ply % 2 === 0 ? "..." : "."}${moment.move_san ?? moment.move_uci}${moment.type === "best_move" ? "!" : annotations[moment.severity]}`,
    typeLabel: criticalTypeLabels[moment.type],
    severityLabel: moment.type === "best_move" ? "Лучший" : severityLabels[moment.severity],
    severityTone: moment.type === "best_move" ? "best" as const : moment.severity,
    explanation: commentary?.summary ?? "Комментарий к этому моменту недоступен.",
    conciseReason: commentary?.headline ?? (visibleError?.primary_type ? conciseTaxonomyLabels[visibleError.primary_type] : criticalReasonLabels[moment.type]),
    evaluationBefore: formatUserPovEvaluation(moment.evaluation_before_user_pov),
    evaluationAfter: formatUserPovEvaluation(moment.evaluation_after_user_pov),
    phaseLabel: moment.phase ? phaseLabels[moment.phase] : null,
  };
}

export function adjacentCriticalMomentPly(moments: CriticalMoment[], selectedPly: number, direction: "previous" | "next"): number | null {
  if (moments.length < 2) return null;
  const current = moments.findIndex((moment) => moment.ply === selectedPly);
  if (direction === "previous") return current > 0 ? moments[current - 1].ply : null;
  if (current === -1) return moments[0].ply;
  return current < moments.length - 1 ? moments[current + 1].ply : null;
}

export function criticalMomentScrollBehavior(reducedMotion: boolean): ScrollBehavior {
  return reducedMotion ? "auto" : "smooth";
}

export function buildEvaluationTimeline(moves: MoveAnalysis[], userColor: UserColor, criticalMoments: CriticalMoment[], selectedPly: number): EvaluationTimelinePoint[] {
  const criticalByPly = new Map(criticalMoments.map((moment) => [moment.ply, moment] as const));
  const ordered = [...moves].sort((a, b) => a.ply - b.ply);
  const initialEvaluation = evaluationToUserPov(ordered[0]?.evaluation_before_cp ?? null, userColor);
  const points: EvaluationTimelinePoint[] = [{
    ply: 0,
    moveLabel: "Начало",
    qualityLabel: "Начальная позиция",
    qualitySymbol: "",
    evaluationBefore: initialEvaluation,
    evaluationAfter: initialEvaluation,
    evaluationBeforeLabel: formatUserPovEvaluation(initialEvaluation),
    evaluationAfterLabel: formatUserPovEvaluation(initialEvaluation),
    displayEvaluation: clampTimelineEvaluation(initialEvaluation),
    classification: "initial",
    isCritical: false,
    criticalType: null,
    isSelected: selectedPly === 0,
  }];
  for (const move of ordered) {
    const before = evaluationToUserPov(move.evaluation_before_cp, userColor);
    const after = evaluationToUserPov(move.evaluation_after_cp, userColor);
    const moveQuality = moveQualityPresentation(move);
    const critical = criticalByPly.get(move.ply) ?? null;
    points.push({
      ply: move.ply,
      moveLabel: `${move.move_number}${move.player_color === "black" ? "..." : "."}${move.played_move_san ?? move.played_move_uci}`,
      qualityLabel: moveQuality.label,
      qualitySymbol: moveQuality.symbol,
      evaluationBefore: before,
      evaluationAfter: after,
      evaluationBeforeLabel: formatUserPovEvaluation(before),
      evaluationAfterLabel: formatUserPovEvaluation(after),
      displayEvaluation: clampTimelineEvaluation(after),
      classification: move.classification,
      isCritical: critical !== null,
      criticalType: critical?.type ?? null,
      isSelected: selectedPly === move.ply,
    });
  }
  return points;
}

export function clampTimelineEvaluation(value: number | null): number | null {
  if (value === null || !Number.isFinite(value)) return null;
  return Math.max(-TIMELINE_EVALUATION_LIMIT, Math.min(TIMELINE_EVALUATION_LIMIT, value));
}

export function buildMoveListRows(moves: MoveAnalysis[]) {
  const grouped = new Map<number, { white?: MoveAnalysis; black?: MoveAnalysis }>();
  for (const move of [...moves].sort((a, b) => a.ply - b.ply)) {
    grouped.set(move.move_number, { ...grouped.get(move.move_number), [move.player_color]: move });
  }
  return [...grouped.entries()].sort(([a], [b]) => a - b);
}

export function moveListPresentation(move: MoveAnalysis, selectedPly: number, criticalPlys: ReadonlySet<number>) {
  const moveQuality = moveQualityPresentation(move);
  const selected = selectedPly === move.ply;
  const critical = criticalPlys.has(move.ply);
  const san = move.played_move_san ?? move.played_move_uci;
  return {
    selected,
    critical,
    san,
    quality: moveQuality,
    accessibleLabel: `${move.move_number}${move.player_color === "black" ? "..." : "."} ${san}, ${moveQuality.label}${critical ? ", критический момент" : ""}`,
  };
}

export function moveListScrollTop(container: { scrollTop: number; clientHeight: number; top: number }, item: { top: number; bottom: number }, padding = 8): number | null {
  const visibleTop = container.top + padding;
  const visibleBottom = container.top + container.clientHeight - padding;
  if (item.top < visibleTop) return Math.max(0, container.scrollTop + item.top - visibleTop);
  if (item.bottom > visibleBottom) return container.scrollTop + item.bottom - visibleBottom;
  return null;
}

export function keyboardNavigationTarget(
  key: string,
  current: number,
  total: number,
): number | null {
  if (key === "ArrowLeft") return Math.max(0, current - 1);
  if (key === "ArrowRight") return Math.min(total, current + 1);
  if (key === "Home") return 0;
  if (key === "End") return total;
  return null;
}

export function shouldIgnoreBoardShortcut(target: Pick<HTMLElement, "matches"> | null): boolean {
  return Boolean(target?.matches("input, textarea, select, button, [contenteditable='true']"));
}
