import { ChevronsLeft, ChevronsRight, ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "@/components/ui";

export function BoardNavigation({ selectedPly, total, onSelect }: { selectedPly: number; total: number; onSelect: (ply: number) => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <p className="text-sm font-semibold text-text-secondary">{selectedPly === 0 ? "Начальная позиция" : `Ход ${selectedPly} из ${total}`}</p>
      <div className="flex gap-1 sm:gap-2"><IconButton label="В начало" size="md" variant="ghost" disabled={selectedPly === 0} onClick={() => onSelect(0)}><ChevronsLeft aria-hidden="true" size={17} /></IconButton><IconButton label="Предыдущий ход" size="md" variant="ghost" disabled={selectedPly === 0} onClick={() => onSelect(selectedPly - 1)}><ChevronLeft aria-hidden="true" size={17} /></IconButton><IconButton label="Следующий ход" size="md" variant="ghost" disabled={selectedPly === total} onClick={() => onSelect(selectedPly + 1)}><ChevronRight aria-hidden="true" size={17} /></IconButton><IconButton label="В конец" size="md" variant="ghost" disabled={selectedPly === total} onClick={() => onSelect(total)}><ChevronsRight aria-hidden="true" size={17} /></IconButton></div>
    </div>
  );
}
