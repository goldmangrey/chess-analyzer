import { DashboardSkeleton } from "@/components/dashboard";
import { AppShell } from "@/components/layout";

export default function Loading() {
  return <AppShell activeSection="dashboard"><DashboardSkeleton /></AppShell>;
}
