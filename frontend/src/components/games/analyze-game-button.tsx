"use client";

import { RefreshCw, ScanSearch } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, ApiNetworkError, queueGameAnalysis } from "@/lib/api";
import type { AnalysisStatus } from "@/lib/api/types";
import { useToast } from "@/components/ui/toast";

export function AnalyzeGameButton({ gameId, status }: { gameId: number; status: AnalysisStatus }) {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const analyzing = ["queued", "processing", "analyzing"].includes(status);
  const repeat = status === "completed";

  async function analyze() {
    setLoading(true);
    try {
      const result = await queueGameAnalysis(gameId, repeat);
      const messages = {
        queued: "Отчёт поставлен в очередь",
        already_queued: "Отчёт уже поставлен в очередь",
        already_analyzing: "Отчёт уже создаётся",
        already_completed: "Отчёт уже готов",
      } as const;
      toast({
        tone: result.status === "queued" ? "success" : "info",
        title: messages[result.status],
      });
      router.refresh();
    } catch (error) {
      const title = error instanceof ApiNetworkError
        ? "Backend недоступен"
        : error instanceof ApiError && error.status === 404
          ? "Партия не найдена"
          : "Не удалось поставить отчёт в очередь";
      toast({ tone: "error", title });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button
      variant={repeat ? "ghost" : "secondary"}
      size="sm"
      loading={loading}
      disabled={analyzing}
      leftIcon={repeat ? <RefreshCw size={14} /> : <ScanSearch size={14} />}
      onClick={analyze}
    >
      {analyzing ? "Создаём отчёт" : repeat ? "Повторить анализ" : status === "failed" ? "Повторить" : "Получить отчёт"}
    </Button>
  );
}
