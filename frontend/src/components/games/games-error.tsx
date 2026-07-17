"use client";

import { RefreshCw, ServerOff } from "lucide-react";
import { useRouter } from "next/navigation";

import { BentoCard, Button } from "@/components/ui";
import { API_BASE_URL } from "@/lib/env";

export function GamesError() {
  const router = useRouter();
  return (
    <BentoCard as="section" tone="yellow" className="p-6 sm:p-10">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-4"><span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-white/70 text-mistake"><ServerOff aria-hidden="true" size={22} /></span><div><h1 className="text-2xl font-semibold tracking-[-0.04em]">Backend недоступен</h1><p className="mt-2 text-sm leading-6 text-text-secondary">Запустите FastAPI на <span className="technical-number">{API_BASE_URL}</span>. История партий не заменена пустым списком.</p></div></div>
        <Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={() => router.refresh()}>Повторить</Button>
      </div>
    </BentoCard>
  );
}
