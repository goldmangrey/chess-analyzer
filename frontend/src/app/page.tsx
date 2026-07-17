import Link from "next/link";

import { AppShell, PageHeading } from "@/components/layout";
import { BentoCard, StatusPill } from "@/components/ui";
import { API_BASE_URL } from "@/lib/env";

export default function Home() {
  return (
    <AppShell activeSection="dashboard">
      <PageHeading
        eyebrow="Local-first chess analytics"
        title="Локальный шахматный анализ"
        description="Партии из Chess.com, нативный Stockfish и спокойный интерфейс для разбора решений — полностью на вашем компьютере."
      />

      <BentoCard as="section" className="accent-shadow relative mt-10 overflow-hidden p-6 sm:p-10 lg:p-12">
        <div aria-hidden="true" className="absolute -right-20 -top-24 size-80 rounded-full bg-lime-surface blur-3xl" />
        <div className="relative grid gap-10 lg:grid-cols-[1fr_22rem] lg:items-end">
          <div>
            <p className="max-w-xl text-lg font-semibold leading-8 tracking-[-0.025em]">
              Общий интерфейс готов к подключению реальных данных на следующих этапах.
            </p>
            <div className="mt-7 flex flex-wrap gap-2.5">
              <StatusPill tone="success" dot>FastAPI Ready</StatusPill>
              <StatusPill tone="info" dot>SQLite Ready</StatusPill>
              <StatusPill tone="dark" dot>Stockfish Local</StatusPill>
            </div>
          </div>
          <div className="rounded-[1.5rem] bg-surface-muted p-5 sm:p-6">
            <p className="text-sm font-semibold">Компоненты интерфейса</p>
            <p className="mt-2 text-sm leading-6 text-text-secondary">
              Shell, формы и feedback states собраны на отдельной странице разработки.
            </p>
            <Link href="/components-preview" className="focus-ring mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-full bg-forest px-5 text-sm font-bold text-white shadow-[var(--shadow-accent)] transition hover:bg-forest-light">
              Открыть preview
            </Link>
            <p className="technical-number mt-5 break-all text-xs text-text-muted">{API_BASE_URL}</p>
          </div>
        </div>
      </BentoCard>
    </AppShell>
  );
}
