import { cn } from "@/lib/cn";

export type SkeletonProps = {
  className?: string;
  rounded?: "sm" | "md" | "lg" | "full";
};

const roundedClasses = {
  sm: "rounded-lg",
  md: "rounded-2xl",
  lg: "rounded-[1.5rem]",
  full: "rounded-full",
};

export function Skeleton({ className, rounded = "md" }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={cn("skeleton block", roundedClasses[rounded], className)}
    />
  );
}
