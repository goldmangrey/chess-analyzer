import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { BentoCard, LocalDateTime, StatusPill } from "@/components/ui";
import type { GameIntelligenceResponse } from "@/lib/api/types";
import { formatColor, formatCpLoss } from "@/lib/format";
import { analysisStatusLabel, analysisStatusTone, gameResultLabel } from "@/lib/status";

export function GameHeaderCard({ intelligence }: { intelligence: GameIntelligenceResponse }) {
  const { game, opening, summary, analysis } = intelligence;
  return (
    <BentoCard as="section" className="p-6 sm:p-8">
      <Link href="/games" className="focus-ring inline-flex items-center gap-2 rounded-full text-sm font-semibold text-forest hover:text-forest-light"><ArrowLeft aria-hidden="true" size={16} />Все партии</Link>
      <div className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-3"><h1 className="text-3xl font-semibold tracking-[-0.05em] sm:text-5xl">vs {game.opponent}</h1><StatusPill tone={analysisStatusTone(analysis.status)} dot>{analysisStatusLabel(analysis.status)}</StatusPill></div>
          <p className="mt-4 text-sm text-text-secondary">{gameResultLabel(game.result)} · {formatColor(game.user_color)} · <LocalDateTime value={game.played_at} dateOnly /> · {game.time_control ?? "Контроль не указан"}</p>
          <p className="mt-3 text-sm"><strong>{game.white_username}</strong> <span className="technical-number text-text-muted">{game.white_rating ?? "—"}</span> <span className="mx-2 text-text-muted">—</span> <strong>{game.black_username}</strong> <span className="technical-number text-text-muted">{game.black_rating ?? "—"}</span></p>
          <p className="mt-4 text-sm text-text-secondary"><span className="font-semibold text-forest-light">{opening.name ?? opening.eco ?? "Дебют не определён"}</span>{opening.name && opening.eco ? <> · {opening.eco}</> : null}</p>
        </div>
        <dl className="grid grid-cols-4 gap-3 rounded-[1.5rem] bg-surface-muted p-4 text-center">
          <div><dt className="text-xs text-text-muted">CP Loss</dt><dd className="technical-number mt-2 font-semibold">{formatCpLoss(summary?.average_cp_loss ?? null)}</dd></div>
          <div><dt className="text-xs text-text-muted">Неточности</dt><dd className="technical-number mt-2 font-semibold text-inaccuracy-text">{summary?.inaccuracies ?? 0}</dd></div>
          <div><dt className="text-xs text-text-muted">Ошибки</dt><dd className="technical-number mt-2 font-semibold text-mistake">{summary?.mistakes ?? 0}</dd></div>
          <div><dt className="text-xs text-text-muted">Зевки</dt><dd className="technical-number mt-2 font-semibold text-blunder-text">{summary?.blunders ?? 0}</dd></div>
        </dl>
      </div>
    </BentoCard>
  );
}
