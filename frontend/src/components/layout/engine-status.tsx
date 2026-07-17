import { cn } from "@/lib/cn";

export type EngineStatus = "ready" | "unavailable" | "analyzing";
export type EngineStatusProps = { status?: EngineStatus };

const content = {
  ready: { label: "Локальный backend готов", compact: "Backend готов", dot: "bg-best" },
  analyzing: { label: "Backend обрабатывает задачу", compact: "В работе", dot: "bg-inaccuracy" },
  unavailable: { label: "Backend недоступен", compact: "Нет backend", dot: "bg-blunder" },
};

export function EngineStatus({ status = "ready" }: EngineStatusProps) {
  const current = content[status];
  return (
    <span
      title={current.label}
      className="inline-flex min-h-9 items-center gap-2 rounded-full bg-surface px-3 text-xs font-semibold text-text-secondary shadow-[var(--shadow-soft)]"
    >
      <span aria-hidden="true" className={cn("size-2 rounded-full", current.dot)} />
      <span className="hidden sm:inline">{current.label}</span>
      <span className="sm:hidden">{current.compact}</span>
    </span>
  );
}
