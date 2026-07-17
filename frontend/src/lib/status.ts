import type { StatusPillTone } from "@/components/ui/status-pill";
import type { AnalysisStatus, GameResult, MoveClassification } from "@/lib/api/types";

export function analysisStatusLabel(status: AnalysisStatus): string {
  return { pending: "Ожидает", analyzing: "Анализируется", completed: "Завершён", failed: "Ошибка" }[status];
}

export function analysisStatusTone(status: AnalysisStatus): StatusPillTone {
  return { pending: "neutral", analyzing: "info", completed: "success", failed: "danger" }[status] as StatusPillTone;
}

export function gameResultLabel(result: GameResult): string {
  return { win: "Победа", draw: "Ничья", loss: "Поражение" }[result];
}

export function moveClassificationLabel(classification: MoveClassification): string {
  return { normal: "Норма", inaccuracy: "Неточность", mistake: "Ошибка", blunder: "Зевок" }[classification];
}
