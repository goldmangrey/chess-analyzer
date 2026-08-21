import type { AccuracyQualityBand } from "./api/types";

const bandLabels: Record<AccuracyQualityBand, string> = {
  excellent: "Отличная", good: "Хорошая", fair: "Средняя", poor: "Низкая",
};

const shortBandLabels: Record<AccuracyQualityBand, string> = {
  excellent: "Отлично", good: "Хорошо", fair: "Средне", poor: "Слабо",
};

export function formatAccuracy(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}%` : "—";
}

export function formatWinPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}%` : "—";
}

export function formatPercentagePointChange(value: number | null | undefined): string | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  const rounded = Math.sign(value) * Math.round(Math.abs(value) * 10) / 10;
  const formatted = Math.abs(rounded).toLocaleString("ru-RU", { maximumFractionDigits: 1 });
  return `${rounded > 0 ? "+" : rounded < 0 ? "−" : ""}${formatted} п.п.`;
}

export function accuracyQualityLabel(value: AccuracyQualityBand | null | undefined): string | null {
  return value ? bandLabels[value] : null;
}

export function accuracyQualityShortLabel(value: AccuracyQualityBand | null | undefined): string | null {
  return value ? shortBandLabels[value] : null;
}
