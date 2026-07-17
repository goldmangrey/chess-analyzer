import { useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "prefix"> & {
  label: string;
  hint?: string;
  error?: string;
  prefix?: ReactNode;
  suffix?: ReactNode;
};

export function Input({
  label,
  hint,
  error,
  prefix,
  suffix,
  id,
  className,
  ...props
}: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = hint || error ? `${inputId}-description` : undefined;

  return (
    <div className="w-full">
      <label htmlFor={inputId} className="text-sm font-semibold text-text-primary">
        {label}
      </label>
      <div
        className={cn(
          "mt-2 flex min-h-12 items-center rounded-[1.05rem] border bg-surface px-4 transition focus-within:border-forest-light focus-within:ring-3 focus-within:ring-mint",
          error ? "border-blunder" : "border-[var(--border-strong)]",
        )}
      >
        {prefix ? <span className="mr-2 text-text-muted">{prefix}</span> : null}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={descriptionId}
          className={cn(
            "min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-50",
            className,
          )}
          {...props}
        />
        {suffix ? <span className="ml-2 text-text-muted">{suffix}</span> : null}
      </div>
      {descriptionId ? (
        <p
          id={descriptionId}
          className={cn(
            "mt-2 text-xs leading-5",
            error ? "text-blunder" : "text-text-muted",
          )}
        >
          {error ?? hint}
        </p>
      ) : null}
    </div>
  );
}
