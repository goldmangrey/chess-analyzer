import type { StatusPillTone } from "@/components/ui/status-pill";
import type { AnalysisStatus, GameResult, MoveClassification } from "@/lib/api/types";

export function analysisStatusLabel(status: AnalysisStatus): string {
  return { pending: "Отчёт не создан", queued: "В очереди", processing: "Создаём отчёт", analyzing: "Создаём отчёт", completed: "Отчёт готов", failed: "Ошибка анализа" }[status];
}

export function analysisStatusTone(status: AnalysisStatus): StatusPillTone {
  return { pending: "neutral", queued: "info", processing: "info", analyzing: "info", completed: "success", failed: "danger" }[status] as StatusPillTone;
}

export function gameResultLabel(result: GameResult): string {
  return { win: "Победа", draw: "Ничья", loss: "Поражение" }[result];
}

export function moveClassificationLabel(classification: MoveClassification): string {
  return { normal: "Норма", inaccuracy: "Неточность", mistake: "Ошибка", blunder: "Зевок" }[classification];
}
