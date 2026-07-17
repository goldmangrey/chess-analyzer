import { BentoGrid, BentoGridItem } from "@/components/layout";
import type { AppSettings, StatisticsDashboard, SystemStatus } from "@/lib/api/types";

import { AnalyzedGamesCard } from "./analyzed-games-card";
import { BlunderFreeCard } from "./blunder-free-card";
import { ImportCard } from "./import-card";
import { PerformanceChart } from "./performance-chart";
import { PrimaryMetricCard } from "./primary-metric-card";
import { RecentGamesCard } from "./recent-games-card";
import { WeakestOpeningsCard } from "./weakest-openings-card";
import { WelcomeCard } from "./welcome-card";
import { EmptyDashboard } from "./empty-dashboard";
import { SystemDiagnosticCard } from "./system-diagnostic-card";

export function DashboardPage({ data, systemStatus, settings }: { data: StatisticsDashboard; systemStatus: SystemStatus; settings: AppSettings }) {
  const { summary, comparison, trends, weakest_openings, recent_games } = data;
  if (summary.total_games === 0) {
    return <><SystemDiagnosticCard status={systemStatus} />
      <BentoGrid>
        <BentoGridItem className="md:col-span-6 xl:col-span-8"><WelcomeCard summary={summary} comparison={comparison} /></BentoGridItem>
        <BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={settings} /></BentoGridItem>
        <BentoGridItem className="md:col-span-6 xl:col-span-12"><EmptyDashboard /></BentoGridItem>
      </BentoGrid>
    </>;
  }

  return <><SystemDiagnosticCard status={systemStatus} />
    <BentoGrid>
      <BentoGridItem className="md:col-span-6 xl:col-span-8"><WelcomeCard summary={summary} comparison={comparison} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={settings} /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-5"><PrimaryMetricCard summary={summary} comparison={comparison} /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-4"><AnalyzedGamesCard analyzed={summary.analyzed_games} total={summary.total_games} /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-3"><BlunderFreeCard percentage={summary.blunder_free_percentage} games={summary.blunder_free_games} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-8"><PerformanceChart trends={trends} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-4"><WeakestOpeningsCard openings={weakest_openings} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-12"><RecentGamesCard games={recent_games} /></BentoGridItem>
    </BentoGrid>
  </>;
}
