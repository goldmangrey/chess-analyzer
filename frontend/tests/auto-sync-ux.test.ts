import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { formatBrowserDateTime } from "../src/lib/date-time.ts";
import {
  ANALYSIS_POLL_INTERVAL_MS,
  DASHBOARD_POLL_INTERVAL_MS,
  shouldPollAnalysis,
} from "../src/lib/polling.ts";

const dashboardSource = readFileSync(new URL("../src/components/dashboard/dashboard-page.tsx", import.meta.url), "utf8");
const analysisSource = readFileSync(new URL("../src/components/analysis/analysis-page.tsx", import.meta.url), "utf8");
const analysisWorkspaceSource = readFileSync(new URL("../src/components/analysis/analysis-workspace.tsx", import.meta.url), "utf8");
const analysisRouteSource = readFileSync(new URL("../src/app/games/[id]/page.tsx", import.meta.url), "utf8");
const analysisLoadingSource = readFileSync(new URL("../src/app/games/[id]/loading.tsx", import.meta.url), "utf8");
const criticalMomentsSource = readFileSync(new URL("../src/components/analysis/critical-moments-card.tsx", import.meta.url), "utf8");
const moveListSource = readFileSync(new URL("../src/components/analysis/move-list.tsx", import.meta.url), "utf8");
const pollingSource = readFileSync(new URL("../src/hooks/use-background-polling.ts", import.meta.url), "utf8");
const frontendSourceFiles = [dashboardSource, analysisSource, pollingSource];

test("UTC timestamp is formatted in the supplied browser timezone", () => {
  assert.equal(
    formatBrowserDateTime("2026-08-11T13:09:00Z", {
      locale: "en-GB",
      timeZone: "Asia/Almaty",
      includeDate: false,
    }),
    "18:09",
  );
});

test("dashboard polls all three resources every 15 seconds", () => {
  assert.equal(DASHBOARD_POLL_INTERVAL_MS, 15_000);
  assert.match(dashboardSource, /fetchAppSettings\(signal\)/);
  assert.match(dashboardSource, /fetchDashboard\(signal\)/);
  assert.match(dashboardSource, /fetchGames\(/);
});

test("background polling pauses while hidden, refreshes on visibility, and prevents overlap", () => {
  assert.match(pollingSource, /document\.hidden/);
  assert.match(pollingSource, /visibilitychange/);
  assert.match(pollingSource, /runningRef\.current/);
  assert.match(pollingSource, /schedule\(\);/);
});

test("pending and processing games poll every 3 seconds", () => {
  assert.equal(ANALYSIS_POLL_INTERVAL_MS, 3_000);
  assert.equal(shouldPollAnalysis("pending"), true);
  assert.equal(shouldPollAnalysis("processing"), true);
});

test("queued and analyzing games also continue polling", () => {
  assert.equal(shouldPollAnalysis("queued"), true);
  assert.equal(shouldPollAnalysis("analyzing"), true);
});

test("analysis polling stops after completed", () => {
  assert.equal(shouldPollAnalysis("completed"), false);
});

test("analysis polling stops after failed", () => {
  assert.equal(shouldPollAnalysis("failed"), false);
});

test("dashboard keeps rendered state when a background request fails", () => {
  assert.match(dashboardSource, /useState\(data\)/);
  assert.match(pollingSource, /setLastError\(error\)/);
  assert.doesNotMatch(pollingSource, /successRef\.current\([^)]*error/);
});

test("live refresh never uses a full-page reload", () => {
  for (const source of frontendSourceFiles) {
    assert.doesNotMatch(source, /(?:window\.)?location\.reload\s*\(/);
  }
});

test("completed analysis fetches moves before rendering the report", () => {
  assert.match(analysisSource, /nextIntelligence\.analysis\.status === "completed"/);
  assert.match(analysisSource, /fetchGameIntelligence/);
  assert.match(analysisSource, /fetchGameMoves/);
  assert.match(analysisSource, /setLiveMoves/);
});

test("analysis route loads unified intelligence with loading and error boundaries", () => {
  assert.match(analysisRouteSource, /fetchGameIntelligence\(gameId\)/);
  assert.doesNotMatch(analysisRouteSource, /fetchGameDetail\(gameId\)/);
  assert.match(analysisLoadingSource, /export default function/);
  assert.match(analysisRouteSource, /status: "unavailable"/);
});

test("critical moment and move list selections update the shared review ply", () => {
  assert.match(criticalMomentsSource, /onSelectPly\(moment\.ply\)/);
  assert.match(analysisSource, /setSelectedPly\(ply\)/);
  assert.match(analysisWorkspaceSource, /scrollIntoView/);
  assert.match(moveListSource, /onSelect\(0\)/);
  assert.match(moveListSource, /selectedPly=\{selectedPly\}/);
});
