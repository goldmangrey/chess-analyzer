import assert from "node:assert/strict";
import test from "node:test";

import type { CriticalMoment, ErrorClassification, MoveAnalysis } from "../src/lib/api/types.ts";
import { fenForSelectedPly, STANDARD_START_FEN } from "../src/lib/chess-position.ts";
import { buildReviewBoardModel, keyboardNavigationTarget, moveReviewPresentation, shouldIgnoreBoardShortcut } from "../src/lib/review-board.ts";


function move(overrides: Partial<MoveAnalysis> = {}): MoveAnalysis {
  return {
    id: 1, game_id: 1, ply: 1, move_number: 1, player_color: "white", is_user_move: true,
    fen_before: STANDARD_START_FEN, played_move_uci: "e2e4", played_move_san: "e4",
    best_move_uci: "d2d4", best_move_san: "d4", evaluation_before_cp: 20,
    evaluation_after_cp: -180, centipawn_loss: 200, classification: "mistake",
    phase: "opening", principal_variation: null, created_at: "2026-01-01T00:00:00Z", ...overrides,
  };
}

function error(overrides: Partial<ErrorClassification> = {}): ErrorClassification {
  return {
    ply: 1, move_number: 1, move_san: "e4", phase: "opening", severity: "blunder",
    primary_type: "allowed_mate", secondary_types: [], confidence: "high",
    centipawn_loss: 1000, critical_moment_type: "allowed_mate", ...overrides,
  };
}

function moment(overrides: Partial<CriticalMoment> = {}): CriticalMoment {
  return {
    ply: 1, move_number: 1, move_san: "e4", move_uci: "e2e4", phase: "opening",
    type: "turning_point", severity: "blunder", centipawn_loss: 300,
    evaluation_before: 20, evaluation_after: -300, evaluation_before_user_pov: 20,
    evaluation_after_user_pov: -300, importance_score: 80, ...overrides,
  };
}

test("played and distinct best moves produce two labelled arrows", () => {
  const model = buildReviewBoardModel(move(), "white");
  assert.deepEqual(model.played, { from: "e2", to: "e4" });
  assert.deepEqual(model.best, { from: "d2", to: "d4" });
  assert.equal(model.arrows.length, 2);
  assert.equal(model.arrows[0].color, "var(--board-arrow-played)");
  assert.equal(model.arrows[1].color, "var(--board-arrow-best)");
});

test("played equals best has one arrow and a best visual state", () => {
  const model = buildReviewBoardModel(move({ best_move_uci: "e2e4", best_move_san: "e4", classification: "normal" }), "white");
  assert.equal(model.arrows.length, 1);
  assert.equal(model.best, null);
  assert.deepEqual(model.badge && { symbol: model.badge.symbol, label: model.badge.label, tone: model.badge.tone }, { symbol: "★", label: "Лучший", tone: "best" });
});

test("mistake and blunder badges use only real classifications", () => {
  assert.equal(buildReviewBoardModel(move({ classification: "mistake" }), "white").badge?.symbol, "?");
  assert.equal(buildReviewBoardModel(move({ classification: "blunder" }), "white").badge?.symbol, "??");
  const labels = ["Хороший", "Неточность", "Ошибка", "Зевок", "Лучший"];
  assert.equal(labels.includes("Блестящий"), false);
});

test("white and black orientation preserve chess squares for native arrow renderer", () => {
  const white = buildReviewBoardModel(move(), "white");
  const black = buildReviewBoardModel(move(), "black");
  assert.equal(white.orientation, "white");
  assert.equal(black.orientation, "black");
  assert.deepEqual(black.arrows, white.arrows);
});

test("changing selected move changes all overlay endpoints", () => {
  const first = buildReviewBoardModel(move(), "white");
  const second = buildReviewBoardModel(move({ fen_before: "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", played_move_uci: "g1f3", best_move_uci: null }), "white");
  assert.notDeepEqual(first.played, second.played);
  assert.equal(second.best, null);
});

test("navigation supports previous, next, first and last", () => {
  assert.equal(keyboardNavigationTarget("ArrowLeft", 4, 10), 3);
  assert.equal(keyboardNavigationTarget("ArrowRight", 4, 10), 5);
  assert.equal(keyboardNavigationTarget("Home", 4, 10), 0);
  assert.equal(keyboardNavigationTarget("End", 4, 10), 10);
  assert.equal(keyboardNavigationTarget("Escape", 4, 10), null);
});

test("keyboard navigation is ignored inside form controls", () => {
  assert.equal(shouldIgnoreBoardShortcut({ matches: (selector) => selector.includes("input") }), true);
  assert.equal(shouldIgnoreBoardShortcut({ matches: () => false }), false);
});

test("missing best move, missing FEN and malformed UCI fail safely", () => {
  assert.equal(buildReviewBoardModel(move({ best_move_uci: null }), "white").arrows.length, 1);
  assert.deepEqual(buildReviewBoardModel(move({ fen_before: "" }), "white").arrows, []);
  assert.deepEqual(buildReviewBoardModel(move({ played_move_uci: "invalid" }), "white").arrows, []);
  assert.equal(fenForSelectedPly([move({ fen_before: "" })], 1), STANDARD_START_FEN);
});

test("review presentation consumes backend commentary and has a legacy-safe fallback", () => {
  const commentary = { headline: "Был доступен мат", summary: "Здесь был доступен мат.", details: [], recommendation: "Лучше было сыграть Qh7#.", intent: "missed_mate" };
  assert.equal(moveReviewPresentation(move(), error(), null, commentary)?.explanation, commentary.summary);
  assert.equal(moveReviewPresentation(move(), null, moment())?.explanation, "Комментарий к этому ходу недоступен.");
});

test("low-confidence taxonomy never produces its specific claim", () => {
  const presentation = moveReviewPresentation(move({ best_move_san: null, best_move_uci: null }), error({ primary_type: "hanging_piece", confidence: "low" }), null);
  assert.notEqual(presentation?.explanation, "После этого хода фигура остаётся без защиты и теряется.");
});

test("workspace keeps review panel synchronized with selected move and intelligence", async () => {
  const source = await import("node:fs/promises").then((fs) => fs.readFile(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8"));
  assert.match(source, /<MoveReviewPanel[^>]+move=\{selectedMove\}[^>]+error=\{selectedError\}[^>]+moment=\{selectedMoment\}/);
  assert.match(source, /key=\{selectedPly\}/);
});
