"use client";

import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui";

export function AnalysisRefreshButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return <Button variant="ghost" size="sm" loading={pending} leftIcon={<RefreshCw size={15} />} onClick={() => startTransition(() => router.refresh())}>Обновить данные</Button>;
}
