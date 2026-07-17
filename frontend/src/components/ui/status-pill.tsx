import type { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type StatusPillTone =
  | "neutral"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "dark";

export type StatusPillProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: StatusPillTone;
  dot?: boolean;
};

const toneClasses: Record<StatusPillTone, string> = {
  neutral: "bg-black/[0.055] text-text-secondary",
  success: "bg-best-surface text-best",
  warning: "bg-inaccuracy-surface text-[#856913]",
  danger: "bg-blunder-surface text-[#a43d3d]",
  info: "bg-mint-surface text-forest-light",
  dark: "bg-surface-dark text-text-on-dark",
};

const dotClasses: Record<StatusPillTone, string> = {
  neutral: "bg-text-muted",
  success: "bg-best",
  warning: "bg-inaccuracy",
  danger: "bg-blunder",
  info: "bg-forest-light",
  dark: "bg-lime",
};

export function StatusPill({
  children,
  className,
  tone = "neutral",
  dot = false,
  ...props
}: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {dot ? (
        <span
          aria-hidden="true"
          className={cn("size-1.5 rounded-full", dotClasses[tone])}
        />
      ) : null}
      {children}
    </span>
  );
}
