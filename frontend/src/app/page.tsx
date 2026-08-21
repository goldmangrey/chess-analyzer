import type { Metadata } from "next";

import { DashboardError, DashboardPage } from "@/components/dashboard";
import { AppShell } from "@/components/layout";
import { ApiNetworkError, fetchAppSettings, fetchDashboard, fetchPlayerIntelligence, fetchSystemStatus } from "@/lib/api";

export const metadata: Metadata = { title: "Chess AI Teacher — Dashboard" };
export const dynamic = "force-dynamic";

async function loadDashboard() {
  const [dashboard, intelligence, systemStatus, settings] = await Promise.allSettled([
    fetchDashboard(),
    fetchPlayerIntelligence(30),
    fetchSystemStatus(),
    fetchAppSettings(),
  ]);
  return { dashboard, intelligence, systemStatus, settings };
}

export default async function Home() {
  const result = await loadDashboard();
  const engineStatus = result.systemStatus.status === "fulfilled"
    ? result.systemStatus.value.status
    : "unavailable";
  if (result.dashboard.status === "rejected") {
    const reason = result.dashboard.reason;
    return <AppShell activeSection="dashboard" engineStatus={engineStatus}>
      <DashboardError
        kind={reason instanceof ApiNetworkError ? "network" : "dashboard"}
        settings={result.settings.status === "fulfilled" ? result.settings.value : null}
      />
    </AppShell>;
  }
  if (result.systemStatus.status === "rejected" || result.settings.status === "rejected") {
    return <AppShell activeSection="dashboard" engineStatus={engineStatus}>
      <DashboardError kind="network" settings={null} />
    </AppShell>;
  }
  return <AppShell activeSection="dashboard" engineStatus={engineStatus}><DashboardPage key={result.settings.value.last_sync_completed_at ?? "never"} data={result.dashboard.value} intelligence={result.intelligence.status === "fulfilled" ? result.intelligence.value : null} systemStatus={result.systemStatus.value} settings={result.settings.value} /></AppShell>;
}
