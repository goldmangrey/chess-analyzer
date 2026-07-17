"use client";

import { RefreshCw } from "lucide-react";

import { AppShell } from "@/components/layout";
import { BentoCard, Button } from "@/components/ui";

export default function GamesRouteError({ unstable_retry }: { error: Error & { digest?: string }; unstable_retry: () => void }) {
  return (
    <AppShell activeSection="games" engineStatus="unavailable">
      <BentoCard as="section" tone="yellow" className="p-7 text-center sm:p-12"><h1 className="text-3xl font-semibold tracking-[-0.05em]">Не удалось отобразить партии</h1><p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-text-secondary">Произошла неожиданная ошибка интерфейса. Технические детали скрыты.</p><Button className="mt-7" leftIcon={<RefreshCw size={16} />} onClick={unstable_retry}>Повторить</Button></BentoCard>
    </AppShell>
  );
}
