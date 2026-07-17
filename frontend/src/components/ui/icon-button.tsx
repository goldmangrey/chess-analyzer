import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  variant?: "default" | "ghost" | "dark";
  size?: "sm" | "md" | "lg";
};

const variants = {
  default:
    "border border-[var(--border-subtle)] bg-surface text-text-primary shadow-[var(--shadow-soft)] hover:bg-surface-muted",
  ghost: "bg-transparent text-text-secondary hover:bg-black/[0.05]",
  dark: "bg-surface-dark text-text-on-dark hover:bg-surface-dark-elevated",
};

const sizes = { sm: "size-9", md: "size-11", lg: "size-12" };

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton(
    {
      label,
      variant = "default",
      size = "md",
      className,
      type = "button",
      children,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        aria-label={label}
        className={cn(
          "focus-ring inline-flex shrink-0 items-center justify-center rounded-2xl transition active:translate-y-px disabled:pointer-events-none disabled:opacity-45",
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      >
        {children}
      </button>
    );
  },
);
