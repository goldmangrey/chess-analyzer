import { API_BASE_URL } from "@/lib/env";

import { ApiError, ApiNetworkError, type ApiErrorPayload } from "./errors";

export type ApiFetchOptions = RequestInit & { signal?: AbortSignal };

function isErrorPayload(value: unknown): value is ApiErrorPayload {
  return typeof value === "object" && value !== null;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${normalizedPath}`, {
      ...options,
      headers,
      cache: options.cache ?? "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiNetworkError("Backend is unavailable", { cause: error });
  }

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      // The status code remains the authoritative error signal.
    }
    const parsed = isErrorPayload(payload) ? payload : {};
    throw new ApiError(
      response.status,
      typeof parsed.error === "string" ? parsed.error : "api_error",
      typeof parsed.message === "string" ? parsed.message : `Request failed with status ${response.status}`,
    );
  }

  return (await response.json()) as T;
}
