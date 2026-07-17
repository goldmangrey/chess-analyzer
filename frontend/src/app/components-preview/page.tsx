import { Info, Search, Sparkles } from "lucide-react";

import {
  AppShell,
  BentoGrid,
  BentoGridItem,
  EngineStatus,
  PageHeading,
  SectionHeading,
} from "@/components/layout";
import {
  BentoCard,
  Button,
  EmptyState,
  IconButton,
  Input,
  Select,
  Separator,
  Skeleton,
  Spinner,
  StatusPill,
  Tooltip,
} from "@/components/ui";

import { InteractivePreview } from "./interactive-preview";

const swatches = [
  ["Surface", "#FFFFFF", "bg-surface"],
  ["Forest", "#185C3B", "bg-forest"],
  ["Mint", "#BFE8D0", "bg-mint"],
  ["Lime", "#C9F36A", "bg-lime"],
  ["Yellow", "#FFD765", "bg-warm-yellow"],
  ["Mistake", "#F09145", "bg-mistake"],
  ["Blunder", "#E95D5D", "bg-blunder"],
] as const;

const gameCountOptions = [
  { value: "5", label: "5 партий" },
  { value: "10", label: "10 партий" },
  { value: "20", label: "20 партий" },
];

export default function ComponentsPreviewPage() {
  return (
    <AppShell>
      <PageHeading
        eyebrow="Design system / Stage 9"
        title="Components preview"
        description="Рабочая поверхность общих компонентов без API-запросов, продуктовой аналитики и демонстрационных метрик."
        action={<StatusPill tone="info">Development only</StatusPill>}
      />

      <div className="mt-12 space-y-12">
        <section>
          <SectionHeading title="Navigation shell" description="Один серверный shell, два маршрута и три presentation-состояния движка." />
          <BentoCard className="mt-5 p-5 sm:p-7">
            <div className="flex flex-wrap gap-3">
              <EngineStatus status="ready" />
              <EngineStatus status="analyzing" />
              <EngineStatus status="unavailable" />
            </div>
          </BentoCard>
        </section>

        <section>
          <SectionHeading title="Bento grid" description="Карточки сохраняют собственную высоту и меняют span без жёсткой матрицы." />
          <BentoGrid className="mt-5">
            <BentoGridItem className="md:col-span-4 xl:col-span-7">
              <BentoCard tone="dark" className="h-full p-6 sm:p-8">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-lime">Typography</p>
                <h3 className="mt-5 text-3xl font-semibold tracking-[-0.05em] sm:text-5xl">Спокойная визуальная иерархия</h3>
                <p className="mt-5 max-w-xl text-sm leading-7 text-white/65">Manrope ведёт повествование, JetBrains Mono отвечает за технические значения.</p>
                <p className="technical-number mt-8 text-3xl text-lime">+1.42 · 084 CPL</p>
              </BentoCard>
            </BentoGridItem>
            <BentoGridItem className="md:col-span-2 xl:col-span-5">
              <BentoCard tone="mint" className="h-full p-6 sm:p-8">
                <h3 className="text-2xl font-semibold tracking-[-0.04em]">Radius hierarchy</h3>
                <div className="mt-6 rounded-[1.75rem] bg-white/70 p-4">
                  Large card
                  <div className="mt-3 rounded-[1.15rem] bg-mint-surface p-4 text-sm text-text-secondary">Inner panel <span className="ml-2 rounded-full bg-forest px-3 py-1 text-xs text-white">Pill</span></div>
                </div>
              </BentoCard>
            </BentoGridItem>
          </BentoGrid>
        </section>

        <section>
          <SectionHeading title="Color tokens" />
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {swatches.map(([label, value, className]) => (
              <div key={label} className="overflow-hidden rounded-[1.15rem] bg-surface shadow-[var(--shadow-soft)]">
                <div aria-hidden="true" className={`h-16 ${className}`} />
                <div className="p-3"><p className="text-xs font-bold">{label}</p><p className="technical-number mt-1 text-xs text-text-muted">{value}</p></div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <SectionHeading title="Controls" description="Native controls с явными labels, hints и error descriptions." />
          <BentoCard className="mt-5 p-5 sm:p-8">
            <div className="grid gap-6 lg:grid-cols-2">
              <Input label="Chess.com username" placeholder="Yeskendir" hint="Используется только как нейтральный пример поля." prefix="@" />
              <Input label="Username с ошибкой" defaultValue=" " error="Введите непустое имя пользователя." />
              <Select label="Количество партий" placeholder="Выберите количество" options={gameCountOptions} hint="Native select без custom dropdown." />
              <Select label="Количество с ошибкой" options={gameCountOptions} error="Выберите допустимое значение." />
            </div>
            <Separator className="my-7" />
            <div className="flex flex-wrap items-center gap-3">
              <Button>Primary</Button><Button variant="secondary">Secondary</Button><Button variant="ghost">Ghost</Button><Button variant="dark">Dark</Button><Button loading>Сохранение</Button>
              <Tooltip content="Доступно по hover и keyboard focus">
                <IconButton label="Информация"><Info aria-hidden="true" size={18} /></IconButton>
              </Tooltip>
              <IconButton label="Поиск" variant="ghost"><Search aria-hidden="true" size={18} /></IconButton>
            </div>
          </BentoCard>
        </section>

        <section>
          <SectionHeading title="Status and loading" />
          <BentoCard tone="yellow" className="mt-5 p-5 sm:p-8">
            <div className="flex flex-wrap gap-2">
              <StatusPill>Neutral</StatusPill><StatusPill tone="success" dot>Завершён</StatusPill><StatusPill tone="warning" dot>Анализируется</StatusPill><StatusPill tone="danger" dot>Ошибка</StatusPill><StatusPill tone="info">Ожидает</StatusPill><StatusPill tone="dark" dot>Stockfish готов</StatusPill>
            </div>
            <Separator className="my-7" />
            <div className="grid gap-5 sm:grid-cols-[auto_1fr] sm:items-center">
              <Spinner className="text-forest" />
              <div className="space-y-3"><Skeleton rounded="full" className="h-4 w-2/3" /><Skeleton rounded="full" className="h-4 w-full" /><Skeleton rounded="lg" className="h-16 w-full" /></div>
            </div>
          </BentoCard>
        </section>

        <section>
          <SectionHeading title="Empty state" />
          <div className="mt-5">
            <EmptyState icon={<Sparkles aria-hidden="true" size={22} />} title="Пока здесь пусто" description="Компонент не содержит жёстко заданного шахматного контекста и принимает любое действие через slot." action={<Button variant="secondary">Нейтральное действие</Button>} />
          </div>
        </section>

        <section>
          <SectionHeading title="Feedback" description="Интерактивность локализована в отдельном client component." />
          <BentoCard className="mt-5 p-5 sm:p-8"><InteractivePreview /></BentoCard>
        </section>
      </div>
    </AppShell>
  );
}
