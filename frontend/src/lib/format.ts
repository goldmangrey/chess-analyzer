const numberFormatter = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });
const oneDecimalFormatter = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const dateTimeFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function formatMetric(value: number | null | undefined, digits = 1): string {
  if (!isFiniteNumber(value)) return "—";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: digits }).format(value);
}

export function formatPercentage(value: number | null | undefined): string {
  return isFiniteNumber(value) ? `${oneDecimalFormatter.format(value)}%` : "—";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Дата неизвестна";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Дата неизвестна" : dateFormatter.format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Ещё не выполнялась";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Дата неизвестна" : dateTimeFormatter.format(date);
}

export function formatRelativeDate(
  value: string | null | undefined,
  reference: string | Date,
): string {
  if (!value) return "Дата неизвестна";
  const date = new Date(value);
  const referenceDate = new Date(reference);
  if (Number.isNaN(date.getTime()) || Number.isNaN(referenceDate.getTime())) return "Дата неизвестна";
  const days = Math.round((date.getTime() - referenceDate.getTime()) / 86_400_000);
  if (Math.abs(days) > 6) return formatDate(value);
  return new Intl.RelativeTimeFormat("ru-RU", { numeric: "auto" }).format(days, "day");
}

export function formatCompactMetric(value: number | null | undefined): string {
  return isFiniteNumber(value) ? numberFormatter.format(value) : "—";
}

export function formatEvaluation(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return "—";
  if (value >= 100_000) return "+#";
  if (value <= -100_000) return "-#";
  const pawns = value / 100;
  return `${pawns >= 0 ? "+" : ""}${pawns.toFixed(2)}`;
}

export function formatColor(color: "white" | "black"): string {
  return color === "white" ? "белые" : "чёрные";
}

export function formatMoveLabel(move: { move_number: number; player_color: "white" | "black"; played_move_san: string | null; played_move_uci: string }): string {
  return `${move.move_number}${move.player_color === "black" ? "..." : "."} ${move.played_move_san ?? move.played_move_uci}`;
}
