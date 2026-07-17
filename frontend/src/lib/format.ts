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

export function formatCpLoss(value: number | null | undefined): string {
  return isFiniteNumber(value) ? oneDecimalFormatter.format(value) : "—";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Дата неизвестна";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Дата неизвестна" : dateFormatter.format(date);
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
