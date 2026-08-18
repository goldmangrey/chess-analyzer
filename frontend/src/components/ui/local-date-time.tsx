"use client";

import { useSyncExternalStore } from "react";

import { formatBrowserDate, formatBrowserDateTime } from "@/lib/date-time";

type LocalDateTimeProps = {
  value: string | null | undefined;
  dateOnly?: boolean;
  fallback?: string;
  className?: string;
};

export function LocalDateTime({ value, dateOnly = false, fallback, className }: LocalDateTimeProps) {
  const mounted = useSyncExternalStore(() => () => undefined, () => true, () => false);
  const serverSafeText = fallback ?? (value ? "—" : dateOnly ? "Дата неизвестна" : "Ещё не выполнялась");
  const text = mounted ? (dateOnly ? formatBrowserDate(value) : formatBrowserDateTime(value)) : serverSafeText;
  return <time className={className} dateTime={value ?? undefined}>{text}</time>;
}
