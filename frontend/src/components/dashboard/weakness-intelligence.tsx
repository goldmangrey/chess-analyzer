"use client";

import { ArrowRight, Crosshair, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { BentoCard, Modal } from "@/components/ui";
import type { DashboardInsight, DashboardRecurringMistake, DashboardViewModel } from "@/lib/dashboard-view-model";

function EvidenceDialog({ insight, open, onOpenChange }: { insight: DashboardRecurringMistake | DashboardInsight | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  if (!insight) return null;
  return <Modal open={open} onOpenChange={onOpenChange} title={insight.label} description={insight.support ?? undefined}>
    <div className="space-y-2">
      {insight.evidence.map((item) => <Link key={`${item.gameId}-${item.ply}`} href={item.href} className="focus-ring flex min-h-12 items-center justify-between gap-3 rounded-xl bg-surface-muted px-3 py-2.5 transition hover:bg-mint-surface">
        <span className="min-w-0"><span className="block text-sm font-semibold">{item.moveLabel}{item.move ? ` · ${item.move}` : ""}</span><span className="mt-0.5 block text-xs text-text-muted">{item.classification}</span></span>
        <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-forest">Посмотреть <ArrowRight aria-hidden="true" size={14} /></span>
      </Link>)}
    </div>
  </Modal>;
}

function InsightCard({ eyebrow, insight, tone, onEvidence }: { eyebrow: string; insight: DashboardInsight | null; tone: "weakness" | "strength"; onEvidence?: () => void }) {
  const weakness = tone === "weakness";
  const Icon = weakness ? Crosshair : ShieldCheck;
  return <BentoCard as="article" className={`h-full min-h-36 p-4 sm:p-5 ${weakness ? "border-mistake/25 bg-mistake-surface/45" : "border-best/15 bg-best-surface/30"}`}>
    <div className="flex items-start justify-between gap-3"><p className={`text-xs font-semibold ${weakness ? "text-mistake" : "text-forest-light"}`}>{eyebrow}</p><Icon aria-hidden="true" size={17} className={weakness ? "text-mistake/70" : "text-forest-light/70"} /></div>
    <h2 className="mt-2 text-lg font-semibold leading-6 tracking-[-0.025em]">{insight?.label ?? (weakness ? "Пока не определена" : "Пока недостаточно данных")}</h2>
    {insight?.support ? <p className="mt-2 text-sm text-text-secondary">{insight.support}</p> : null}
    <div className="mt-3 flex min-h-8 flex-wrap items-center justify-between gap-2">
      <p className="text-xs text-text-muted">{insight ? insight.confidenceLabel : weakness ? "Нужно больше надёжных паттернов" : "Надёжная сильная сторона ещё не определена"}</p>
      {insight && insight.evidence.length > 0 && onEvidence ? <button type="button" onClick={onEvidence} className="focus-ring min-h-10 rounded-full px-3 text-xs font-semibold text-forest hover:bg-white/70">Примеры</button> : null}
    </div>
  </BentoCard>;
}

export function WeaknessStrengthCards({ model }: { model: DashboardViewModel }) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  return <>
    <div className="grid gap-3 min-[430px]:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
      <InsightCard eyebrow="Главная слабость" insight={model.primaryWeakness} tone="weakness" onEvidence={() => setEvidenceOpen(true)} />
      <InsightCard eyebrow="Сильная сторона" insight={model.primaryStrength} tone="strength" />
    </div>
    <EvidenceDialog insight={model.primaryWeakness} open={evidenceOpen} onOpenChange={setEvidenceOpen} />
  </>;
}

export function RecurringMistakesCard({ model }: { model: DashboardViewModel }) {
  const [selected, setSelected] = useState<DashboardRecurringMistake | null>(null);
  return <>
    <BentoCard as="section" className="h-full p-4 sm:p-5" aria-labelledby="recurring-title">
      <p className="text-xs font-semibold text-forest-light">Личный паттерн игры</p>
      <h2 id="recurring-title" className="mt-1 text-lg font-semibold tracking-[-0.025em]">Повторяющиеся ошибки</h2>
      {model.recurringMistakes.length ? <ol className="mt-3 divide-y divide-[var(--border-subtle)]">{model.recurringMistakes.map((item, index) => <li key={item.taxonomy}>
        {item.evidence.length ? <button type="button" onClick={() => setSelected(item)} aria-label={`${item.label}: открыть примеры`} className="focus-ring flex min-h-14 w-full items-center gap-3 rounded-lg py-2.5 text-left hover:bg-surface-muted">
          <RecurringRow item={item} index={index} interactive />
        </button> : <div className="flex min-h-14 items-center gap-3 py-2.5"><RecurringRow item={item} index={index} /></div>}
      </li>)}</ol> : <p className="mt-4 text-sm text-text-muted">Повторяющиеся ошибки пока не определены.</p>}
    </BentoCard>
    <EvidenceDialog insight={selected} open={selected !== null} onOpenChange={(open) => { if (!open) setSelected(null); }} />
  </>;
}

function RecurringRow({ item, index, interactive = false }: { item: DashboardRecurringMistake; index: number; interactive?: boolean }) {
  return <><span className="technical-number w-4 shrink-0 text-xs text-text-muted">{index + 1}</span><div className="min-w-0 flex-1"><p className="text-sm font-semibold leading-5">{item.label}</p><p className="mt-0.5 text-xs text-text-muted">{item.support}</p></div>{interactive ? <ArrowRight aria-hidden="true" size={15} className="shrink-0 text-text-muted" /> : null}</>;
}
