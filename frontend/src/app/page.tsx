import type { Metadata } from "next";

import { DashboardError, DashboardPage } from "@/components/dashboard";
import { AppShell } from "@/components/layout";
import { fetchAppSettings, fetchDashboard, fetchSystemStatus } from "@/lib/api";

export const metadata: Metadata = { title: "Chess AI Teacher — Dashboard" };
export const dynamic = "force-dynamic";

async function loadDashboard() {
  try {
    const [data, systemStatus, settings] = await Promise.all([fetchDashboard(), fetchSystemStatus(), fetchAppSettings()]);
    return { data, systemStatus, settings, available: true } as const;
  } catch {
    return { data: null, systemStatus: null, settings: null, available: false } as const;
  }
}

export default async function Home() {
  const result = await loadDashboard();
  if (!result.available) {
    return <AppShell activeSection="dashboard" engineStatus="unavailable"><DashboardError /></AppShell>;
  }
  return <AppShell activeSection="dashboard" engineStatus={result.systemStatus.status}><DashboardPage data={result.data} systemStatus={result.systemStatus} settings={result.settings} /></AppShell>;
}
