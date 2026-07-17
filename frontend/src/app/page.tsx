import Link from "next/link";

import { BentoCard } from "@/components/ui/bento-card";
import { StatusPill } from "@/components/ui/status-pill";
import { API_BASE_URL } from "@/lib/env";

export default function Home() {
  return (
    <main className="ambient-gradient min-h-screen overflow-hidden px-4 py-5 sm:px-7 sm:py-7 lg:px-10 lg:py-10">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl flex-col sm:min-h-[calc(100vh-3.5rem)] lg:min-h-[calc(100vh-5rem)]">
        <header className="flex items-center justify-between px-1 py-2">
          <p className="text-sm font-extrabold tracking-[-0.03em] text-forest sm:text-base">
            Chess AI Teacher
          </p>
          <span className="technical-number text-xs text-text-muted">
            local / v0.1
          </span>
        </header>

        <div className="flex flex-1 items-center py-10 sm:py-14">
          <BentoCard
            as="section"
            className="accent-shadow relative w-full overflow-hidden p-6 sm:p-10 lg:p-14"
          >
            <div
              aria-hidden="true"
              className="absolute -right-20 -top-24 size-72 rounded-full bg-lime-surface blur-3xl sm:size-96"
            />
            <div
              aria-hidden="true"
              className="absolute -bottom-28 left-1/3 size-64 rounded-full bg-mint-surface blur-3xl"
            />

            <div className="relative grid gap-12 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)] lg:items-end">
              <div>
                <p className="mb-5 text-xs font-bold uppercase tracking-[0.18em] text-forest-light">
                  Soft Bento Foundation
                </p>
                <h1 className="max-w-4xl text-[clamp(2.75rem,8vw,6.8rem)] font-semibold leading-[0.94] tracking-[-0.065em] text-text-primary">
                  Локальный шахматный анализ
                </h1>
                <p className="mt-7 max-w-2xl text-base leading-7 text-text-secondary sm:text-lg sm:leading-8">
                  Партии из Chess.com, нативный Stockfish и спокойный интерфейс
                  для разбора решений — полностью на вашем компьютере.
                </p>

                <div className="mt-8 flex flex-wrap gap-2.5">
                  <StatusPill tone="success" dot>
                    FastAPI Ready
                  </StatusPill>
                  <StatusPill tone="info" dot>
                    SQLite Ready
                  </StatusPill>
                  <StatusPill tone="dark" dot>
                    Stockfish Local
                  </StatusPill>
                </div>
              </div>

              <aside className="rounded-[1.5rem] border border-[var(--border-subtle)] bg-surface-muted/80 p-5 backdrop-blur-sm sm:p-6">
                <p className="text-sm font-semibold text-text-primary">
                  Основа интерфейса готова
                </p>
                <p className="mt-2 text-sm leading-6 text-text-secondary">
                  Токены, типографика и базовые компоненты собраны в отдельной
                  preview-странице.
                </p>
                <Link
                  href="/components-preview"
                  className="focus-ring mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-full bg-forest px-5 text-sm font-bold text-white shadow-[var(--shadow-accent)] transition hover:bg-forest-light active:translate-y-px"
                >
                  Открыть components preview
                </Link>
                <div className="mt-6 border-t border-[var(--border-subtle)] pt-4">
                  <p className="text-xs text-text-muted">Backend URL</p>
                  <p className="technical-number mt-1 break-all text-xs text-text-secondary">
                    {API_BASE_URL}
                  </p>
                </div>
              </aside>
            </div>
          </BentoCard>
        </div>
      </div>
    </main>
  );
}
