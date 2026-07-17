"use client";

import { useSyncExternalStore } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { BentoCard } from "@/components/ui";
import type { TrendPoint } from "@/lib/api/types";
import { formatCpLoss, formatDate } from "@/lib/format";

const subscribe = () => () => undefined;

export function PerformanceChart({ trends }: { trends: TrendPoint[] }) {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  if (trends.length < 2) {
    return (
      <BentoCard as="section" className="h-full min-h-80 p-6 sm:p-8">
        <h2 className="text-2xl font-semibold tracking-[-0.04em]">Динамика формы</h2>
        <div className="grid min-h-56 place-items-center text-center text-sm text-text-muted">Недостаточно данных для графика</div>
      </BentoCard>
    );
  }

  const data = trends.map((point, index) => ({ ...point, order: index + 1, dateLabel: formatDate(point.played_at) }));

  return (
    <BentoCard as="section" className="h-full p-6 sm:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Последние {trends.length} партий</p><h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">Динамика CP Loss</h2></div>
        <p className="text-xs text-text-muted">Старые → новые</p>
      </div>
      <div className="mt-7 h-72" aria-label="График среднего CP Loss по последним партиям">
        {mounted ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid vertical={false} stroke="var(--border-subtle)" strokeDasharray="4 6" />
              <XAxis dataKey="order" tickLine={false} axisLine={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
              <Tooltip
                formatter={(value) => [formatCpLoss(typeof value === "number" ? value : null), "CP Loss"]}
                labelFormatter={(_, payload) => payload[0]?.payload?.dateLabel ?? "Партия"}
                contentStyle={{ border: "1px solid var(--border-subtle)", borderRadius: "16px", boxShadow: "var(--shadow-soft)", fontFamily: "var(--font-sans)" }}
              />
              <Line type="monotone" dataKey="average_cp_loss" stroke="var(--forest-light)" strokeWidth={3} dot={{ r: 3, fill: "var(--surface)", strokeWidth: 2 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : null}
      </div>
      <p className="sr-only">Минимальный CP Loss: {formatCpLoss(Math.min(...trends.map((point) => point.average_cp_loss)))}. Максимальный: {formatCpLoss(Math.max(...trends.map((point) => point.average_cp_loss)))}.</p>
    </BentoCard>
  );
}
