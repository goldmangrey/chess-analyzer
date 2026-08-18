import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import type { CriticalMoment, MoveAnalysis } from "../src/lib/api/types.ts";
import { STANDARD_START_FEN } from "../src/lib/chess-position.ts";
import { buildEvaluationTimeline, buildMoveListRows, clampTimelineEvaluation, moveListPresentation, moveListScrollTop, TIMELINE_EVALUATION_LIMIT } from "../src/lib/review-board.ts";

function move(overrides: Partial<MoveAnalysis> = {}): MoveAnalysis {
  return { id: 1, game_id: 1, ply: 1, move_number: 1, player_color: "white", is_user_move: true, fen_before: STANDARD_START_FEN, played_move_uci: "e2e4", played_move_san: "e4", best_move_uci: "d2d4", best_move_san: "d4", evaluation_before_cp: 20, evaluation_after_cp: -180, centipawn_loss: 200, classification: "mistake", phase: "opening", principal_variation: null, created_at: "2026-01-01T00:00:00Z", ...overrides };
}

function moment(overrides: Partial<CriticalMoment> = {}): CriticalMoment {
  return { ply: 1, move_number: 1, move_san: "e4", move_uci: "e2e4", phase: "opening", type: "turning_point", severity: "blunder", centipawn_loss: 300, evaluation_before: 20, evaluation_after: -300, evaluation_before_user_pov: 20, evaluation_after_user_pov: -300, importance_score: 80, ...overrides };
}

test("timeline points are ordered by ply and retain the initial position", () => {
  const points = buildEvaluationTimeline([move({ ply: 2 }), move({ ply: 1 })], "white", [], 0);
  assert.deepEqual(points.map(({ ply }) => ply), [0, 1, 2]);
  assert.equal(points[0].moveLabel, "Начало");
  assert.equal(points[0].isSelected, true);
});

test("timeline uses user POV for white and black users", () => {
  const white = buildEvaluationTimeline([move({ evaluation_before_cp: 120, evaluation_after_cp: -80 })], "white", [], 1)[1];
  const black = buildEvaluationTimeline([move({ evaluation_before_cp: 120, evaluation_after_cp: -80 })], "black", [], 1)[1];
  assert.equal(white.evaluationBefore, 120);
  assert.equal(white.evaluationAfter, -80);
  assert.equal(black.evaluationBefore, -120);
  assert.equal(black.evaluationAfter, 80);
});

test("null evaluation remains a gap instead of invented zero", () => {
  const point = buildEvaluationTimeline([move({ evaluation_after_cp: null })], "white", [], 1)[1];
  assert.equal(point.evaluationAfter, null);
  assert.equal(point.displayEvaluation, null);
  assert.equal(point.evaluationAfterLabel, null);
});

test("positive and negative mate use labels while chart values are clamped", () => {
  const positive = buildEvaluationTimeline([move({ evaluation_after_cp: 100_000 })], "white", [], 1)[1];
  const negative = buildEvaluationTimeline([move({ evaluation_after_cp: -100_000 })], "white", [], 1)[1];
  assert.equal(positive.evaluationAfterLabel, "Мат за вас");
  assert.equal(negative.evaluationAfterLabel, "Мат против вас");
  assert.equal(positive.displayEvaluation, TIMELINE_EVALUATION_LIMIT);
  assert.equal(negative.displayEvaluation, -TIMELINE_EVALUATION_LIMIT);
  assert.equal(clampTimelineEvaluation(2_500), 800);
});

test("selected ply, critical moment and classifications become chart markers", () => {
  const moves = [move({ ply: 1, classification: "normal" }), move({ ply: 2, classification: "mistake" }), move({ ply: 3, classification: "blunder" })];
  const points = buildEvaluationTimeline(moves, "white", [moment({ ply: 3, type: "allowed_mate" })], 2);
  assert.equal(points[1].classification, "normal");
  assert.equal(points[1].isCritical, false);
  assert.equal(points[2].classification, "mistake");
  assert.equal(points[2].isSelected, true);
  assert.equal(points[3].classification, "blunder");
  assert.equal(points[3].isCritical, true);
  assert.equal(points[3].criticalType, "allowed_mate");
});

test("move list reuses best, inaccuracy, mistake and blunder quality indicators", () => {
  assert.equal(moveListPresentation(move({ best_move_uci: "e2e4", classification: "normal" }), 0, new Set()).quality.symbol, "★");
  assert.equal(moveListPresentation(move({ classification: "inaccuracy" }), 0, new Set()).quality.symbol, "?!");
  assert.equal(moveListPresentation(move({ classification: "mistake" }), 0, new Set()).quality.symbol, "?");
  assert.equal(moveListPresentation(move({ classification: "blunder" }), 0, new Set()).quality.symbol, "??");
});

test("selected and critical move states are derived from shared ply data", () => {
  const item = moveListPresentation(move({ ply: 7 }), 7, new Set([7]));
  assert.equal(item.selected, true);
  assert.equal(item.critical, true);
  assert.match(item.accessibleLabel, /критический момент/);
});

test("move rows remain grouped by full move number and ordered", () => {
  const rows = buildMoveListRows([move({ ply: 2, player_color: "black" }), move({ ply: 1, player_color: "white" }), move({ ply: 4, move_number: 2, player_color: "black" })]);
  assert.deepEqual(rows.map(([number]) => number), [1, 2]);
  assert.equal(rows[0][1].white?.ply, 1);
  assert.equal(rows[0][1].black?.ply, 2);
});

test("move list scroll calculation changes only when item leaves its viewport", () => {
  assert.equal(moveListScrollTop({ scrollTop: 100, clientHeight: 200, top: 50 }, { top: 100, bottom: 130 }), null);
  assert.equal(moveListScrollTop({ scrollTop: 100, clientHeight: 200, top: 50 }, { top: 20, bottom: 45 }), 62);
  assert.equal(moveListScrollTop({ scrollTop: 100, clientHeight: 200, top: 50 }, { top: 260, bottom: 285 }), 143);
});

test("timeline and move list clicks use the same onSelect ply callback", async () => {
  const timeline = await readFile(new URL("../src/components/analysis/evaluation-timeline.tsx", import.meta.url), "utf8");
  const moveRow = await readFile(new URL("../src/components/analysis/move-list-row.tsx", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8");
  assert.match(timeline, /onSelect\(data\[index\]\.ply\)/);
  assert.match(moveRow, /onSelect\(move\.ply\)/);
  assert.match(workspace, /selectedPly=\{selectedPly\}/);
  assert.match(workspace, /criticalMoments=\{intelligence\.critical_moments\}/);
});

test("move list auto-scroll is container-scoped and initial position remains selectable", async () => {
  const source = await readFile(new URL("../src/components/analysis/move-list.tsx", import.meta.url), "utf8");
  assert.match(source, /container\.scrollTo/);
  assert.doesNotMatch(source, /scrollIntoView/);
  assert.match(source, /onSelect\(0\)/);
  assert.match(source, />Начало</);
});

test("timeline exposes user POV and does not invent Brilliant quality", async () => {
  const timeline = await readFile(new URL("../src/components/analysis/evaluation-timeline.tsx", import.meta.url), "utf8");
  const moveRow = await readFile(new URL("../src/components/analysis/move-list-row.tsx", import.meta.url), "utf8");
  assert.match(timeline, /Оценка с вашей стороны/);
  assert.doesNotMatch(`${timeline}${moveRow}`, /Блестящ/);
});
