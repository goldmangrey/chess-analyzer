import type { ReactNode } from "react";

import { TopNavigation } from "./top-navigation";

export type AppShellProps = {
  children: ReactNode;
  activeSection?: "dashboard" | "games";
};

export function AppShell({ children, activeSection }: AppShellProps) {
  return (
    <div className="ambient-gradient relative min-h-screen overflow-x-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-72" />
      <div className="relative mx-auto w-full max-w-[1440px] px-4 sm:px-7 lg:px-10">
        <TopNavigation activeSection={activeSection} />
        <main className="py-10 sm:py-14 lg:py-16">{children}</main>
      </div>
    </div>
  );
}
