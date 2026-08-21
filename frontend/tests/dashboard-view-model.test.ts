import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import type { GamePhase, PlayerIntelligenceResponse, ProfileConfidence } from "../src/lib/api/types.ts";
import { buildDashboardViewModel } from "../src/lib/dashboard-view-model.ts";

function confidence(level: ProfileConfidence["level"] = "medium"): ProfileConfidence {
  return { level, score: level === "insufficient" ? 0 : 0.6, sample_games: 30, eligible_games: 30, coverage_rate: 1, eligible_user_moves: 600 };
}

function metricTrend(recent: number | null, previous: number | null, direction: "improving" | "stable" | "worsening" | "insufficient" = "improving") {
  return { recent, previous, absolute_change: recent !== null && previous !== null ? recent - previous : null, relative_change: recent !== null && previous ? (recent - previous) / previous : null, direction, confidence: { level: direction === "insufficient" ? "insufficient" as const : "medium" as const, score: direction === "insufficient" ? 0 : 0.6, recent_games: 30, previous_games: previous === null ? 0 : 19, recent_user_moves: 600, previous_user_moves: previous === null ? 0 : 380, coverage_rate: 1 } };
}

function intelligence(overrides: Partial<PlayerIntelligenceResponse> = {}): PlayerIntelligenceResponse {
  const evidence = [{ game_id: 42, ply: 17, classification: "mistake" as const, phase: "middlegame" as const, played_move_san: "Nb5", played_move_uci: "c3b5", centipawn_loss: 140 }];
  const phase = (name: GamePhase, acpl: number | null, level: ProfileConfidence["level"] = "medium") => ({
    metrics: { user_moves: acpl === null ? 0 : 100, games_with_phase: acpl === null ? 0 : 20, participation_rate: acpl === null ? null : 0.67, moves_with_cp_loss: acpl === null ? 0 : 100, moves_with_classification: acpl === null ? 0 : 100, average_cp_loss: acpl, accuracy: acpl === null ? null : 100 - acpl / 2, accuracy_eligible_moves: acpl === null ? 0 : 100, accuracy_coverage_rate: acpl === null ? 0 : 1, accuracy_quality_band: acpl === null ? null : "good", inaccuracies: 1, mistakes: 2, blunders: 1, serious_errors: 3, serious_errors_per_100_moves: acpl === null ? null : 3 },
    conclusion: { phase: name, weakness_score: acpl, confidence: confidence(level) },
  });
  const opening = phase("opening", 35);
  const middlegame = phase("middlegame", 78);
  const endgame = phase("endgame", null, "insufficient");
  const segment = { games: 10, user_moves: 200, average_cp_loss: 50, accuracy: 84, accuracy_eligible_moves: 200, accuracy_coverage_rate: 1, accuracy_quality_band: "good" as const, mistakes_per_100_moves: 2, blunders_per_100_moves: 1, serious_errors_per_100_moves: 3, blunder_free_rate: 0.5, wins: 5, draws: 1, losses: 4, confidence: confidence() };
  const baseTrend = metricTrend(2, 3);
  return {
    intelligence_version: "1",
    window: { requested_games: 30, available_analyzed_games: 30, selected_games: 30, total_available_analyzed_games: 49 },
    sample: { games: 30, user_moves: 600, white_games: 14, black_games: 16, wins: 13, draws: 2, losses: 15 },
    overall: { average_cp_loss: 61, accuracy: 86.3, accuracy_eligible_moves: 600, accuracy_coverage_rate: 1, accuracy_quality_band: "good", inaccuracies: 20, mistakes: 18, blunders: 9, blunder_free_games: 14, blunder_free_rate: 0.47 },
    data_quality: { games_with_move_analysis: 30, games_with_taxonomy_data: 28, games_with_phase_data: 29, moves_with_phase: 580, moves_without_phase: 20 },
    recurring_errors: [
      { taxonomy: "hanging_piece", incidents: 8, games_affected: 6, games_affected_rate: 0.2, incidents_per_game: 0.27, incidents_per_100_moves: 1.33, evidence },
      { taxonomy: "missed_capture", incidents: 6, games_affected: 5, games_affected_rate: 0.17, incidents_per_game: 0.2, incidents_per_100_moves: 1, evidence: [] },
      { taxonomy: "king_safety", incidents: 4, games_affected: 4, games_affected_rate: 0.13, incidents_per_game: 0.13, incidents_per_100_moves: 0.67, evidence: [] },
      { taxonomy: "fork", incidents: 3, games_affected: 3, games_affected_rate: 0.1, incidents_per_game: 0.1, incidents_per_100_moves: 0.5, evidence: [] },
    ],
    weaknesses: [{ taxonomy: "hanging_piece", score: 72, rank: 1, confidence: confidence(), components: { spread: 0.2, frequency: 0.5, severity: 0.7, recurrence: 0.6 }, evidence_summary: { incidents: 8, games_affected: 6, games_affected_rate: 0.2, incidents_per_100_moves: 1.33 }, evidence }],
    strengths: [{ type: "low_blunder_rate", score: 75, rank: 1, confidence: confidence(), normalized_component: 0.75, metrics: { blunders_per_100_moves: 1 } }],
    phases: { opening: opening.metrics, middlegame: middlegame.metrics, endgame: endgame.metrics },
    phase_profile: { performance: { opening: opening.conclusion, middlegame: middlegame.conclusion, endgame: endgame.conclusion }, strongest_phase: opening.conclusion, weakest_phase: middlegame.conclusion },
    trends: { window_games: 30, recent_games: 30, previous_games: 19, overall: { average_cp_loss: baseTrend, accuracy: metricTrend(86.3, 82.1), inaccuracies_per_100_moves: baseTrend, mistakes_per_100_moves: baseTrend, blunders_per_100_moves: baseTrend, serious_errors_per_100_moves: baseTrend, blunder_free_rate: metricTrend(0.47, 0.4) }, phases: { opening: { average_cp_loss: baseTrend, serious_errors_per_100_moves: baseTrend }, middlegame: { average_cp_loss: baseTrend, serious_errors_per_100_moves: baseTrend }, endgame: { average_cp_loss: baseTrend, serious_errors_per_100_moves: baseTrend } }, recurring_errors: [] },
    segments: { time_controls: { bullet: { ...segment, games: 0 }, blitz: segment, rapid: segment, unknown: { ...segment, games: 0 } }, colors: { white: segment, black: segment }, games_with_known_time_control: 30, games_with_known_color: 30 },
    summary: { status: "ready", main_weakness: { taxonomy: "hanging_piece", score: 72, confidence: confidence() }, main_strength: { type: "low_blunder_rate", score: 75, confidence: confidence() }, strongest_phase: opening.conclusion, weakest_phase: middlegame.conclusion, overall_direction: "improving", confidence: { level: "medium", score: 0.6 } },
    openings: { selected_games: 30, games_with_recognized_opening: 28, games_with_opening_identity: 30, recognition_coverage_rate: 0.93, top: ["Sicilian", "Caro-Kann", "French", "English"].map((name, index) => ({ eco: `B${20 + index}`, name, family: name, variation: null, subvariation: null, games: 8 - index, wins: 3, draws: 1, losses: 4 - index })), by_color: { white: [], black: [] } },
    ...overrides,
  };
}

