"use client";

import { RefreshCw, ServerOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { BentoCard, Button } from "@/components/ui";
import { API_BASE_URL } from "@/lib/env";

export function AnalysisError() {
  const router = useRouter();
  return <BentoCard as="section" tone="yellow" className="p-7 sm:p-10"><div className="flex gap-4"><span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-white/70 text-mistake"><ServerOff aria-hidden="true" size={22} /></span><div><h1 className="text-2xl font-semibold tracking-[-0.04em]">Не удалось загрузить анализ</h1><p className="mt-2 text-sm leading-6 text-text-secondary">Проверьте локальный backend на <span className="technical-number">{API_BASE_URL}</span>. Это состояние не считается отсутствующей партией.</p><div className="mt-6 flex flex-wrap gap-3"><Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={() => router.refresh()}>Повторить</Button><Link href="/games" className="focus-ring inline-flex min-h-11 items-center rounded-full px-5 text-sm font-semibold text-forest hover:bg-mint-surface">Все партии</Link></div></div></div></BentoCard>;
}
