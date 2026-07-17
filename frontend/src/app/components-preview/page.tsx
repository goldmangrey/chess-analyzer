import Link from "next/link";

import { BentoCard } from "@/components/ui/bento-card";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/ui/status-pill";

const swatches = [
  { label: "Surface", value: "#FFFFFF", className: "bg-surface" },
  { label: "Muted", value: "#F8F8F5", className: "bg-surface-muted" },
  { label: "Dark", value: "#262626", className: "bg-surface-dark" },
  { label: "Forest", value: "#185C3B", className: "bg-forest" },
  { label: "Mint", value: "#BFE8D0", className: "bg-mint" },
  { label: "Lime", value: "#C9F36A", className: "bg-lime" },
  { label: "Yellow", value: "#FFD765", className: "bg-warm-yellow" },
  { label: "Best", value: "#25875A", className: "bg-best" },
  { label: "Inaccuracy", value: "#E2B93B", className: "bg-inaccuracy" },
  { label: "Mistake", value: "#F09145", className: "bg-mistake" },
  { label: "Blunder", value: "#E95D5D", className: "bg-blunder" },
];

export default function ComponentsPreviewPage() {
  return (
    <main className="ambient-gradient min-h-screen px-4 py-6 sm:px-7 sm:py-9 lg:px-10 lg:py-12">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-extrabold text-forest">Chess AI Teacher</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-[-0.055em] sm:text-6xl">
              Components preview
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-text-secondary">
              Рабочая поверхность дизайн-системы: цвет, ритм, типографика и
              низкоуровневые элементы без продуктовых данных.
            </p>
          </div>
          <Link
            href="/"
            className="focus-ring rounded-full px-4 py-2 text-sm font-semibold text-text-secondary hover:bg-black/[0.045]"
          >
            Вернуться к foundation
          </Link>
        </header>

        <div className="mt-10 space-y-6 sm:mt-14 sm:space-y-8">
          <BentoCard as="section" className="p-5 sm:p-8">
            <h2 className="text-xl font-semibold tracking-[-0.035em] sm:text-2xl">
              Цветовая система
            </h2>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {swatches.map((swatch) => (
                <div
                  key={swatch.label}
                  className="overflow-hidden rounded-[1.25rem] border border-[var(--border-subtle)] bg-white"
                >
                  <div
                    aria-hidden="true"
                    className={`h-20 ${swatch.className}`}
                  />
                  <div className="p-3">
                    <p className="text-xs font-bold text-text-primary">
                      {swatch.label}
                    </p>
                    <p className="technical-number mt-1 text-xs text-text-muted">
                      {swatch.value}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </BentoCard>

          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <BentoCard as="section" tone="dark" className="p-6 sm:p-9">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-lime">
                Typography
              </p>
              <h2 className="mt-5 max-w-2xl text-4xl font-semibold leading-tight tracking-[-0.055em] sm:text-6xl">
                Editorial analytics, без визуального шума
              </h2>
              <p className="mt-6 max-w-xl text-base leading-7 text-white/65">
                Manrope ведёт повествование, а JetBrains Mono удерживает точность
                технических значений.
              </p>
              <div className="mt-8 flex flex-wrap items-end gap-6 border-t border-white/10 pt-6">
                <div>
                  <p className="text-xs text-white/45">Evaluation</p>
                  <p className="technical-number mt-1 text-3xl text-lime">+1.42</p>
                </div>
                <div>
                  <p className="text-xs text-white/45">CP Loss</p>
                  <p className="technical-number mt-1 text-3xl text-warm-yellow">
                    084
                  </p>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-white/45">FEN fragment</p>
                  <p className="technical-number mt-2 truncate text-sm text-white/75">
                    r1bq1rk1/ppp2ppp/2np1n2
                  </p>
                </div>
              </div>
            </BentoCard>

            <BentoCard as="section" tone="mint" className="p-6 sm:p-8">
              <h2 className="text-2xl font-semibold tracking-[-0.04em]">
                Radius hierarchy
              </h2>
              <div className="mt-7 rounded-[1.75rem] bg-white/70 p-4 shadow-[var(--shadow-soft)]">
                <p className="text-sm font-semibold">Large card · 28px</p>
                <div className="mt-4 rounded-[1.25rem] bg-mint-surface p-4">
                  <p className="text-sm text-text-secondary">Inner panel · 20px</p>
                  <div className="mt-4 inline-flex rounded-full bg-forest px-4 py-2 text-xs font-bold text-white">
                    Pill · full
                  </div>
                </div>
              </div>
            </BentoCard>
          </div>

          <section className="grid gap-6 lg:grid-cols-3">
            <BentoCard tone="yellow" className="p-6 sm:p-8 lg:col-span-2">
              <h2 className="text-2xl font-semibold tracking-[-0.04em]">
                Buttons
              </h2>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button variant="primary">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="dark">Dark</Button>
                <Button size="sm">Small</Button>
                <Button size="lg">Large</Button>
                <Button disabled>Disabled</Button>
              </div>
            </BentoCard>

            <BentoCard tone="muted" className="p-6 sm:p-8">
              <h2 className="text-2xl font-semibold tracking-[-0.04em]">
                Loading state
              </h2>
              <div className="mt-6 space-y-3" aria-label="Пример загрузки">
                <div className="skeleton h-4 w-2/3 rounded-full" />
                <div className="skeleton h-4 w-full rounded-full" />
                <div className="skeleton h-20 w-full rounded-[1.25rem]" />
              </div>
            </BentoCard>
          </section>

          <BentoCard as="section" className="p-6 sm:p-8">
            <h2 className="text-2xl font-semibold tracking-[-0.04em]">
              Status pills
            </h2>
            <div className="mt-6 flex flex-wrap gap-3">
              <StatusPill tone="neutral">Neutral</StatusPill>
              <StatusPill tone="success" dot>
                Completed
              </StatusPill>
              <StatusPill tone="warning" dot>
                Analyzing
              </StatusPill>
              <StatusPill tone="danger" dot>
                Failed
              </StatusPill>
              <StatusPill tone="info">Pending</StatusPill>
              <StatusPill tone="dark" dot>
                Stockfish ready
              </StatusPill>
            </div>
          </BentoCard>
        </div>
      </div>
    </main>
  );
}
