import { cn } from "@/lib/cn";

export type SpinnerProps = {
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizes = { sm: "size-4 border-2", md: "size-6 border-2", lg: "size-9 border-3" };

export function Spinner({ size = "md", className }: SpinnerProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-block animate-spin rounded-full border-current border-r-transparent motion-reduce:animate-none",
        sizes[size],
        className,
      )}
    />
  );
}
