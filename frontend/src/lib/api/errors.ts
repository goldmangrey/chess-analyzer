export type ApiErrorPayload = { error?: string; message?: string };

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiNetworkError extends Error {
  constructor(message = "Backend is unavailable", options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiNetworkError";
  }
}

export function importErrorMessage(error: unknown): string {
  if (error instanceof ApiNetworkError) return "Backend недоступен";
  if (error instanceof ApiError) {
    if (error.code === "chesscom_user_not_found" || error.status === 404) {
      return "Пользователь Chess.com не найден";
    }
    if (error.code === "chesscom_unavailable" || error.status === 502 || error.status === 503) {
      return "Chess.com временно недоступен";
    }
    if (error.status === 422) return "Проверьте username и попробуйте снова";
  }
  return "Не удалось импортировать партии";
}
