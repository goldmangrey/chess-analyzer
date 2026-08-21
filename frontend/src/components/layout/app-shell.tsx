import type { ReactNode } from "react";

import { TopNavigation } from "./top-navigation";
import type { EngineStatus } from "./engine-status";

export type AppShellProps = {
  children: ReactNode;
  activeSection?: "dashboard" | "games";
  engineStatus?: EngineStatus;
};

export function AppShell({ children, activeSection, engineStatus }: AppShellProps) {
  return (
    <div className="ambient-gradient relative min-h-screen overflow-x-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-72" />
      <div className="relative mx-auto w-full max-w-[1440px] px-4 sm:px-7 lg:px-10">
        <TopNavigation activeSection={activeSection} engineStatus={engineStatus} />
        <main className="py-6 sm:py-8 lg:py-10">{children}</main>
      </div>
    </div>
  );
}
