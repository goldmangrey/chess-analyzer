import type { ReactNode } from "react";

export type SectionHeadingProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function SectionHeading({ title, description, action }: SectionHeadingProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-[-0.04em] text-text-primary sm:text-3xl">
          {title}
        </h2>
        {description ? <p className="mt-2 text-sm leading-6 text-text-secondary">{description}</p> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  );
}
