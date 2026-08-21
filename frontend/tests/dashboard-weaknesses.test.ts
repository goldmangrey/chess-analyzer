import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import { gameMomentHref, parseInitialSelectedPly } from "../src/lib/analysis-url.ts";
import { gameCountLabel, incidentCountLabel, taxonomyLabel } from "../src/lib/chess-labels.ts";

test("dashboard taxonomy labels are centralized and human-readable", () => {
  assert.equal(taxonomyLabel("missed_capture"), "Упущенные взятия");
  assert.equal(taxonomyLabel("missed_mate"), "Упущенный мат");
  assert.equal(taxonomyLabel("hanging_piece"), "Фигуры под ударом");
});

test("Russian support counts use correct plural forms", () => {
  assert.equal(incidentCountLabel(1), "1 случай");
  assert.equal(incidentCountLabel(2), "2 случая");
  assert.equal(incidentCountLabel(5), "5 случаев");
  assert.equal(incidentCountLabel(11), "11 случаев");
  assert.equal(gameCountLabel(1), "1 партия");
  assert.equal(gameCountLabel(2), "2 партии");
  assert.equal(gameCountLabel(5), "5 партий");
});

test("evidence links target an exact Game Report ply", () => {
  assert.equal(gameMomentHref(42, 17), "/games/42?ply=17");
});

test("Game Report accepts only an in-range integer initial ply", () => {
  assert.equal(parseInitialSelectedPly("17", 40), 17);
  assert.equal(parseInitialSelectedPly("0", 40), 0);
  assert.equal(parseInitialSelectedPly("41", 40), 0);
  assert.equal(parseInitialSelectedPly("-1", 40), 0);
  assert.equal(parseInitialSelectedPly("1.5", 40), 0);
  assert.equal(parseInitialSelectedPly(["17"], 40), 0);
  assert.equal(parseInitialSelectedPly(undefined, 40), 0);
});

test("deep-link ply initializes the existing selectedPly state", async () => {
  const route = await readFile(new URL("../src/app/games/[id]/page.tsx", import.meta.url), "utf8");
  const page = await readFile(new URL("../src/components/analysis/analysis-page.tsx", import.meta.url), "utf8");
  assert.match(route, /parseInitialSelectedPly/);
  assert.match(route, /initialSelectedPly=\{initialSelectedPly\}/);
  assert.match(page, /useState\(initialSelectedPly\)/);
  assert.doesNotMatch(page, /initialSelectedPly.*useEffect/);
});
