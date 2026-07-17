import type { MoveAnalysis } from "@/lib/api/types";
import { moveClassificationLabel } from "@/lib/status";

const markerClasses = { normal: "bg-text-muted", inaccuracy: "bg-inaccuracy", mistake: "bg-mistake", blunder: "bg-blunder" };

export function MoveButton({ move, selected, onSelect, buttonRef }: { move: MoveAnalysis; selected: boolean; onSelect: (ply: number) => void; buttonRef?: (node: HTMLButtonElement | null) => void }) {
  return (
    <button ref={buttonRef} type="button" aria-pressed={selected} aria-label={`${move.move_number}${move.player_color === "black" ? "..." : "."} ${move.played_move_san ?? move.played_move_uci}, ${moveClassificationLabel(move.classification)}, CP Loss ${move.centipawn_loss}`} title={`${moveClassificationLabel(move.classification)} · CP Loss ${move.centipawn_loss}`} onClick={() => onSelect(move.ply)} className={selected ? "focus-ring flex min-w-0 items-center gap-2 rounded-xl bg-surface-dark px-3 py-2 text-left text-sm font-semibold text-white" : "focus-ring flex min-w-0 items-center gap-2 rounded-xl px-3 py-2 text-left text-sm hover:bg-surface-muted"}>
      <span aria-hidden="true" className={`size-2 shrink-0 rounded-full ${markerClasses[move.classification]}`} />
      <span className="truncate">{move.played_move_san ?? move.played_move_uci}</span>
      {move.is_user_move ? <span className={selected ? "ml-auto text-[10px] text-mint" : "ml-auto text-[10px] text-forest-light"}>вы</span> : null}
    </button>
  );
}

export function MoveListRow({ moveNumber, white, black, selectedPly, onSelect, register }: { moveNumber: number; white?: MoveAnalysis; black?: MoveAnalysis; selectedPly: number; onSelect: (ply: number) => void; register: (ply: number, node: HTMLButtonElement | null) => void }) {
  return <div className="grid grid-cols-[2.25rem_minmax(0,1fr)_minmax(0,1fr)] items-center gap-1"><span className="technical-number text-xs text-text-muted">{moveNumber}.</span>{white ? <MoveButton move={white} selected={selectedPly === white.ply} onSelect={onSelect} buttonRef={(node) => register(white.ply, node)} /> : <span />}{black ? <MoveButton move={black} selected={selectedPly === black.ply} onSelect={onSelect} buttonRef={(node) => register(black.ply, node)} /> : <span />}</div>;
}
