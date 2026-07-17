import { useId, type ReactElement } from "react";

export type TooltipProps = {
  content: string;
  children: ReactElement;
};

export function Tooltip({ content, children }: TooltipProps) {
  const tooltipId = useId();

  return (
    <span
      className="group/tooltip relative inline-flex"
      tabIndex={0}
      aria-describedby={tooltipId}
    >
      {children}
      <span
        id={tooltipId}
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-max max-w-56 -translate-x-1/2 rounded-xl bg-surface-dark px-3 py-2 text-center text-xs leading-5 text-text-on-dark opacity-0 shadow-[var(--shadow-soft)] transition group-hover/tooltip:opacity-100 group-focus-visible/tooltip:opacity-100"
      >
        {content}
      </span>
    </span>
  );
}