test("view model selects backend-ranked reliable conclusions", () => {
  const model = buildDashboardViewModel(intelligence(), { chesscom_username: "Student" });
  assert.equal(model.profile.username, "Student");
  assert.equal(model.primaryWeakness?.key, "hanging_piece");
  assert.equal(model.primaryStrength?.key, "low_blunder_rate");
  assert.equal(model.primaryWeakness?.support, "8 случаев · 6 партий");
  assert.deepEqual(model.primaryWeakness?.evidence[0], { gameId: 42, ply: 17, move: "Nb5", moveLabel: "Ход 9.", classification: "Ошибка", href: "/games/42?ply=17" });
  assert.equal(model.primaryStrength?.support, "1 зевок на 100 ходов");
  assert.equal(model.overallTrend.direction, "improving");
  assert.equal(model.phases.find((phase) => phase.isWeakest)?.phase, "middlegame");
  assert.equal(model.phases[0].qualityLabel, "Хорошо");
  assert.equal(model.phases[0].eligibleMoves, 100);
  assert.deepEqual(model.hero, {
    username: "Student", accuracy: 86.3, qualityBand: "good", qualityLabel: "Хорошая",
    sampleGames: 30, userMoves: 600, record: { wins: 13, draws: 2, losses: 15 },
    trend: { direction: "improving", label: "Улучшается" }, readiness: { status: "ready", label: null },
    rating: null, hasData: true,
  });
});

