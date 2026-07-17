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
  const analyzing = status === "analyzing";
  const repeat = status === "completed";

  async function analyze() {
    setLoading(true);
    try {
      const result = await queueGameAnalysis(gameId);
      toast({
        tone: result.status === "already_analyzing" ? "info" : "success",
        title: result.status === "already_analyzing" ? "Партия уже анализируется" : "Анализ поставлен в очередь",
        description: result.status === "queued" ? `Партия #${gameId} будет обработана в background.` : undefined,
      });
      router.refresh();
    } catch (error) {
      const title = error instanceof ApiNetworkError
        ? "Backend недоступен"
        : error instanceof ApiError && error.status === 404
          ? "Партия не найдена"
          : "Не удалось запустить анализ";
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
