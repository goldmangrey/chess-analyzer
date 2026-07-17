import {
  forwardRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "dark";
export type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-forest text-white shadow-[var(--shadow-accent)] hover:bg-forest-light",
  secondary:
    "border border-[var(--border-strong)] bg-white text-text-primary hover:bg-surface-muted",
  ghost: "bg-transparent text-text-secondary hover:bg-black/[0.045]",
  dark: "bg-surface-dark text-text-on-dark hover:bg-surface-dark-elevated",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "min-h-9 px-4 text-sm",
  md: "min-h-11 px-5 text-sm",
  lg: "min-h-12 px-6 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      className,
      variant = "primary",
      size = "md",
      type = "button",
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={cn(
          "focus-ring inline-flex items-center justify-center rounded-full font-semibold transition duration-200 ease-out active:translate-y-px disabled:pointer-events-none disabled:opacity-45",
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        <span className="relative inline-flex items-center justify-center gap-2">
          {loading ? (
            <span
              aria-hidden="true"
              className="absolute right-full mr-2 size-4 animate-spin rounded-full border-2 border-current border-r-transparent motion-reduce:animate-none"
            />
          ) : leftIcon ? (
            <span aria-hidden="true" className="shrink-0">
              {leftIcon}
            </span>
          ) : null}
          <span>{children}</span>
          {!loading && rightIcon ? (
            <span aria-hidden="true" className="shrink-0">
              {rightIcon}
            </span>
          ) : null}
        </span>
      </button>
    );
  },
);
