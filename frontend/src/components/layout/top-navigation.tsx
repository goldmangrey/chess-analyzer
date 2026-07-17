import Link from "next/link";

import { EngineStatus, type EngineStatusProps } from "./engine-status";
import { Logo } from "./logo";

export type TopNavigationProps = {
  activeSection?: "dashboard" | "games";
  engineStatus?: EngineStatusProps["status"];
};

const links = [
  { section: "dashboard" as const, href: "/", label: "Главная" },
  { section: "games" as const, href: "/games", label: "Партии" },
];

export function TopNavigation({
  activeSection,
  engineStatus = "ready",
}: TopNavigationProps) {
  return (
    <header className="relative z-10 pt-4 sm:pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.5rem] border border-white/70 bg-white/75 p-2.5 shadow-[var(--shadow-soft)] backdrop-blur-xl sm:flex-nowrap sm:rounded-full sm:px-3">
        <Logo />
        <nav
          aria-label="Основная навигация"
          className="order-3 flex w-full items-center rounded-full bg-black/[0.04] p-1 sm:order-none sm:w-auto"
        >
          {links.map((link) => {
            const active = activeSection === link.section;
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "focus-ring flex-1 rounded-full bg-surface-dark px-4 py-2 text-center text-sm font-semibold text-text-on-dark shadow-[var(--shadow-soft)] sm:flex-none"
                    : "focus-ring flex-1 rounded-full px-4 py-2 text-center text-sm font-semibold text-text-secondary transition hover:bg-white/80 hover:text-text-primary sm:flex-none"
                }
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <EngineStatus status={engineStatus} />
      </div>
    </header>
  );
}
