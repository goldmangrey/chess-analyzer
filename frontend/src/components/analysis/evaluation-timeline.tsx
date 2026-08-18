"use client";

import { useMemo, useSyncExternalStore } from "react";
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { BentoCard } from "@/components/ui";
import type { CriticalMoment, MoveAnalysis, UserColor } from "@/lib/api/types";
import { buildEvaluationTimeline, type EvaluationTimelinePoint, TIMELINE_EVALUATION_LIMIT } from "@/lib/review-board";

const subscribe = () => () => undefined;

function TimelineDot({ cx, cy, payload }: { cx?: number; cy?: number; payload?: EvaluationTimelinePoint }) {
  if (cx === undefined || cy === undefined || !payload || payload.displayEvaluation === null) return <g />;
  const errorRadius = payload.classification === "blunder" ? 5 : payload.classification === "mistake" ? 4 : payload.classification === "inaccuracy" ? 3.5 : 2.5;
  const radius = payload.isCritical ? 6.5 : errorRadius;
  const positive = payload.criticalType === "best_move";
  const severityFill = payload.classification === "blunder" ? "var(--blunder)" : payload.classification === "mistake" ? "var(--mistake)" : payload.classification === "inaccuracy" ? "var(--inaccuracy)" : "var(--forest-light)";
  const fill = payload.isCritical ? (positive ? "var(--best)" : severityFill) : payload.classification === "normal" || payload.classification === "initial" ? "var(--surface)" : severityFill;
  return <g>{payload.isSelected ? <circle cx={cx} cy={cy} r={10} fill="var(--surface)" stroke="var(--forest)" strokeWidth={2.5} /> : null}<circle cx={cx} cy={cy} r={radius} fill={fill} stroke={payload.isCritical ? "var(--surface)" : "var(--forest-light)"} strokeWidth={payload.isCritical ? 2.5 : 1.5} /></g>;
}

export function EvaluationTimeline({ moves, criticalMoments, userColor, selectedPly, onSelect }: { moves: MoveAnalysis[]; criticalMoments: CriticalMoment[]; userColor: UserColor; selectedPly: number; onSelect: (ply: number) => void }) {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const data = useMemo(() => buildEvaluationTimeline(moves, userColor, criticalMoments, selectedPly), [criticalMoments, moves, selectedPly, userColor]);
  return (
    <BentoCard as="section" className="p-5 sm:p-8">
      <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Оценка с вашей стороны</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">Ход партии</h2><p className="mt-2 text-sm text-text-muted">Нажмите на точку, чтобы перейти к позиции.</p></div>
      {data.length < 3 ? <div className="grid h-56 place-items-center text-sm text-text-muted">Недостаточно данных для timeline</div> : (
        <div className="mt-5 h-64 sm:h-72" aria-label="Изменение оценки позиции с точки зрения пользователя">
          {mounted ? <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 12, right: 10, bottom: 0, left: -18 }} onClick={(state) => { const index = Number(state.activeTooltipIndex); if (Number.isInteger(index) && data[index]) onSelect(data[index].ply); }}>
            <ReferenceArea y1={0} y2={TIMELINE_EVALUATION_LIMIT} fill="var(--mint-surface)" fillOpacity={0.45} /><ReferenceArea y1={-TIMELINE_EVALUATION_LIMIT} y2={0} fill="var(--yellow-surface)" fillOpacity={0.28} />
            <CartesianGrid vertical={false} stroke="var(--border-subtle)" strokeDasharray="3 8" /><ReferenceLine y={0} stroke="var(--border-strong)" strokeWidth={1.5} /><ReferenceLine x={selectedPly} stroke="var(--forest)" strokeDasharray="3 5" strokeOpacity={0.55} />
            <XAxis dataKey="ply" tickCount={7} tickLine={false} axisLine={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} /><YAxis domain={[-TIMELINE_EVALUATION_LIMIT, TIMELINE_EVALUATION_LIMIT]} ticks={[-800, -400, 0, 400, 800]} tickFormatter={(value) => `${value / 100}`} tickLine={false} axisLine={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
            <Tooltip formatter={(_value, _name, item) => { const point = item.payload as EvaluationTimelinePoint; return [`${point.evaluationBeforeLabel ?? "—"} → ${point.evaluationAfterLabel ?? "—"}`, `${point.moveLabel}${point.qualitySymbol} · ${point.qualityLabel}`]; }} labelFormatter={() => ""} cursor={{ stroke: "var(--forest-light)", strokeDasharray: "3 5" }} contentStyle={{ border: "1px solid var(--border-subtle)", borderRadius: "16px", boxShadow: "var(--shadow-soft)" }} />
            <Line type="monotone" dataKey="displayEvaluation" connectNulls={false} stroke="var(--forest-light)" strokeWidth={3} dot={<TimelineDot />} activeDot={{ r: 7, fill: "var(--lime)", stroke: "var(--forest)", strokeWidth: 2 }} />
          </LineChart></ResponsiveContainer> : null}
        </div>
      )}
      <p className="sr-only">Timeline содержит {data.length - 1} оценок ходов с точки зрения пользователя. Критические моменты и качество каждого хода доступны в списке ходов ниже.</p>
    </BentoCard>
  );
}