test("hero preserves mixed and insufficient trends and backend readiness", () => {
  const mixed = intelligence();
  mixed.summary.overall_direction = "mixed";
  mixed.summary.status = "limited";
  const limited = buildDashboardViewModel(mixed).hero;
  assert.deepEqual(limited.trend, { direction: "mixed", label: "Смешанный" });
  assert.equal(limited.readiness.label, "Выводы пока ограничены");

  const empty = intelligence();
  empty.sample = { ...empty.sample, games: 0, user_moves: 0, wins: 0, draws: 0, losses: 0 };
  empty.overall.accuracy = null;
  empty.overall.accuracy_quality_band = null;
  empty.summary.overall_direction = "insufficient";
  empty.summary.status = "insufficient";
  const noData = buildDashboardViewModel(empty).hero;
  assert.equal(noData.hasData, false);
  assert.equal(noData.rating, null);
  assert.equal(noData.trend.label, "Недостаточно данных");
});

test("insufficient conclusions and phases stay hidden instead of becoming fake insights", () => {
  const source = intelligence();
  source.weaknesses[0].confidence = confidence("insufficient");
  source.strengths[0].confidence = confidence("insufficient");
  const model = buildDashboardViewModel(source);
  assert.equal(model.primaryWeakness, null);
  assert.equal(model.primaryStrength, null);
  assert.equal(model.phases[2].accuracy, null);
  assert.equal(model.phases[2].isInsufficient, true);
  assert.equal(model.phases[2].support, "Недостаточно данных");
});

test("phase summary follows backend conclusions and never synthesizes a weakest phase", () => {
  const source = intelligence();
  source.summary.weakest_phase = null;
  const model = buildDashboardViewModel(source);
  assert.deepEqual(model.phases.map((phase) => phase.phase), ["opening", "middlegame", "endgame"]);
  assert.equal(model.phases.some((phase) => phase.isWeakest), false);
  assert.equal(model.phases[0].accuracy, 82.5);
  assert.equal(model.phases[0].qualityLabel, "Хорошо");
  assert.equal(model.phases[2].accuracy, null);
  assert.equal(model.phases[2].isInsufficient, true);
});

test("progress uses backend Accuracy trend and preserves a mixed overall conclusion", () => {
  const source = intelligence();
  source.summary.overall_direction = "mixed";
  source.trends.overall.accuracy = metricTrend(87, 81, "improving");
  const progress = buildDashboardViewModel(source).progress;
  assert.deepEqual(progress, {
    current: 87, previous: 81, delta: 6,
    accuracyDirection: "improving", accuracyDirectionLabel: "Улучшается",
    overallDirection: "mixed", overallDirectionLabel: "Смешанный",
    confidence: "medium", hasCurrent: true, hasComparison: true,
    recentGames: 30, previousGames: 19,
    windowLabel: "Последние 30 vs предыдущие 19",
  });
});

test("progress keeps current Accuracy when the previous window is unavailable", () => {
  const source = intelligence();
  source.trends.previous_games = 0;
  source.trends.overall.accuracy = metricTrend(87, null, "insufficient");
  const progress = buildDashboardViewModel(source).progress;
  assert.equal(progress.current, 87);
  assert.equal(progress.previous, null);
  assert.equal(progress.delta, null);
  assert.equal(progress.hasComparison, false);
  assert.equal(progress.accuracyDirection, "insufficient");
  assert.equal(progress.windowLabel, "Последние 30 партий");
});

test("segments retain product order and backend insufficient semantics", () => {
  const source = intelligence();
  source.segments.time_controls.rapid = { ...source.segments.time_controls.rapid, accuracy: 88, games: 12 };
  source.segments.time_controls.blitz = { ...source.segments.time_controls.blitz, accuracy: 82, games: 15 };
  source.segments.time_controls.bullet = { ...source.segments.time_controls.bullet, accuracy: 95, accuracy_eligible_moves: 10, games: 3, confidence: confidence("insufficient") };
  source.segments.colors.white = { ...source.segments.colors.white, accuracy: 88, games: 15 };
  source.segments.colors.black = { ...source.segments.colors.black, accuracy: 84, games: 15 };
  const segments = buildDashboardViewModel(source).segments;
  assert.deepEqual(segments.timeControls.map((segment) => segment.key), ["rapid", "blitz", "bullet"]);
  assert.deepEqual(segments.timeControls.map((segment) => segment.accuracy), [88, 82, 95]);
  assert.equal(segments.timeControls[2].isInsufficient, true);
  assert.equal(segments.timeControls[2].gameCount, "3 партии");
  assert.deepEqual(segments.colors.map((segment) => [segment.label, segment.accuracy]), [["Белыми", 88], ["Чёрными", 84]]);
  assert.equal("isBest" in segments.timeControls[0], false);
});

