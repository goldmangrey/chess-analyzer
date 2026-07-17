"use client";

import { RefreshCw } from "lucide-react";
import Link from "next/link";

import { AppShell } from "@/components/layout";
import { BentoCard, Button } from "@/components/ui";

export default function AnalysisRouteError({ unstable_retry }: { error: Error & { digest?: string }; unstable_retry: () => void }) {
  return <AppShell activeSection="games" engineStatus="unavailable"><BentoCard as="section" tone="yellow" className="p-7 text-center sm:p-12"><h1 className="text-3xl font-semibold tracking-[-0.05em]">Не удалось отобразить анализ</h1><p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-text-secondary">Произошла неожиданная ошибка интерфейса. Технические детали скрыты.</p><div className="mt-7 flex flex-wrap justify-center gap-3"><Button leftIcon={<RefreshCw size={16} />} onClick={unstable_retry}>Повторить</Button><Link href="/games" className="focus-ring inline-flex min-h-11 items-center rounded-full px-5 text-sm font-semibold text-forest hover:bg-mint-surface">Все партии</Link></div></BentoCard></AppShell>;
}
