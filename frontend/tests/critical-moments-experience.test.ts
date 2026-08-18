import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import type { CriticalMoment, ErrorClassification } from "../src/lib/api/types.ts";
import { adjacentCriticalMomentPly, criticalMomentPresentation, criticalMomentScrollBehavior } from "../src/lib/review-board.ts";

function moment(overrides: Partial<CriticalMoment> = {}): CriticalMoment {
  return { ply: 21, move_number: 11, move_san: "Nf6", move_uci: "g8f6", phase: "middlegame", type: "turning_point", severity: "blunder", centipawn_loss: 566, evaluation_before: 244, evaluation_after: -322, evaluation_before_user_pov: 244, evaluation_after_user_pov: -322, importance_score: 91, ...overrides };
}

function error(overrides: Partial<ErrorClassification> = {}): ErrorClassification {
  return { ply: 21, move_number: 11, move_san: "Nf6", phase: "middlegame", severity: "blunder", primary_type: "allowed_mate", secondary_types: [], confidence: "high", centipawn_loss: 566, critical_moment_type: "turning_point", ...overrides };
}

test("ranked moments preserve the provided order", () => {
  const moments = [moment({ ply: 31, move_san: "Qa4", importance_score: 90 }), moment({ ply: 9, move_san: "Bb5", importance_score: 80 }), moment({ ply: 22, move_san: "Nf6", importance_score: 70 })];
  assert.deepEqual(moments.map((item, index) => criticalMomentPresentation(item, null, index + 1)).map((item) => [item.rank, item.moveLabel]), [[1, "11.Qa4??"], [2, "11.Bb5??"], [3, "11...Nf6??"]]);
});

test("all critical types have Russian labels", () => {
  assert.equal(criticalMomentPresentation(moment(), null, 1).typeLabel, "Переломный момент");
  assert.equal(criticalMomentPresentation(moment({ type: "missed_opportunity" }), null, 1).typeLabel, "Упущенный шанс");
  assert.equal(criticalMomentPresentation(moment({ type: "missed_mate" }), null, 1).typeLabel, "Упущенный мат");
  assert.equal(criticalMomentPresentation(moment({ type: "allowed_mate" }), null, 1).typeLabel, "Допущенный мат");
  assert.equal(criticalMomentPresentation(moment({ type: "best_move", severity: "normal" }), null, 1).typeLabel, "Сильный момент");
});

test("critical type and severity remain separate textual axes", () => {
  const item = criticalMomentPresentation(moment(), null, 1);
  assert.equal(item.typeLabel, "Переломный момент");
  assert.equal(item.severityLabel, "Зевок");
  assert.equal(criticalMomentPresentation(moment({ severity: "mistake" }), null, 1).severityLabel, "Ошибка");
});

test("phase is localized and null phase stays absent", () => {
  assert.equal(criticalMomentPresentation(moment(), null, 1).phaseLabel, "Миттельшпиль");
  assert.equal(criticalMomentPresentation(moment({ phase: null }), null, 1).phaseLabel, null);
});

test("user-POV evaluation and mate values are formatted without sentinels", () => {
  const regular = criticalMomentPresentation(moment(), null, 1);
  assert.equal(`${regular.evaluationBefore} → ${regular.evaluationAfter}`, "+2.44 → -3.22");
  const mate = criticalMomentPresentation(moment({ evaluation_before_user_pov: 100_000, evaluation_after_user_pov: -100_000 }), null, 1);
  assert.equal(mate.evaluationBefore, "Мат за вас");
  assert.equal(mate.evaluationAfter, "Мат против вас");
});

test("taxonomy is concise while shared explanation remains deterministic", () => {
  const item = criticalMomentPresentation(moment(), error(), 1);
  assert.equal(item.conciseReason, "Допущенный мат");
  assert.match(item.explanation, /форсированный мат/);
});

test("low-confidence taxonomy is not overclaimed", () => {
  const item = criticalMomentPresentation(moment(), error({ primary_type: "hanging_piece", confidence: "low" }), 1);
  assert.equal(item.conciseReason, "Резкая смена оценки");
  assert.doesNotMatch(item.explanation, /без защиты/);
});

test("previous and next navigation respect ranked boundaries", () => {
  const moments = [moment({ ply: 10 }), moment({ ply: 20 }), moment({ ply: 30 })];
  assert.equal(adjacentCriticalMomentPly(moments, 20, "previous"), 10);
  assert.equal(adjacentCriticalMomentPly(moments, 20, "next"), 30);
  assert.equal(adjacentCriticalMomentPly(moments, 10, "previous"), null);
  assert.equal(adjacentCriticalMomentPly(moments, 30, "next"), null);
});

test("no moments and one moment have no meaningless navigation loop", () => {
  assert.equal(adjacentCriticalMomentPly([], 0, "next"), null);
  assert.equal(adjacentCriticalMomentPly([moment()], 21, "next"), null);
  assert.equal(adjacentCriticalMomentPly([moment()], 21, "previous"), null);
});

test("next navigation starts at the first ranked moment when none is active", () => {
  const moments = [moment({ ply: 10 }), moment({ ply: 20 })];
  assert.equal(adjacentCriticalMomentPly(moments, 0, "next"), 10);
  assert.equal(adjacentCriticalMomentPly(moments, 0, "previous"), null);
});

test("reduced-motion preference changes scroll behavior", () => {
  assert.equal(criticalMomentScrollBehavior(false), "smooth");
  assert.equal(criticalMomentScrollBehavior(true), "auto");
});

test("component derives active state from selectedPly and invokes the board callback", async () => {
  const source = await readFile(new URL("../src/components/analysis/critical-moments-card.tsx", import.meta.url), "utf8");
  assert.match(source, /selectedPly === moment\.ply/);
  assert.match(source, /aria-current=\{active \? "step"/);
  assert.match(source, /onSelectPly\(moment\.ply\)/);
  assert.match(source, /Сейчас на доске/);
  assert.doesNotMatch(source, /importance_score/);
});

test("workspace callback synchronizes selection and reduced-motion board scroll", async () => {
  const source = await readFile(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8");
  assert.match(source, /selectPly\(ply\)/);
  assert.match(source, /prefers-reduced-motion/);
  assert.match(source, /scrollIntoView/);
  assert.match(source, /selectedPly=\{selectedPly\}/);
});