test("lists are compact, color-separated and deterministic", () => {
  const source = intelligence();
  source.openings.by_color.white = source.openings.top.slice(0, 2);
  source.openings.by_color.black = source.openings.top.slice(2);
  const first = buildDashboardViewModel(source);
  const second = buildDashboardViewModel(source);
  assert.deepEqual(first, second);
  assert.equal(first.recurringMistakes.length, 3);
  assert.equal(first.openings.white.length, 2);
  assert.equal(first.openings.black.length, 2);
  assert.equal(first.openings.white[0].name, "Sicilian");
  assert.equal(first.openings.black[0].name, "French");
  assert.equal(first.openings.coverageLabel, "28 из 30 партий распознано");
});

test("opening summary keeps backend color order, identity and factual record", () => {
  const source = intelligence();
  source.openings.by_color.white = [
    { eco: "A00", name: null, family: null, variation: null, subvariation: null, games: 4, wins: 1, draws: 1, losses: 2 },
    { eco: null, name: null, family: null, variation: null, subvariation: null, games: 2, wins: 0, draws: 0, losses: 2 },
    ...source.openings.top,
  ];
  source.openings.by_color.black = [{ eco: "B12", name: "Caro-Kann Defense: Advance Variation", family: "Caro-Kann Defense", variation: "Advance Variation", subvariation: null, games: 7, wins: 4, draws: 1, losses: 2 }];
  const model = buildDashboardViewModel(source);
  assert.equal(model.openings.white.length, 3);
  assert.equal(model.openings.white[0].name, "A00");
  assert.equal(model.openings.white[1].name, "Дебют не определён");
  assert.equal(model.openings.black[0].name, "Защита Каро-Канн");
  assert.equal(model.openings.black[0].variation, "Вариант с выдвижением");
  assert.equal(model.openings.black[0].gameCount, "7 партий");
  assert.equal(model.openings.black[0].record, "В 4 · Н 1 · П 2");
});

test("empty opening recognition remains a compact factual state", () => {
  const source = intelligence();
  source.openings = { selected_games: 30, games_with_recognized_opening: 0, games_with_opening_identity: 0, recognition_coverage_rate: 0, top: [], by_color: { white: [], black: [] } };
  const model = buildDashboardViewModel(source);
  assert.equal(model.openings.hasData, false);
  assert.equal(model.openings.coverageLabel, "0 из 30 партий распознано");
  assert.deepEqual(model.openings.white, []);
  assert.deepEqual(model.openings.black, []);
});

test("evidence stays bounded while recurring order remains backend-defined", () => {
  const source = intelligence();
  const baseEvidence = source.recurring_errors[0].evidence[0];
  source.recurring_errors[0].evidence = Array.from({ length: 7 }, (_, index) => ({ ...baseEvidence, game_id: 100 + index, ply: index + 1 }));
  source.weaknesses[0].evidence = source.recurring_errors[0].evidence;
  const model = buildDashboardViewModel(source);
  assert.deepEqual(model.recurringMistakes.map((item) => item.taxonomy), ["hanging_piece", "missed_capture", "king_safety"]);
  assert.equal(model.recurringMistakes[0].evidence.length, 5);
  assert.equal(model.primaryWeakness?.evidence.length, 5);
});

test("empty intelligence yields compact empty states without invented scores", () => {
  const source = intelligence({ weaknesses: [], strengths: [], recurring_errors: [], openings: { selected_games: 0, games_with_recognized_opening: 0, games_with_opening_identity: 0, recognition_coverage_rate: null, top: [], by_color: { white: [], black: [] } } });
  const model = buildDashboardViewModel(source);
  assert.equal(model.primaryWeakness, null);
  assert.equal(model.primaryStrength, null);
  assert.deepEqual(model.recurringMistakes, []);
  assert.equal("calculationScore" in model, false);
  assert.equal("chessDNA" in model, false);
});

