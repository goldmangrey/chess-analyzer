import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { BentoCard } from "@/components/ui";
import type { DashboardProfileHeroViewModel } from "@/lib/dashboard-view-model";
import { formatAccuracy } from "@/lib/human-metrics";

const trendIcons = {
  improving: ArrowUpRight,
  worsening: ArrowDownRight,
  stable: Minus,
  mixed: Minus,
  insufficient: Minus,
} as const;

const trendTones = {
  improving: "text-best",
  worsening: "text-mistake",
  stable: "text-forest",
  mixed: "text-text-secondary",
  insufficient: "text-text-muted",
} as const;

export function ChessProfileHero({ hero }: { hero: DashboardProfileHeroViewModel }) {
  const TrendIcon = trendIcons[hero.trend.direction];
  if (!hero.hasData) {
    return <BentoCard as="section" aria-labelledby="profile-title" data-testid="chess-profile-hero" className="p-4 sm:p-5"><p className="text-xs font-semibold text-forest-light">Шахматный профиль</p><h1 id="profile-title" className="mt-1 text-xl font-semibold tracking-[-0.035em]">{hero.username ?? "Ваш профиль"}</h1><p className="mt-3 text-sm text-text-secondary">Недостаточно партий для профиля</p></BentoCard>;
  }

  return <BentoCard as="section" aria-labelledby="profile-title" data-testid="chess-profile-hero" className="overflow-hidden p-0">
    <div className="grid gap-4 p-4 sm:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] sm:items-center sm:p-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.9fr)_minmax(0,1fr)]">
      <div className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1"><h1 id="profile-title" className="text-lg font-semibold tracking-[-0.035em] sm:text-xl">Шахматный профиль</h1><span className="truncate text-xs text-text-muted">{hero.username ? `@${hero.username}` : "Ваш профиль"}</span></div>
        <p className="mt-1 text-xs text-text-muted">Последние {hero.sampleGames} партий · {hero.userMoves} ходов</p>
        <div className="mt-3 flex items-end gap-3"><p className="technical-number text-[2.35rem] font-semibold leading-none tracking-[-0.055em] text-text-primary">{formatAccuracy(hero.accuracy)}</p><div className="pb-0.5"><p className="text-sm font-semibold">Точность</p>{hero.qualityLabel ? <p className="mt-0.5 text-xs text-forest-light">{hero.qualityLabel}</p> : null}</div></div>
      </div>

      <div className="min-w-0 border-t border-[var(--border-subtle)] pt-3 sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0 lg:px-5">
        <p className="text-xs text-text-muted">Результаты</p>
        <dl className="mt-2 grid grid-cols-3 gap-2 text-center sm:text-left"><div><dt className="text-[11px] text-text-muted">Победы</dt><dd className="technical-number mt-0.5 text-lg font-semibold">{hero.record.wins}</dd></div><div><dt className="text-[11px] text-text-muted">Ничьи</dt><dd className="technical-number mt-0.5 text-lg font-semibold">{hero.record.draws}</dd></div><div><dt className="text-[11px] text-text-muted">Поражения</dt><dd className="technical-number mt-0.5 text-lg font-semibold">{hero.record.losses}</dd></div></dl>
      </div>

      <div className="flex min-w-0 items-center justify-between gap-3 border-t border-[var(--border-subtle)] pt-3 sm:col-span-2 lg:col-span-1 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
        <div><p className="text-xs text-text-muted">Общий тренд</p><p className={`mt-1.5 flex items-center gap-2 text-sm font-semibold ${trendTones[hero.trend.direction]}`}><TrendIcon aria-hidden="true" size={17} />{hero.trend.label}</p>{hero.readiness.label ? <p className="mt-1.5 text-[11px] leading-4 text-text-muted">{hero.readiness.label}</p> : null}</div>
      </div>
    </div>
  </BentoCard>;
}

export function ChessProfileHeroUnavailable() {
  return <BentoCard as="section" aria-labelledby="profile-title" data-testid="chess-profile-hero" className="p-4 sm:p-5"><p className="text-xs font-semibold text-forest-light">Шахматный профиль</p><h1 id="profile-title" className="mt-1 text-xl font-semibold tracking-[-0.035em]">Профиль временно недоступен</h1><p className="mt-2 text-sm text-text-secondary">Остальные данные Dashboard можно продолжать использовать.</p></BentoCard>;
}
