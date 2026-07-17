import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BentoCardTone =
  | "default"
  | "muted"
  | "dark"
  | "mint"
  | "lime"
  | "yellow";

export type BentoCardProps = {
  children: ReactNode;
  className?: string;
  tone?: BentoCardTone;
  as?: "div" | "section" | "article";
  id?: string;
};

const toneClasses: Record<BentoCardTone, string> = {
  default: "bento-card",
  muted: "bento-card-muted",
  dark: "bento-card-dark",
  mint: "bento-card border-[var(--mint)] bg-mint-surface",
  lime: "bento-card border-[var(--lime)] bg-lime-surface",
  yellow: "bento-card border-[var(--warm-yellow)] bg-yellow-surface",
};

export function BentoCard({
  children,
  className,
  tone = "default",
  as: Component = "div",
  id,
}: BentoCardProps) {
  return (
    <Component id={id} className={cn(toneClasses[tone], className)}>{children}</Component>
  );
}
