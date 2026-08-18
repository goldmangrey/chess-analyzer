"use client";

import { useState } from "react";

import { BentoGrid, BentoGridItem } from "@/components/layout";
import { fetchAppSettings, fetchDashboard, fetchGames } from "@/lib/api";
import type { AppSettings, StatisticsDashboard, SystemStatus } from "@/lib/api/types";
import { useBackgroundPolling } from "@/hooks/use-background-polling";
import { DASHBOARD_POLL_INTERVAL_MS } from "@/lib/polling";

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
  const [liveData, setLiveData] = useState(data);
  const [liveSettings, setLiveSettings] = useState(settings);
  const [dashboardLoadError, setDashboardLoadError] = useState(false);

  const { isRefreshing } = useBackgroundPolling({
    intervalMs: DASHBOARD_POLL_INTERVAL_MS,
    fetcher: async (signal) => Promise.allSettled([
      fetchDashboard(signal),
      fetchAppSettings(signal),
      fetchGames({ limit: 20, sort: "newest" }, signal),
    ]),
    onSuccess: ([dashboardResult, settingsResult, gamesResult]) => {
      setDashboardLoadError(dashboardResult.status === "rejected");
      if (dashboardResult.status === "fulfilled") {
        const statuses = new Map(
          gamesResult.status === "fulfilled"
            ? gamesResult.value.items.map((game) => [game.id, game.analysis_status])
            : [],
        );
        setLiveData({
          ...dashboardResult.value,
          recent_games: dashboardResult.value.recent_games.map((game) => ({
            ...game,
            analysis_status: statuses.get(game.game_id) ?? game.analysis_status,
          })),
        });
      }
      if (settingsResult.status === "fulfilled") setLiveSettings(settingsResult.value);
    },
  });

  const { summary, comparison, trends, weakest_openings, recent_games } = liveData;
  const refreshStatus = <div aria-live="polite" className="mb-3 min-h-4 text-right text-xs text-text-muted">{isRefreshing ? "Обновляем данные…" : dashboardLoadError ? <span className="text-mistake">Не удалось обновить статистику. Показаны последние загруженные данные.</span> : ""}</div>;
  if (summary.total_games === 0) {
    return <>{refreshStatus}<SystemDiagnosticCard status={systemStatus} />
      <BentoGrid>
        <BentoGridItem className="md:col-span-6 xl:col-span-8"><WelcomeCard summary={summary} comparison={comparison} /></BentoGridItem>
        <BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={liveSettings} /></BentoGridItem>
        <BentoGridItem className="md:col-span-6 xl:col-span-12"><EmptyDashboard /></BentoGridItem>
      </BentoGrid>
    </>;
  }

  return <>{refreshStatus}<SystemDiagnosticCard status={systemStatus} />
    <BentoGrid>
      <BentoGridItem className="md:col-span-6 xl:col-span-8"><WelcomeCard summary={summary} comparison={comparison} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={liveSettings} /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-5"><PrimaryMetricCard summary={summary} comparison={comparison} /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-4"><AnalyzedGamesCard analyzed={summary.analyzed_games} total={summary.total_games} /></BentoGridItem>
      <BentoGridItem className="md:col-span-3 xl:col-span-3"><BlunderFreeCard percentage={summary.blunder_free_percentage} games={summary.blunder_free_games} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-8"><PerformanceChart trends={trends} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-4"><WeakestOpeningsCard openings={weakest_openings} /></BentoGridItem>
      <BentoGridItem className="md:col-span-6 xl:col-span-12"><RecentGamesCard games={recent_games} /></BentoGridItem>
    </BentoGrid>
  </>;
}
