export type DateTimeFormatOptions = {
  locale?: string | string[];
  timeZone?: string;
  includeDate?: boolean;
};

export function parseUtcTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatBrowserDateTime(
  value: string | null | undefined,
  { locale, timeZone, includeDate = true }: DateTimeFormatOptions = {},
): string {
  const date = parseUtcTimestamp(value);
  if (!date) return value ? "Дата неизвестна" : "Ещё не выполнялась";
  return new Intl.DateTimeFormat(locale, {
    ...(includeDate ? { day: "numeric", month: "short", year: "numeric" } : {}),
    hour: "2-digit",
    minute: "2-digit",
    timeZone,
  }).format(date);
}

export function formatBrowserDate(
  value: string | null | undefined,
  { locale, timeZone }: Omit<DateTimeFormatOptions, "includeDate"> = {},
): string {
  const date = parseUtcTimestamp(value);
  if (!date) return "Дата неизвестна";
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone,
  }).format(date);
}
