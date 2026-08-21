"use client";

import { useState } from "react";

import { BentoGrid, BentoGridItem } from "@/components/layout";
import { fetchAppSettings, fetchDashboard, fetchGames, fetchPlayerIntelligence } from "@/lib/api";
import type { AppSettings, PlayerIntelligenceResponse, StatisticsDashboard, SystemStatus } from "@/lib/api/types";
import { buildDashboardViewModel } from "@/lib/dashboard-view-model";
import { useBackgroundPolling } from "@/hooks/use-background-polling";
import { DASHBOARD_POLL_INTERVAL_MS } from "@/lib/polling";

import { DashboardTierOne, OpeningFoundation, RecurringMistakesFoundation, SegmentFoundation } from "./dashboard-intelligence-foundation";
import { ImportCard } from "./import-card";
import { ProgressComparison } from "./progress-comparison";
import { ChessProfileHeroUnavailable } from "./chess-profile-hero";
import { RecentGamesCard } from "./recent-games-card";
import { EmptyDashboard } from "./empty-dashboard";
import { SystemDiagnosticCard } from "./system-diagnostic-card";

export function DashboardPage({ data, intelligence, systemStatus, settings }: { data: StatisticsDashboard; intelligence: PlayerIntelligenceResponse | null; systemStatus: SystemStatus; settings: AppSettings }) {
  const [liveData, setLiveData] = useState(data);
  const [liveIntelligence, setLiveIntelligence] = useState<PlayerIntelligenceResponse | null>(intelligence);
  const [liveSettings, setLiveSettings] = useState(settings);
  const [dashboardLoadError, setDashboardLoadError] = useState(false);

  const { isRefreshing } = useBackgroundPolling({
    intervalMs: DASHBOARD_POLL_INTERVAL_MS,
    fetcher: async (signal) => Promise.allSettled([
      fetchDashboard(signal),
      fetchPlayerIntelligence(30, signal),
      fetchAppSettings(signal),
      fetchGames({ limit: 20, sort: "newest" }, signal),
    ]),
    onSuccess: ([dashboardResult, intelligenceResult, settingsResult, gamesResult]) => {
      setDashboardLoadError(dashboardResult.status === "rejected" || intelligenceResult.status === "rejected");
      if (intelligenceResult.status === "fulfilled") setLiveIntelligence(intelligenceResult.value);
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

  const { summary, recent_games } = liveData;
  const model = liveIntelligence ? buildDashboardViewModel(liveIntelligence, liveSettings) : null;
  const refreshStatus = <div aria-live="polite" className="mb-3 min-h-4 text-right text-xs text-text-muted">{isRefreshing ? "Обновляем данные…" : dashboardLoadError ? <span className="text-mistake">Не удалось обновить статистику. Показаны последние загруженные данные.</span> : ""}</div>;
  if (summary.total_games === 0) {
    return <>{refreshStatus}<SystemDiagnosticCard status={systemStatus} />
      <BentoGrid>
        <BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={liveSettings} /></BentoGridItem>
        <BentoGridItem className="md:col-span-6 xl:col-span-12"><EmptyDashboard /></BentoGridItem>
      </BentoGrid>
    </>;
  }

  if (!model || !liveIntelligence) {
    return <>{refreshStatus}<SystemDiagnosticCard status={systemStatus} /><div className="space-y-4"><ChessProfileHeroUnavailable /><BentoGrid><BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={liveSettings} /></BentoGridItem><BentoGridItem className="md:col-span-6 xl:col-span-8"><RecentGamesCard games={recent_games} /></BentoGridItem></BentoGrid></div></>;
  }

  return <>{refreshStatus}<SystemDiagnosticCard status={systemStatus} />
    <div className="space-y-4">
      <DashboardTierOne model={model} />
      <section data-dashboard-tier="2" aria-label="Повторяющиеся ошибки и прогресс"><BentoGrid className="gap-4"><BentoGridItem className="md:col-span-3 xl:col-span-5"><RecurringMistakesFoundation model={model} /></BentoGridItem><BentoGridItem className="md:col-span-3 xl:col-span-7"><ProgressComparison progress={model.progress} /></BentoGridItem></BentoGrid></section>
      <section data-dashboard-tier="3" aria-label="Дебюты, сегменты и партии" className="space-y-4"><BentoGrid className="gap-4"><BentoGridItem className="md:col-span-3 xl:col-span-7"><OpeningFoundation model={model} /></BentoGridItem><BentoGridItem className="md:col-span-3 xl:col-span-5"><SegmentFoundation model={model} /></BentoGridItem><BentoGridItem className="md:col-span-6 xl:col-span-4"><ImportCard settings={liveSettings} /></BentoGridItem></BentoGrid><RecentGamesCard games={recent_games} /></section>
    </div>
  </>;
}
