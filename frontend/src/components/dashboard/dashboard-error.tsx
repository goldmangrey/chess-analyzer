"use client";

import { RefreshCw, ServerOff, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";

import { BentoCard, Button } from "@/components/ui";
import { API_BASE_URL } from "@/lib/env";
import type { AppSettings } from "@/lib/api/types";

import { ImportCard } from "./import-card";

export function DashboardError({ kind, settings }: { kind: "network" | "dashboard"; settings: AppSettings | null }) {
  const router = useRouter();
  const networkFailure = kind === "network";
  const Icon = networkFailure ? ServerOff : TriangleAlert;
  const error = (
    <BentoCard as="section" tone="yellow" className="p-6 sm:p-10">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-4"><span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-white/70 text-mistake"><Icon aria-hidden="true" size={22} /></span><div><h1 className="text-2xl font-semibold tracking-[-0.04em]">{networkFailure ? "Backend недоступен" : "Не удалось загрузить статистику"}</h1><p className="mt-2 text-sm leading-6 text-text-secondary">{networkFailure ? <>Не удалось подключиться к FastAPI на <span className="technical-number">{API_BASE_URL}</span>.</> : "Dashboard API вернул ошибку. Остальные доступные данные приложения сохранены."}</p></div></div>
        <Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={() => router.refresh()}>Повторить</Button>
      </div>
    </BentoCard>
  );
  if (!settings) return error;
  return <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">{error}<ImportCard settings={settings} /></div>;
}
