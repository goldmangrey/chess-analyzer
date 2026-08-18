import type { AnalysisStatus } from "./api/types";

export const DASHBOARD_POLL_INTERVAL_MS = 15_000;
export const ANALYSIS_POLL_INTERVAL_MS = 3_000;

const ACTIVE_ANALYSIS_STATUSES: ReadonlySet<AnalysisStatus> = new Set([
  "pending",
  "queued",
  "processing",
  "analyzing",
]);

export function shouldPollAnalysis(status: AnalysisStatus): boolean {
  return ACTIVE_ANALYSIS_STATUSES.has(status);
}

export function isTerminalAnalysisStatus(status: AnalysisStatus): boolean {
  return status === "completed" || status === "failed";
}
