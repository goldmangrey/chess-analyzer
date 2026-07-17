import type { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type SeparatorProps = HTMLAttributes<HTMLDivElement> & {
  orientation?: "horizontal" | "vertical";
};

export function Separator({
  orientation = "horizontal",
  className,
  ...props
}: SeparatorProps) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={cn(
        "shrink-0 bg-[var(--border-subtle)]",
        orientation === "horizontal" ? "h-px w-full" : "h-full min-h-6 w-px",
        className,
      )}
      {...props}
    />
  );
}
