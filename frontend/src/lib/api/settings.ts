import { apiFetch } from "./client";
import type { AppSettings, AppSettingsUpdate } from "./types";

export function fetchAppSettings(signal?: AbortSignal): Promise<AppSettings> {
  return apiFetch<AppSettings>("/api/settings", { cache: "no-store", signal });
}

export function updateAppSettings(request: AppSettingsUpdate, signal?: AbortSignal): Promise<AppSettings> {
  return apiFetch<AppSettings>("/api/settings", { method: "PATCH", body: JSON.stringify(request), signal });
}
