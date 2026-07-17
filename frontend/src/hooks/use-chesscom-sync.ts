"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

import { syncChessCom } from "@/lib/api";
import { useToast } from "@/components/ui";

export function useChessComSync({ enabled, intervalMs = 180_000 }: { enabled: boolean; intervalMs?: number }) {
  const router = useRouter();
  const { toast } = useToast();
  const running = useRef(false);
  const warned = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    const synchronize = async () => {
      if (document.visibilityState !== "visible" || running.current) return;
      running.current = true;
      try {
        const result = await syncChessCom({ mode: "incremental" });
        if (result.imported > 0) {
          toast({ tone: "success", title: `Загружено новых партий: ${result.imported}` });
          router.refresh();
        }
      } catch {
        if (!warned.current) {
          warned.current = true;
          toast({ tone: "warning", title: "Фоновая синхронизация временно недоступна" });
        }
      } finally {
        running.current = false;
      }
    };
    const timer = window.setInterval(synchronize, intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs, router, toast]);
}
