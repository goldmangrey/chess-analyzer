import { apiFetch } from "./client";
import type { SystemStatus } from "./types";

export function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  return apiFetch<SystemStatus>("/api/system/status", { cache: "no-store", signal });
}
