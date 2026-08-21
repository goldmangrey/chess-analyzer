import Link from "next/link";

import { PageHeading } from "@/components/layout";
import { BentoCard, EmptyState, ToastProvider } from "@/components/ui";
import type { GamesListResponse } from "@/lib/api/types";
import type { GamesUrlState } from "@/lib/games-query";

import { GameCardList } from "./game-card-list";
import { GamesPagination } from "./games-pagination";
import { GamesRefreshButton } from "./games-refresh-button";
import { GamesTable } from "./games-table";
import { GamesToolbar } from "./games-toolbar";

export function GamesPage({ data, state }: { data: GamesListResponse; state: GamesUrlState }) {
  const hasFiltering = Boolean(state.opening || state.result || state.status);
  return (
    <ToastProvider>
      <PageHeading
        eyebrow="История партий"
        title="Ваши партии"
        description={`${data.total} ${data.total === 1 ? "партия" : "партий"} по текущему запросу`}
        action={<div className="flex flex-wrap gap-3"><GamesRefreshButton /><Link href="/#import" className="focus-ring inline-flex min-h-11 items-center rounded-full bg-forest px-5 text-sm font-semibold text-white shadow-[var(--shadow-accent)] hover:bg-forest-light">Импортировать партии</Link></div>}
      />
      <div className="mt-8"><GamesToolbar key={`${state.opening ?? ""}-${state.result ?? ""}-${state.status ?? ""}-${state.sort}-${state.limit}`} state={state} /></div>
      {data.items.length === 0 ? (
        <div className="mt-6">
          {hasFiltering ? (
            <EmptyState title="По выбранным фильтрам партий нет" description="Измените параметры поиска или вернитесь к полной истории." action={<Link href="/games" className="focus-ring rounded-full bg-surface-dark px-5 py-3 text-sm font-semibold text-white">Сбросить фильтры</Link>} />
          ) : (
            <EmptyState title="Партий пока нет" description="Импортируйте последние партии с Chess.com на главной странице." action={<Link href="/#import" className="focus-ring rounded-full bg-forest px-5 py-3 text-sm font-semibold text-white">Перейти к импорту</Link>} />
          )}
        </div>
      ) : (
        <div id="games-list" className="mt-6 scroll-mt-6"><BentoCard className="p-3 sm:p-5"><GamesTable games={data.items} /><GameCardList games={data.items} /></BentoCard><GamesPagination total={data.total} limit={data.limit} offset={data.offset} /></div>
      )}
    </ToastProvider>
  );
}
