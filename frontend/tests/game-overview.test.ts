import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import type { GameIntelligenceResponse, GamePhaseStatistics } from "../src/lib/api/types.ts";
import { canShowIntelligence, formatGameResult, formatOpening, formatPlyMove, formatTaxonomyLabel, formatTimeControl, presentPhases, selectMainWeakness, selectPlayers, selectStrongestPhase, selectWeakestPhase } from "../src/lib/game-overview.ts";

function phase(average_cp_loss: number | null, overrides: Partial<GamePhaseStatistics> = {}): GamePhaseStatistics {
  return { start_ply: 1, end_ply: 20, user_moves: 10, average_cp_loss, accuracy: average_cp_loss === null ? null : 100 - average_cp_loss / 2, accuracy_eligible_moves: average_cp_loss === null ? 0 : 10, accuracy_coverage_rate: average_cp_loss === null ? 0 : 1, accuracy_quality_band: "good", inaccuracies: 1, mistakes: 0, blunders: 0, ...overrides };
}

function game(overrides: Partial<GameIntelligenceResponse["game"]> = {}): GameIntelligenceResponse["game"] {
  return { id: 1, external_id: "x", platform: "chess.com", played_at: null, result: "loss", user_color: "white", opponent: "Rival", white_username: "Student", black_username: "Rival", white_rating: 1400, black_rating: 1450, time_control: "180+2", ...overrides };
}

test("game results map to Russian labels", () => {
  assert.equal(formatGameResult("win"), "Победа");
  assert.equal(formatGameResult("loss"), "Поражение");
  assert.equal(formatGameResult("draw"), "Ничья");
  assert.equal(formatGameResult("legacy"), "Результат не указан");
});

test("time controls convert stored seconds without mutating source data", () => {
  assert.equal(formatTimeControl("180+2"), "3+2");
  assert.equal(formatTimeControl("300"), "5+0");
  assert.equal(formatTimeControl("600"), "10+0");
  assert.equal(formatTimeControl(null), null);
});

test("opening presentation supports name, ECO-only and absent data", () => {
  assert.deepEqual(formatOpening({ name: "Caro-Kann Defense", eco: "B13" }), { name: "Защита Каро-Канн", eco: "B13", family: "Защита Каро-Канн", variation: null, subvariation: null });
  assert.deepEqual(formatOpening({ name: null, eco: "A00" }), { name: "A00", eco: null, family: null, variation: null, subvariation: null });
  assert.equal(formatOpening({ name: null, eco: null }), null);
});

test("opening move labels distinguish white and black plies", () => {
  assert.equal(formatPlyMove(11, "Be3"), "6.Be3");
  assert.equal(formatPlyMove(12, "Be3"), "6...Be3");
  assert.equal(formatPlyMove(null, "Be3"), null);
});

test("strongest and weakest phases use higher human accuracy as better", () => {
  const phases = { opening: phase(31), middlegame: phase(126), endgame: phase(54) };
  assert.equal(selectStrongestPhase(phases)?.key, "opening");
  assert.equal(selectWeakestPhase(phases)?.key, "middlegame");
});

test("missing endgame is not synthesized", () => {
  const phases = presentPhases({ opening: phase(31), middlegame: phase(80) });
  assert.deepEqual(phases.map(({ key }) => key), ["opening", "middlegame"]);
});

test("one valid phase does not create a fake best/worst comparison", () => {
  const phases = { opening: phase(31) };
  assert.equal(selectStrongestPhase(phases), null);
  assert.equal(selectWeakestPhase(phases), null);
});

test("zero-user-move and null-ACPL phases are ignored for comparison", () => {
  const phases = { opening: phase(31), middlegame: phase(100, { user_moves: 0 }), endgame: phase(null) };
  assert.deepEqual(presentPhases(phases).map(({ key }) => key), ["opening", "endgame"]);
  assert.equal(selectStrongestPhase(phases), null);
});

test("main weakness selects the largest primary taxonomy count", () => {
  assert.deepEqual(selectMainWeakness({ missed_capture: 3, king_safety: 1 }), { type: "missed_capture", label: "Упущенные взятия", count: 3 });
});

test("taxonomy labels are localized", () => {
  assert.equal(formatTaxonomyLabel("hanging_piece"), "Фигуры под ударом");
  assert.equal(formatTaxonomyLabel("fork"), "Вилки");
  assert.equal(formatTaxonomyLabel("back_rank"), "Слабость последней горизонтали");
});

test("empty or zero error breakdown has no fake weakness", () => {
  assert.equal(selectMainWeakness({}), null);
  assert.equal(selectMainWeakness({ king_safety: 0 }), null);
});

test("main weakness ties use a stable documented priority", () => {
  assert.equal(selectMainWeakness({ king_safety: 2, missed_capture: 2 })?.type, "missed_capture");
});

test("phase ties remain deterministic and choose distinct endpoints", () => {
  const phases = { opening: phase(50), middlegame: phase(50), endgame: phase(50) };
  assert.equal(selectStrongestPhase(phases)?.key, "opening");
  assert.equal(selectWeakestPhase(phases)?.key, "endgame");
});

test("pending, failed and completed analysis states gate derived metrics", () => {
  assert.equal(canShowIntelligence({ status: "pending", intelligence_ready: false }), false);
  assert.equal(canShowIntelligence({ status: "failed", intelligence_ready: false }), false);
  assert.equal(canShowIntelligence({ status: "completed", intelligence_ready: true }), true);
});

test("player snapshots follow user color and omit missing rating data", () => {
  assert.deepEqual(selectPlayers(game()), { user: "Student", userRating: 1400, opponent: "Rival", opponentRating: 1450 });
  assert.deepEqual(selectPlayers(game({ user_color: "black", white_rating: null, black_rating: 1500 })), { user: "Rival", userRating: 1500, opponent: "Student", opponentRating: null });
});

test("overview uses responsive grids and replaces duplicate legacy cards", async () => {
  const component = await readFile(new URL("../src/components/analysis/game-overview.tsx", import.meta.url), "utf8");
  const page = await readFile(new URL("../src/components/analysis/analysis-page.tsx", import.meta.url), "utf8");
  assert.match(component, /grid-cols-2/);
  assert.match(component, /sm:grid-cols-4/);
  assert.match(component, /break-words/);
  assert.match(page, /<GameOverview/);
  assert.doesNotMatch(page, /GameHeaderCard|PhaseStatisticsCard/);
});
