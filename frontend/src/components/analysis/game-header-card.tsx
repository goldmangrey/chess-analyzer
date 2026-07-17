import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { BentoCard, StatusPill } from "@/components/ui";
import type { GameDetailResponse } from "@/lib/api/types";
import { formatColor, formatCpLoss, formatDate } from "@/lib/format";
import { analysisStatusLabel, analysisStatusTone, gameResultLabel } from "@/lib/status";

export function GameHeaderCard({ game }: { game: GameDetailResponse }) {
  const opponent = game.user_color === "white" ? game.black_username : game.white_username;
  return (
    <BentoCard as="section" className="p-6 sm:p-8">
      <Link href="/games" className="focus-ring inline-flex items-center gap-2 rounded-full text-sm font-semibold text-forest hover:text-forest-light"><ArrowLeft aria-hidden="true" size={16} />Все партии</Link>
      <div className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-3"><h1 className="text-3xl font-semibold tracking-[-0.05em] sm:text-5xl">vs {opponent}</h1><StatusPill tone={analysisStatusTone(game.analysis_status)} dot>{analysisStatusLabel(game.analysis_status)}</StatusPill></div>
          <p className="mt-4 text-sm text-text-secondary">{gameResultLabel(game.result)} · {formatColor(game.user_color)} · {formatDate(game.played_at)} · {game.time_control ?? "Контроль не указан"}</p>
          <p className="mt-3 text-sm"><strong>{game.white_username}</strong> <span className="technical-number text-text-muted">{game.white_rating ?? "—"}</span> <span className="mx-2 text-text-muted">—</span> <strong>{game.black_username}</strong> <span className="technical-number text-text-muted">{game.black_rating ?? "—"}</span></p>
          <p className="mt-4 text-sm text-text-secondary"><span className="font-semibold text-forest-light">{game.opening_code ?? "—"}</span> · {game.opening_name ?? "Дебют не определён"}</p>
        </div>
        <dl className="grid grid-cols-4 gap-3 rounded-[1.5rem] bg-surface-muted p-4 text-center">
          <div><dt className="text-xs text-text-muted">CP Loss</dt><dd className="technical-number mt-2 font-semibold">{formatCpLoss(game.average_cp_loss)}</dd></div>
          <div><dt className="text-xs text-text-muted">Неточности</dt><dd className="technical-number mt-2 font-semibold text-inaccuracy-text">{game.inaccuracies}</dd></div>
          <div><dt className="text-xs text-text-muted">Ошибки</dt><dd className="technical-number mt-2 font-semibold text-mistake">{game.mistakes}</dd></div>
          <div><dt className="text-xs text-text-muted">Зевки</dt><dd className="technical-number mt-2 font-semibold text-blunder-text">{game.blunders}</dd></div>
        </dl>
      </div>
    </BentoCard>
  );
}
