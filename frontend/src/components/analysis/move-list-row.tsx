import type { MoveAnalysis } from "@/lib/api/types";
import { moveListPresentation } from "@/lib/review-board";

const qualityClasses = { best: "bg-best text-white", normal: "bg-surface text-forest", inaccuracy: "bg-inaccuracy text-text-primary", mistake: "bg-mistake text-text-primary", blunder: "bg-blunder text-white" } as const;

export function MoveButton({ move, selectedPly, criticalPlys, onSelect, buttonRef }: { move: MoveAnalysis; selectedPly: number; criticalPlys: ReadonlySet<number>; onSelect: (ply: number) => void; buttonRef?: (node: HTMLButtonElement | null) => void }) {
  const item = moveListPresentation(move, selectedPly, criticalPlys);
  return (
    <button ref={buttonRef} type="button" aria-current={item.selected ? "step" : undefined} aria-label={item.accessibleLabel} title={`${item.quality.label}${item.critical ? " · Критический момент" : ""}`} onClick={() => onSelect(move.ply)} className={`focus-ring relative flex min-h-10 min-w-0 items-center gap-2 rounded-xl border-l-[3px] px-2.5 py-2 text-left text-sm transition ${item.selected ? "border-lime bg-surface-dark font-semibold text-white shadow-sm" : item.critical ? "border-forest bg-surface-muted hover:bg-mint-surface" : "border-transparent hover:bg-surface-muted"}`}>
      {item.critical ? <span aria-hidden="true" className={`absolute -left-[5px] top-1/2 size-2.5 -translate-y-1/2 rounded-full border-2 ${item.selected ? "border-surface-dark bg-lime" : "border-surface bg-forest"}`} /> : null}
      <span className="truncate">{item.san}</span>
      <span aria-hidden="true" className={`ml-auto grid min-w-5 place-items-center rounded-md px-1 py-0.5 text-[10px] font-black leading-none ${qualityClasses[item.quality.tone]}`}>{item.quality.symbol}</span>
    </button>
  );
}

export function MoveListRow({ moveNumber, white, black, selectedPly, criticalPlys, onSelect, register }: { moveNumber: number; white?: MoveAnalysis; black?: MoveAnalysis; selectedPly: number; criticalPlys: ReadonlySet<number>; onSelect: (ply: number) => void; register: (ply: number, node: HTMLButtonElement | null) => void }) {
  return <div className="grid grid-cols-[2rem_minmax(0,1fr)_minmax(0,1fr)] items-center gap-1"><span className="technical-number text-xs text-text-muted">{moveNumber}.</span>{white ? <MoveButton move={white} selectedPly={selectedPly} criticalPlys={criticalPlys} onSelect={onSelect} buttonRef={(node) => register(white.ply, node)} /> : <span />}{black ? <MoveButton move={black} selectedPly={selectedPly} criticalPlys={criticalPlys} onSelect={onSelect} buttonRef={(node) => register(black.ply, node)} /> : <span />}</div>;
}
