import { AnalysisSkeleton } from "@/components/analysis";
import { AppShell } from "@/components/layout";

export default function Loading() {
  return <AppShell activeSection="games"><AnalysisSkeleton /></AppShell>;
}
