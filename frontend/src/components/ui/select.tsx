import { useId, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type SelectOption = { label: string; value: string };

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  hint?: string;
  error?: string;
  options: readonly SelectOption[];
  placeholder?: string;
};

export function Select({
  label,
  hint,
  error,
  options,
  placeholder,
  id,
  className,
  ...props
}: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const descriptionId = hint || error ? `${selectId}-description` : undefined;

  return (
    <div className="w-full">
      <label htmlFor={selectId} className="text-sm font-semibold text-text-primary">
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={descriptionId}
        className={cn(
          "select-chevron focus-ring mt-2 min-h-12 w-full appearance-none rounded-[1.05rem] border bg-surface px-4 pr-10 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-50",
          error ? "border-blunder" : "border-[var(--border-strong)]",
          className,
        )}
        {...props}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {descriptionId ? (
        <p
          id={descriptionId}
          className={cn("mt-2 text-xs", error ? "text-blunder" : "text-text-muted")}
        >
          {error ?? hint}
        </p>
      ) : null}
    </div>
  );
}
