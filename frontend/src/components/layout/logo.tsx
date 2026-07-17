import Link from "next/link";

export function Logo() {
  return (
    <Link
      href="/"
      className="focus-ring inline-flex items-center gap-2.5 rounded-xl text-text-primary"
      aria-label="Chess AI Teacher — на главную"
    >
      <span
        aria-hidden="true"
        className="grid size-9 grid-cols-2 overflow-hidden rounded-xl bg-surface-dark p-1.5 shadow-[var(--shadow-soft)]"
      >
        <span className="rounded-sm bg-lime" />
        <span />
        <span />
        <span className="rounded-sm bg-mint" />
      </span>
      <span className="text-sm font-extrabold leading-tight tracking-[-0.035em] sm:text-base">
        Chess AI Teacher
      </span>
    </Link>
  );
}