test("dashboard composition keeps Tier 1 before Tier 2 and Tier 3", async () => {
  const source = await readFile(new URL("../src/components/dashboard/dashboard-page.tsx", import.meta.url), "utf8");
  assert.ok(source.indexOf('data-dashboard-tier="1"') === -1, "Tier 1 is encapsulated in DashboardTierOne");
  assert.ok(source.indexOf("<DashboardTierOne") < source.indexOf('data-dashboard-tier="2"'));
  assert.ok(source.indexOf('data-dashboard-tier="2"') < source.indexOf('data-dashboard-tier="3"'));
  assert.ok(source.lastIndexOf("<RecentGamesCard") > source.indexOf('data-dashboard-tier="3"'));
});

test("compact Hero renders human metrics without technical or invented scores", async () => {
  const source = await readFile(new URL("../src/components/dashboard/chess-profile-hero.tsx", import.meta.url), "utf8");
  assert.match(source, /formatAccuracy\(hero\.accuracy\)/);
  assert.match(source, /hero\.qualityLabel/);
  assert.match(source, /Последние \{hero\.sampleGames\} партий/);
  assert.match(source, /hero\.record\.wins/);
  assert.match(source, /hero\.trend\.label/);
  assert.match(source, /sm:grid-cols/);
  assert.doesNotMatch(source, /ACPL|CP Loss|centipawn|Chess DNA|confidence|Elo|rating/);
});

test("weakness UI exposes bounded evidence without leaking ranking scores", async () => {
  const source = await readFile(new URL("../src/components/dashboard/weakness-intelligence.tsx", import.meta.url), "utf8");
  assert.match(source, /Главная слабость/);
  assert.match(source, /Повторяющиеся ошибки/);
  assert.match(source, /Примеры/);
  assert.match(source, /item\.href/);
  assert.match(source, /min-\[430px\]:grid-cols/);
  assert.doesNotMatch(source, /\.score|weakness_score|confidence_score|83\.4|100%/);
});

test("phase and opening components stay compact and human-facing", async () => {
  const source = await readFile(new URL("../src/components/dashboard/phase-opening-intelligence.tsx", import.meta.url), "utf8");
  assert.match(source, /Игра по фазам/);
  assert.match(source, /Слабейшая фаза/);
  assert.match(source, /Ваши дебюты/);
  assert.match(source, /Белыми/);
  assert.match(source, /Чёрными/);
  assert.match(source, /sm:grid-cols-2/);
  assert.match(source, /overflow-wrap:anywhere/);
  assert.doesNotMatch(source, /ACPL|CP Loss|mastery|skill score|weakness_score|confidence\.score/);
});

test("Progress and Segments are compact, responsive and free of technical metrics", async () => {
  const progress = await readFile(new URL("../src/components/dashboard/progress-comparison.tsx", import.meta.url), "utf8");
  const segments = await readFile(new URL("../src/components/dashboard/dashboard-intelligence-foundation.tsx", import.meta.url), "utf8");
  assert.match(progress, /Прогресс/);
  assert.match(progress, /Тренд точности/);
  assert.match(progress, /Общий тренд/);
  assert.match(progress, /formatPercentagePointChange/);
  assert.match(progress, /Недостаточно предыдущих данных/);
  assert.match(segments, /Контроль времени/);
  assert.match(segments, /По цвету/);
  assert.match(segments, /sm:grid-cols-2/);
  assert.match(segments, /Недостаточно данных/);
  assert.doesNotMatch(`${progress}\n${segments}`, /ACPL|CP Loss|centipawn|best time control|skill score|rating|isBest/);
});

test("dashboard keeps a compact profile fallback when intelligence is unavailable", async () => {
  const dashboardPage = await readFile(new URL("../src/components/dashboard/dashboard-page.tsx", import.meta.url), "utf8");
  const route = await readFile(new URL("../src/app/page.tsx", import.meta.url), "utf8");
  assert.match(dashboardPage, /ChessProfileHeroUnavailable/);
  assert.match(dashboardPage, /intelligence: PlayerIntelligenceResponse \| null/);
  assert.match(route, /result\.dashboard\.status === "rejected"/);
  assert.match(route, /result\.intelligence\.status === "fulfilled" \? result\.intelligence\.value : null/);
});
