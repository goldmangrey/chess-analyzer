import assert from "node:assert/strict";
import test from "node:test";

import type { CriticalMoment, ErrorClassification, MoveAnalysis } from "../src/lib/api/types.ts";
import { STANDARD_START_FEN } from "../src/lib/chess-position.ts";
import { formatReviewEvaluation, fullMoveReviewPresentation, principalVariationPresentation } from "../src/lib/review-board.ts";

function move(overrides: Partial<MoveAnalysis> = {}): MoveAnalysis {
  return {
    id: 1, game_id: 1, ply: 1, move_number: 1, player_color: "white", is_user_move: true,
    fen_before: STANDARD_START_FEN, played_move_uci: "e2e4", played_move_san: "e4",
    best_move_uci: "d2d4", best_move_san: "d4", evaluation_before_cp: 244,
    evaluation_after_cp: -322, centipawn_loss: 566, classification: "mistake",
    phase: "opening", principal_variation: "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3", created_at: "2026-01-01T00:00:00Z", ...overrides,
  };
}

function error(primary_type: ErrorClassification["primary_type"], confidence: ErrorClassification["confidence"] = "high"): ErrorClassification {
  return { ply: 1, move_number: 1, move_san: "e4", phase: "opening", severity: "blunder", primary_type, secondary_types: [], confidence, centipawn_loss: 566, critical_moment_type: null };
}

function moment(type: CriticalMoment["type"] = "turning_point"): CriticalMoment {
  return { ply: 1, move_number: 1, move_san: "e4", move_uci: "e2e4", phase: "opening", type, severity: "mistake", centipawn_loss: 566, evaluation_before: 244, evaluation_after: -322, evaluation_before_user_pov: 244, evaluation_after_user_pov: -322, importance_score: 80 };
}

test("mistake, blunder and inaccuracy panels share their board quality mapping", () => {
  assert.equal(fullMoveReviewPresentation(move(), null, null, "white")?.label, "Ошибка");
  assert.equal(fullMoveReviewPresentation(move({ classification: "blunder" }), null, null, "white")?.label, "Зевок");
  assert.equal(fullMoveReviewPresentation(move({ classification: "inaccuracy" }), null, null, "white")?.label, "Неточность");
});

test("best move panel does not duplicate played and best moves", () => {
  const review = fullMoveReviewPresentation(move({ best_move_uci: "e2e4", best_move_san: "e4", classification: "normal" }), null, null, "white");
  assert.equal(review?.label, "Лучший");
  assert.equal(review?.isBest, true);
  assert.equal(review?.explanation, "Это сильнейший найденный движком ход.");
});

test("missing best move remains a useful positive panel", () => {
  const review = fullMoveReviewPresentation(move({ best_move_uci: null, best_move_san: null, classification: "normal" }), null, null, "white");
  assert.equal(review?.bestSan, null);
  assert.equal(review?.explanation, "Ход сохраняет оценку позиции.");
});

test("specific deterministic explanations cover mate, capture and fork", () => {
  assert.match(fullMoveReviewPresentation(move(), error("allowed_mate"), null, "white")?.explanation ?? "", /соперник получает форсированный мат/);
  assert.match(fullMoveReviewPresentation(move(), error("missed_mate"), null, "white")?.explanation ?? "", /упустил/);
  assert.equal(fullMoveReviewPresentation(move(), error("missed_capture"), null, "white")?.explanation, "Здесь было более сильное взятие.");
  assert.match(fullMoveReviewPresentation(move(), error("fork"), null, "white")?.explanation ?? "", /вилку/);
});

test("turning point is used after low-confidence taxonomy fallback", () => {
  const review = fullMoveReviewPresentation(move(), error("hanging_piece", "low"), moment(), "white");
  assert.equal(review?.explanation, "После этого хода оценка позиции резко меняется.");
  assert.doesNotMatch(review?.explanation ?? "", /без защиты/);
});

test("generic severity explanations remain available without derived intelligence", () => {
  assert.match(fullMoveReviewPresentation(move({ classification: "blunder" }), null, null, "white")?.explanation ?? "", /значительно/);
  assert.match(fullMoveReviewPresentation(move({ classification: "inaccuracy" }), null, null, "white")?.explanation ?? "", /более точное/);
});

test("normal evaluation formatting uses explicit user POV", () => {
  assert.equal(formatReviewEvaluation(244, "white"), "+2.44");
  assert.equal(formatReviewEvaluation(244, "black"), "-2.44");
  const black = fullMoveReviewPresentation(move(), null, null, "black");
  assert.equal(black?.evaluationBefore, "-2.44");
  assert.equal(black?.evaluationAfter, "+3.22");
});

test("mate and null evaluations never render as giant pawn scores", () => {
  assert.equal(formatReviewEvaluation(100_000, "white"), "Мат за вас");
  assert.equal(formatReviewEvaluation(-100_000, "white"), "Мат против вас");
  assert.equal(formatReviewEvaluation(100_000, "black"), "Мат против вас");
  assert.equal(formatReviewEvaluation(null, "white"), null);
});

test("CP loss and phase are normalized in the presentation model", () => {
  const review = fullMoveReviewPresentation(move(), null, null, "white");
  assert.equal(review?.centipawnLoss, 566);
  assert.equal(review?.phaseLabel, "Дебют");
});

test("persisted SAN PV has a bounded preview and an accessible full value", () => {
  const pv = principalVariationPresentation("d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3", STANDARD_START_FEN);
  assert.equal(pv?.preview, "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7");
  assert.equal(pv?.full.endsWith("e3"), true);
  assert.equal(pv?.truncated, true);
});

test("missing and malformed PV fail safely", () => {
  assert.equal(principalVariationPresentation(null, STANDARD_START_FEN), null);
  assert.equal(principalVariationPresentation("  ", STANDARD_START_FEN), null);
  assert.equal(principalVariationPresentation("e4 {raw-json}", STANDARD_START_FEN), null);
  assert.equal(principalVariationPresentation("e4 illegal", STANDARD_START_FEN), null);
});

test("legacy UCI PV is converted to readable SAN from fen_before", () => {
  const pv = principalVariationPresentation("e2e4 e7e5 g1f3", STANDARD_START_FEN);
  assert.equal(pv?.full, "e4 e5 Nf3");
});

test("changing selected move produces a new synchronized panel model", () => {
  const first = fullMoveReviewPresentation(move(), null, null, "white");
  const second = fullMoveReviewPresentation(move({ ply: 2, move_number: 1, player_color: "black", played_move_uci: "e7e5", played_move_san: "e5", classification: "normal" }), null, null, "white");
  assert.notEqual(first?.moveLabel, second?.moveLabel);
  assert.equal(second?.moveLabel.startsWith("1...e5"), true);
});
