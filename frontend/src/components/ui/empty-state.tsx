import type { ReactNode } from "react";

export type EmptyStateProps = {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
};

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <section className="rounded-[1.75rem] bg-surface-muted px-5 py-10 text-center sm:px-8 sm:py-14">
      {icon ? (
        <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-mint-surface text-forest">
          {icon}
        </div>
      ) : null}
      <h2 className="mt-5 text-xl font-semibold tracking-[-0.035em] text-text-primary">
        {title}
      </h2>
      {description ? (
        <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-text-secondary">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-6 flex justify-center">{action}</div> : null}
    </section>
  );
}
