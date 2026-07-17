"use client";

import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui";

export function GamesRefreshButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return <Button variant="secondary" loading={pending} leftIcon={<RefreshCw size={16} />} onClick={() => startTransition(() => router.refresh())}>Обновить</Button>;
}
