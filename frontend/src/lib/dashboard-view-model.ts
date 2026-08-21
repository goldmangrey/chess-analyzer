import type {
  AppSettings,
  ErrorType,
  GamePhase,
  IntelligenceConfidenceLevel,
  IntelligenceDirection,
  PlayerIntelligenceResponse,
  PlayerSegmentMetrics,
  PlayerStrengthType,
  UserColor,
} from "./api/types";
import { classificationLabel, confidenceLabel, gameCountLabel, incidentCountLabel, pluralizeRu, taxonomyLabel } from "./chess-labels.ts";
import { gameMomentHref } from "./analysis-url.ts";
import { accuracyQualityLabel, accuracyQualityShortLabel } from "./human-metrics.ts";
import { localizeOpeningFamily, localizeOpeningName, localizeOpeningVariation } from "./opening-localization.ts";

const strengthLabels: Record<PlayerStrengthType, string> = {
  low_blunder_rate: "Редкие зевки", blunder_free_consistency: "Стабильность без зевков",
  low_mistake_rate: "Редкие ошибки", overall_precision: "Общая точность",
};
const phaseLabels: Record<GamePhase, string> = { opening: "Дебют", middlegame: "Миттельшпиль", endgame: "Эндшпиль" };
const directionLabels: Record<IntelligenceDirection, string> = {
  improving: "Улучшается", stable: "Стабильно", worsening: "Ухудшается", mixed: "Смешанный", insufficient: "Недостаточно данных",
};

export type DashboardEvidenceViewModel = {
  gameId: number;
  ply: number;
  move: string | null;
  moveLabel: string;
  classification: string;
  href: string;
};

export type DashboardInsight = {
  key: string;
  label: string;
  confidence: IntelligenceConfidenceLevel;
  confidenceLabel: string;
  support: string | null;
  evidence: DashboardEvidenceViewModel[];
};

export type DashboardRecurringMistake = {
  taxonomy: ErrorType;
  label: string;
  incidents: number;
  gamesAffected: number;
  support: string;
  evidence: DashboardEvidenceViewModel[];
};

export type DashboardProfileHeroViewModel = {
  username: string | null;
  accuracy: number | null;
  qualityBand: PlayerIntelligenceResponse["overall"]["accuracy_quality_band"];
  qualityLabel: string | null;
  sampleGames: number;
  userMoves: number;
  record: { wins: number; draws: number; losses: number };
  trend: { direction: IntelligenceDirection; label: string };
  readiness: {
    status: PlayerIntelligenceResponse["summary"]["status"];
    label: string | null;
  };
  rating: null;
  hasData: boolean;
};

export type DashboardPhaseViewModel = {
  phase: GamePhase;
  label: string;
  accuracy: number | null;
  qualityLabel: string | null;
  isWeakest: boolean;
  isInsufficient: boolean;
  eligibleMoves: number;
  support: string;
};

export type DashboardOpeningRowViewModel = {
  key: string;
  eco: string | null;
  name: string;
  variation: string | null;
  games: number;
  gameCount: string;
  record: string;
};

export type DashboardOpeningSummaryViewModel = {
  selectedGames: number;
  recognizedGames: number;
  coverageLabel: string | null;
  hasData: boolean;
  white: DashboardOpeningRowViewModel[];
  black: DashboardOpeningRowViewModel[];
};

export type DashboardProgressViewModel = {
  current: number | null;
  previous: number | null;
  delta: number | null;
  accuracyDirection: IntelligenceDirection;
  accuracyDirectionLabel: string;
  overallDirection: IntelligenceDirection;
  overallDirectionLabel: string;
  confidence: IntelligenceConfidenceLevel;
  hasCurrent: boolean;
  hasComparison: boolean;
  recentGames: number;
  previousGames: number;
  windowLabel: string;
};

export type DashboardSegmentViewModel = {
  key: "rapid" | "blitz" | "bullet" | UserColor;
  label: string;
  accuracy: number | null;
  games: number;
  gameCount: string;
  qualityLabel: string | null;
  confidence: IntelligenceConfidenceLevel;
  isInsufficient: boolean;
};

export type DashboardViewModel = {
  hero: DashboardProfileHeroViewModel;
  profile: {
    username: string | null;
    rating: number | null;
    games: number;
    userMoves: number;
    wins: number;
    draws: number;
    losses: number;
    accuracy: number | null;
    status: PlayerIntelligenceResponse["summary"]["status"];
  };
  primaryWeakness: DashboardInsight | null;
  primaryStrength: DashboardInsight | null;
  overallTrend: { direction: IntelligenceDirection; label: string; confidence: IntelligenceConfidenceLevel };
  phases: DashboardPhaseViewModel[];
  recurringMistakes: DashboardRecurringMistake[];
  openings: DashboardOpeningSummaryViewModel;
  progress: DashboardProgressViewModel;
  segments: {
    timeControls: DashboardSegmentViewModel[];
    colors: DashboardSegmentViewModel[];
  };
};

