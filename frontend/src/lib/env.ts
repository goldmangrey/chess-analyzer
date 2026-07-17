const fallbackApiBaseUrl = "http://127.0.0.1:8000";

export function normalizeApiBaseUrl(value: string): string {
  const withoutTrailingSlashes = value.replace(/\/+$/, "");
  const withoutTerminalApi = withoutTrailingSlashes.replace(/\/api$/, "");
  return withoutTerminalApi || fallbackApiBaseUrl;
}

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL || fallbackApiBaseUrl,
);

export function parsePublicBoolean(value: string | undefined, fallback = false): boolean {
  if (value === undefined || value === "") return fallback;
  if (value === "true") return true;
  if (value === "false") return false;
  throw new Error("NEXT_PUBLIC_SERVER_SYNC_ENABLED must be true or false");
}

export const SERVER_SYNC_ENABLED = parsePublicBoolean(
  process.env.NEXT_PUBLIC_SERVER_SYNC_ENABLED,
);
