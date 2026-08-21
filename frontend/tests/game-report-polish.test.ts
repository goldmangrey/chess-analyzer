import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import { buildReviewBoardModel } from "../src/lib/review-board.ts";

test("completed report follows overview, board, review, critical, timeline, move-list hierarchy", async () => {
  const source = await readFile(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8");
  const board = source.indexOf("<ChessBoardPanel");
  const review = source.indexOf("<MoveReviewPanel");
  const critical = source.indexOf("<CriticalMomentsCard");
  const timeline = source.indexOf("<EvaluationTimeline");
  const moves = source.indexOf("<MoveList");
  assert.equal(board >= 0 && board < review && review < critical && critical < timeline && timeline < moves, true);
});

test("initial ply has no played move, best arrow or badge", () => {
  const model = buildReviewBoardModel(null, "white");
  assert.equal(model.played, null);
  assert.equal(model.best, null);
  assert.equal(model.badge, null);
  assert.deepEqual(model.arrows, []);
});

test("mobile structure avoids forced widths and keeps board before supporting sections", async () => {
  const workspace = await readFile(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8");
  const overview = await readFile(new URL("../src/components/analysis/game-overview.tsx", import.meta.url), "utf8");
  const moveList = await readFile(new URL("../src/components/analysis/move-list.tsx", import.meta.url), "utf8");
  assert.match(workspace, /grid min-w-0 gap-4.*xl:grid-cols/);
  assert.match(workspace, /xl:row-span-2/);
  assert.match(workspace, /xl:col-start-2 xl:row-start-2/);
  assert.match(overview, /min-w-0/);
  assert.match(overview, /w-full.*sm:w-auto/);
  assert.doesNotMatch(moveList, /sm:min-w-/);
});

test("touch controls retain practical hit areas", async () => {
  const navigation = await readFile(new URL("../src/components/analysis/board-navigation.tsx", import.meta.url), "utf8");
  const moveList = await readFile(new URL("../src/components/analysis/move-list-row.tsx", import.meta.url), "utf8");
  const review = await readFile(new URL("../src/components/analysis/move-review-panel.tsx", import.meta.url), "utf8");
  assert.match(navigation, /size="md"/);
  assert.match(moveList, /min-h-10/);
  assert.match(review, /min-h-10/);
});

test("loading skeleton mirrors the final report section order", async () => {
  const source = await readFile(new URL("../src/components/analysis/analysis-skeleton.tsx", import.meta.url), "utf8");
  assert.match(source, /xl:grid-cols-\[7fr_5fr\]/);
  assert.match(source, /xl:row-span-2/);
});

test("desktop review keeps board, review and move list in one primary grid", async () => {
  const workspace = await readFile(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8");
  const moveList = await readFile(new URL("../src/components/analysis/move-list.tsx", import.meta.url), "utf8");
  const timeline = await readFile(new URL("../src/components/analysis/evaluation-timeline.tsx", import.meta.url), "utf8");
  assert.match(workspace, /xl:grid-cols-\[minmax\(0,7fr\)_minmax\(350px,5fr\)\]/);
  assert.match(moveList, /overflow-y-auto/);
  assert.doesNotMatch(workspace, /overflow-y-auto/);
  assert.match(timeline, /h-44 sm:h-48/);
});

test("board uses the normalized fresh-green palette and keeps overlay tokens", async () => {
  const css = await readFile(new URL("../src/app/globals.css", import.meta.url), "utf8");
  const board = await readFile(new URL("../src/components/analysis/chess-board-panel.tsx", import.meta.url), "utf8");
  assert.match(css, /--board-light: #f3eddd/);
  assert.match(css, /--board-dark: #5d8b61/);
  assert.match(board, /var\(--board-last-move\)/);
  assert.match(board, /var\(--board-best-move\)/);
  assert.match(board, /var\(--board-arrow-best\)/);
});

test("evaluation bar uses a hydration-stable percentage", async () => {
  const source = await readFile(new URL("../src/components/analysis/evaluation-bar.tsx", import.meta.url), "utf8");
  assert.match(source, /evaluationWhitePercent\(evaluation\)\.toFixed\(4\)/);
});
