"use client";

import { useMemo, useSyncExternalStore } from "react";
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { BentoCard } from "@/components/ui";
import type { MoveAnalysis } from "@/lib/api/types";
import { formatEvaluation } from "@/lib/format";
import { moveClassificationLabel } from "@/lib/status";

const subscribe = () => () => undefined;

export function EvaluationTimeline({ moves, selectedPly, onSelect }: { moves: MoveAnalysis[]; selectedPly: number; onSelect: (ply: number) => void }) {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const data = useMemo(() => [{ ply: 0, label: "Начало", evaluation: 0, rawEvaluation: 0, classification: "—", cpLoss: 0 }, ...moves.filter((move) => move.evaluation_after_cp !== null).map((move) => ({ ply: move.ply, label: move.played_move_san ?? move.played_move_uci, evaluation: Math.max(-1000, Math.min(1000, move.evaluation_after_cp ?? 0)), rawEvaluation: move.evaluation_after_cp, classification: moveClassificationLabel(move.classification), cpLoss: move.centipawn_loss }))], [moves]);
  return (
    <BentoCard as="section" className="p-6 sm:p-8">
      <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">White perspective</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">Timeline оценки</h2></div>
      {data.length < 3 ? <div className="grid h-56 place-items-center text-sm text-text-muted">Недостаточно данных для timeline</div> : (
        <div className="mt-6 h-72" aria-label="Timeline оценки позиции по всем полуходам">
          {mounted ? <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -14 }} onClick={(state) => { const index = Number(state.activeTooltipIndex); if (Number.isInteger(index) && data[index]) onSelect(data[index].ply); }}>
            <ReferenceArea y1={0} y2={1000} fill="var(--mint-surface)" fillOpacity={0.55} /><ReferenceArea y1={-1000} y2={0} fill="var(--yellow-surface)" fillOpacity={0.35} />
            <CartesianGrid vertical={false} stroke="var(--border-subtle)" strokeDasharray="4 6" /><ReferenceLine y={0} stroke="var(--border-strong)" strokeWidth={1.5} />
            <XAxis dataKey="ply" tickLine={false} axisLine={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} /><YAxis domain={[-1000, 1000]} tickFormatter={(value) => `${value / 100}`} tickLine={false} axisLine={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
            <Tooltip formatter={(_, __, item) => [formatEvaluation(item.payload.rawEvaluation), `${item.payload.label} · ${item.payload.classification} · CPL ${item.payload.cpLoss}`]} labelFormatter={(ply) => `Ply ${ply}`} contentStyle={{ border: "1px solid var(--border-subtle)", borderRadius: "16px", boxShadow: "var(--shadow-soft)" }} />
            <Line type="linear" dataKey="evaluation" stroke="var(--forest-light)" strokeWidth={3} dot={(props) => { const active = props.payload.ply === selectedPly; return <circle key={props.key} cx={props.cx} cy={props.cy} r={active ? 6 : 3} fill={active ? "var(--lime)" : "var(--surface)"} stroke="var(--forest-light)" strokeWidth={2} />; }} activeDot={{ r: 6, fill: "var(--lime)" }} />
          </LineChart></ResponsiveContainer> : null}
        </div>
      )}
      <p className="sr-only">Timeline содержит {data.length - 1} оценок ходов. Положительные значения означают преимущество белых, отрицательные — чёрных.</p>
    </BentoCard>
  );
}