function usable(level: IntelligenceConfidenceLevel): boolean {
  return level !== "insufficient";
}

function evidenceViewModel(evidence: PlayerIntelligenceResponse["recurring_errors"][number]["evidence"] | undefined): DashboardEvidenceViewModel[] {
  return (evidence ?? []).slice(0, 5).map((item) => ({
    gameId: item.game_id,
    ply: item.ply,
    move: item.played_move_san,
    moveLabel: `Ход ${Math.ceil(item.ply / 2)}${item.ply % 2 === 0 ? "…" : "."}`,
    classification: classificationLabel(item.classification),
    href: gameMomentHref(item.game_id, item.ply),
  }));
}

function strengthSupport(strength: PlayerIntelligenceResponse["strengths"][number]): string | null {
  const metric = Object.entries(strength.metrics)[0];
  if (!metric || !Number.isFinite(metric[1])) return null;
  const [name, value] = metric;
  if (name === "blunder_free_rate") return `${Math.round(value * 100)}% партий без зевков`;
  if (name === "blunders_per_100_moves") return `${value.toLocaleString("ru-RU", { maximumFractionDigits: 1 })} ${value === 1 ? "зевок" : "зевка"} на 100 ходов`;
  if (name === "mistakes_per_100_moves") return `${value.toLocaleString("ru-RU", { maximumFractionDigits: 1 })} ${value === 1 ? "ошибка" : "ошибки"} на 100 ходов`;
  return null;
}

function openingRow(opening: PlayerIntelligenceResponse["openings"]["top"][number]): DashboardOpeningRowViewModel {
  const name = localizeOpeningFamily(opening.family) ?? localizeOpeningName(opening.name) ?? opening.eco ?? "Дебют не определён";
  return {
    key: `${opening.eco ?? "no-eco"}:${opening.name ?? name}`,
    eco: opening.eco,
    name,
    variation: localizeOpeningVariation(opening.variation),
    games: opening.games,
    gameCount: gameCountLabel(opening.games),
    record: `В ${opening.wins} · Н ${opening.draws} · П ${opening.losses}`,
  };
}

const segmentLabels = {
  rapid: "Rapid", blitz: "Blitz", bullet: "Bullet", white: "Белыми", black: "Чёрными",
} as const;

function segmentViewModel(
  key: "rapid" | "blitz" | "bullet" | UserColor,
  metrics: PlayerSegmentMetrics,
): DashboardSegmentViewModel {
  const isInsufficient = metrics.confidence.level === "insufficient"
    || metrics.accuracy === null
    || metrics.accuracy_eligible_moves <= 0;
  return {
    key,
    label: segmentLabels[key],
    accuracy: metrics.accuracy,
    games: metrics.games,
    gameCount: gameCountLabel(metrics.games),
    qualityLabel: isInsufficient ? null : accuracyQualityShortLabel(metrics.accuracy_quality_band),
    confidence: metrics.confidence.level,
    isInsufficient,
  };
}

