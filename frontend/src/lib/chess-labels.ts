import type { ErrorType, IntelligenceConfidenceLevel, MoveClassification } from "./api/types";

const taxonomyLabels: Record<ErrorType, string> = {
  hanging_piece: "Фигуры под ударом",
  missed_capture: "Упущенные взятия",
  missed_check: "Упущенные шахи",
  missed_mate: "Упущенный мат",
  allowed_mate: "Допущенный мат",
  king_safety: "Безопасность короля",
  development: "Развитие фигур",
  bad_exchange: "Неудачные размены",
  pawn_structure: "Пешечная структура",
  tactical_pattern: "Тактические ошибки",
  fork: "Вилки",
  pin: "Связки",
  skewer: "Линейные удары",
  back_rank: "Слабость последней горизонтали",
};

const confidenceLabels: Record<IntelligenceConfidenceLevel, string> = {
  insufficient: "Недостаточно данных",
  low: "Низкая уверенность",
  medium: "Средняя уверенность",
  high: "Высокая уверенность",
};

const classificationLabels: Record<MoveClassification, string> = {
  normal: "Обычный ход",
  inaccuracy: "Неточность",
  mistake: "Ошибка",
  blunder: "Зевок",
};

export function taxonomyLabel(taxonomy: ErrorType): string {
  return taxonomyLabels[taxonomy] ?? "Шахматный паттерн";
}

export function confidenceLabel(level: IntelligenceConfidenceLevel): string {
  return confidenceLabels[level];
}

export function classificationLabel(classification: MoveClassification): string {
  return classificationLabels[classification];
}

export function pluralizeRu(value: number, forms: readonly [string, string, string]): string {
  const absolute = Math.abs(Math.trunc(value));
  const modulo100 = absolute % 100;
  const modulo10 = absolute % 10;
  const form = modulo100 >= 11 && modulo100 <= 14
    ? forms[2]
    : modulo10 === 1
      ? forms[0]
      : modulo10 >= 2 && modulo10 <= 4
        ? forms[1]
        : forms[2];
  return `${value} ${form}`;
}

export const incidentCountLabel = (value: number) => pluralizeRu(value, ["случай", "случая", "случаев"]);
export const gameCountLabel = (value: number) => pluralizeRu(value, ["партия", "партии", "партий"]);
