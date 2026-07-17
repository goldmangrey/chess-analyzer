import { AlertTriangle } from "lucide-react";

import { BentoCard } from "@/components/ui";
import type { SystemStatus } from "@/lib/api/types";

export function SystemDiagnosticCard({ status }: { status: SystemStatus }) {
  const issues = [
    status.database.status !== "ready" ? "Локальная база недоступна или её схема не инициализирована." : null,
    status.stockfish.status !== "ready" ? `Stockfish не найден. Проверьте STOCKFISH_PATH в backend/.env (${status.stockfish.path}).` : null,
    !status.chesscom.configured ? "Настройте CHESS_USERNAME в backend/.env." : null,
    !status.chesscom.user_agent_configured ? "Настройте CHESSCOM_USER_AGENT в backend/.env." : null,
  ].filter((issue): issue is string => issue !== null);

  if (issues.length === 0) return null;
  return (
    <BentoCard as="section" tone="yellow" className="mb-6 flex gap-4 p-5 sm:p-6">
      <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0 text-inaccuracy-text" size={20} />
      <div><h2 className="font-semibold">Локальная среда требует настройки</h2><ul className="mt-2 space-y-1 text-sm leading-6 text-text-secondary">{issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></div>
    </BentoCard>
  );
}
