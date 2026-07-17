import { GamesSkeleton } from "@/components/games";
import { AppShell } from "@/components/layout";

export default function Loading() {
  return <AppShell activeSection="games"><GamesSkeleton /></AppShell>;
}
