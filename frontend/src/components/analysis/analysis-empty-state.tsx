"use client";

import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import { AnalyzeGameButton } from "@/components/games/analyze-game-button";
import { BentoCard, Button } from "@/components/ui";
import type { AnalysisStatus } from "@/lib/api/types";
import { useAnalysisRefresh } from "@/hooks/use-analysis-refresh";

const copy = {
  pending: ["Отчёт для этой партии ещё не создан", "Запустите локальный Stockfish, чтобы получить оценку каждого полухода."],
  analyzing: ["Stockfish анализирует партию", "Обработка идёт в background. Обновите данные через некоторое время."],
  failed: ["Не удалось проанализировать партию", "Проверьте STOCKFISH_PATH и повторите анализ."],
  completed: ["Анализ завершён, но данные ходов отсутствуют", "Состояние данных несогласованно — запустите анализ повторно."],
} satisfies Record<AnalysisStatus, [string, string]>;

export function AnalysisEmptyState({ gameId, status }: { gameId: number; status: AnalysisStatus }) {
  const router = useRouter();
  useAnalysisRefresh({ enabled: status === "analyzing", onRefresh: () => router.refresh() });
  return (
    <BentoCard as="section" tone={status === "failed" ? "yellow" : "muted"} className="mt-6 p-7 text-center sm:p-12">
      <h2 className="text-3xl font-semibold tracking-[-0.05em]">{copy[status][0]}</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-text-secondary">{copy[status][1]}</p>
      <div className="mt-7 flex flex-wrap justify-center gap-3">
        {status === "analyzing" ? <Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={() => router.refresh()}>Обновить данные</Button> : <AnalyzeGameButton gameId={gameId} status={status} />}
      </div>
    </BentoCard>
  );
}
