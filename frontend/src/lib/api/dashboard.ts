import { apiFetch } from "./client";
import type { StatisticsDashboard } from "./types";

export function fetchDashboard(signal?: AbortSignal): Promise<StatisticsDashboard> {
  return apiFetch<StatisticsDashboard>("/api/stats/dashboard", { cache: "no-store", signal });
}
