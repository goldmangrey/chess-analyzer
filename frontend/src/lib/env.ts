const fallbackApiBaseUrl = "http://127.0.0.1:8000";

export function normalizeApiBaseUrl(value: string): string {
  const withoutTrailingSlashes = value.replace(/\/+$/, "");
  const withoutTerminalApi = withoutTrailingSlashes.replace(/\/api$/, "");
  return withoutTerminalApi || fallbackApiBaseUrl;
}

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL || fallbackApiBaseUrl,
);
