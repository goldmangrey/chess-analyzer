import type { ReactNode } from "react";

export type PageHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function PageHeading({ eyebrow, title, description, action }: PageHeadingProps) {
  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? (
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="mt-2 text-[clamp(2.5rem,7vw,5.5rem)] font-semibold leading-[0.96] tracking-[-0.06em] text-text-primary">
          {title}
        </h1>
        {description ? (
          <p className="mt-5 max-w-2xl text-base leading-7 text-text-secondary sm:text-lg">
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