export function buildDashboardViewModel(
  intelligence: PlayerIntelligenceResponse,
  settings?: Pick<AppSettings, "chesscom_username">,
): DashboardViewModel {
  const weakness = intelligence.summary.main_weakness && usable(intelligence.summary.main_weakness.confidence.level)
    ? intelligence.weaknesses.find((item) => item.taxonomy === intelligence.summary.main_weakness?.taxonomy && usable(item.confidence.level)) ?? null
    : null;
  const strength = intelligence.summary.main_strength && usable(intelligence.summary.main_strength.confidence.level)
    ? intelligence.strengths.find((item) => item.type === intelligence.summary.main_strength?.type && usable(item.confidence.level)) ?? null
    : null;
  const weakestPhase = intelligence.summary.weakest_phase?.confidence.level !== "insufficient"
    ? intelligence.summary.weakest_phase?.phase ?? null
    : null;
  const username = settings?.chesscom_username ?? null;
  const accuracy = intelligence.overall.accuracy ?? null;
  const accuracyTrend = intelligence.trends.overall.accuracy;
  const readinessLabel = intelligence.summary.status === "limited"
    ? "Выводы пока ограничены"
    : intelligence.summary.status === "insufficient"
      ? "Недостаточно партий для полного профиля"
      : null;
  return {
    hero: {
      username,
      accuracy,
      qualityBand: intelligence.overall.accuracy_quality_band ?? null,
      qualityLabel: accuracyQualityLabel(intelligence.overall.accuracy_quality_band),
      sampleGames: intelligence.sample.games,
      userMoves: intelligence.sample.user_moves,
      record: {
        wins: intelligence.sample.wins,
        draws: intelligence.sample.draws,
        losses: intelligence.sample.losses,
      },
      trend: {
        direction: intelligence.summary.overall_direction,
        label: directionLabels[intelligence.summary.overall_direction],
      },
      readiness: { status: intelligence.summary.status, label: readinessLabel },
      rating: null,
      hasData: intelligence.sample.games > 0,
    },
    profile: {
      username,
      rating: null,
      games: intelligence.sample.games,
      userMoves: intelligence.sample.user_moves,
      wins: intelligence.sample.wins,
      draws: intelligence.sample.draws,
      losses: intelligence.sample.losses,
      accuracy: intelligence.overall.accuracy ?? null,
      status: intelligence.summary.status,
    },
    primaryWeakness: weakness ? {
      key: weakness.taxonomy,
      label: taxonomyLabel(weakness.taxonomy),
      confidence: weakness.confidence.level,
      confidenceLabel: confidenceLabel(weakness.confidence.level),
      support: `${incidentCountLabel(weakness.evidence_summary.incidents)} · ${gameCountLabel(weakness.evidence_summary.games_affected)}`,
      evidence: evidenceViewModel(weakness.evidence),
    } : null,
    primaryStrength: strength ? {
      key: strength.type,
      label: strengthLabels[strength.type],
      confidence: strength.confidence.level,
      confidenceLabel: confidenceLabel(strength.confidence.level),
      support: strengthSupport(strength),
      evidence: [],
    } : null,
    overallTrend: {
      direction: intelligence.summary.overall_direction,
      label: directionLabels[intelligence.summary.overall_direction],
      confidence: intelligence.summary.confidence.level,
    },
    phases: (["opening", "middlegame", "endgame"] as const).map((phase) => {
      const metrics = intelligence.phases[phase];
      const confidence = intelligence.phase_profile.performance[phase].confidence.level;
      const accuracy = metrics.accuracy ?? null;
      const isInsufficient = confidence === "insufficient" || accuracy === null || metrics.accuracy_eligible_moves <= 0;
      return {
        phase,
        label: phaseLabels[phase],
        accuracy,
        qualityLabel: isInsufficient ? null : accuracyQualityShortLabel(metrics.accuracy_quality_band),
        eligibleMoves: metrics.accuracy_eligible_moves,
        isInsufficient,
        isWeakest: !isInsufficient && weakestPhase === phase,
        support: isInsufficient ? "Недостаточно данных" : pluralizeRu(metrics.accuracy_eligible_moves, ["ход", "хода", "ходов"]),
      };
    }),
    recurringMistakes: intelligence.recurring_errors.slice(0, 3).map((item) => ({
      taxonomy: item.taxonomy,
      label: taxonomyLabel(item.taxonomy),
      incidents: item.incidents,
      gamesAffected: item.games_affected,
      support: `${incidentCountLabel(item.incidents)} · ${gameCountLabel(item.games_affected)}`,
      evidence: evidenceViewModel(item.evidence),
    })),
    openings: {
      selectedGames: intelligence.openings.selected_games,
      recognizedGames: intelligence.openings.games_with_recognized_opening,
      coverageLabel: intelligence.openings.selected_games > 0
        ? `${intelligence.openings.games_with_recognized_opening} из ${intelligence.openings.selected_games} партий распознано`
        : null,
      hasData: intelligence.openings.games_with_recognized_opening > 0,
      white: intelligence.openings.by_color.white.slice(0, 3).map(openingRow),
      black: intelligence.openings.by_color.black.slice(0, 3).map(openingRow),
    },
    progress: {
      current: accuracyTrend.recent,
      previous: accuracyTrend.previous,
      delta: accuracyTrend.absolute_change,
      accuracyDirection: accuracyTrend.direction,
      accuracyDirectionLabel: directionLabels[accuracyTrend.direction],
      overallDirection: intelligence.summary.overall_direction,
      overallDirectionLabel: directionLabels[intelligence.summary.overall_direction],
      confidence: accuracyTrend.confidence.level,
      hasCurrent: accuracyTrend.recent !== null,
      hasComparison: accuracyTrend.recent !== null && accuracyTrend.previous !== null,
      recentGames: intelligence.trends.recent_games,
      previousGames: intelligence.trends.previous_games,
      windowLabel: intelligence.trends.previous_games > 0
        ? `Последние ${intelligence.trends.recent_games} vs предыдущие ${intelligence.trends.previous_games}`
        : `Последние ${intelligence.trends.recent_games} партий`,
    },
    segments: {
      timeControls: (["rapid", "blitz", "bullet"] as const)
        .map((key) => segmentViewModel(key, intelligence.segments.time_controls[key])),
      colors: (["white", "black"] as const)
        .map((key) => segmentViewModel(key, intelligence.segments.colors[key])),
    },
  };
}
