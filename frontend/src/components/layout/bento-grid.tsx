import type { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export function BentoGrid({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("grid grid-cols-1 gap-5 md:grid-cols-6 xl:grid-cols-12", className)} {...props} />;
}

export function BentoGridItem({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("min-w-0 md:col-span-3 xl:col-span-6", className)} {...props} />;
}
