"use client";

import { Download } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { BentoCard, Button, Input, Select, ToastProvider, useToast } from "@/components/ui";
import { importChessComGames, importErrorMessage, type ChessComImportResponse } from "@/lib/api";

const limitOptions = [5, 10, 20, 50].map((value) => ({ value: String(value), label: `${value} партий` }));

function ImportForm() {
  const router = useRouter();
  const { toast } = useToast();
  const [username, setUsername] = useState("Yeskendir");
  const [limit, setLimit] = useState<5 | 10 | 20 | 50>(10);
  const [analyze, setAnalyze] = useState(true);
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<ChessComImportResponse | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim()) {
      toast({ tone: "warning", title: "Введите Chess.com username" });
      return;
    }
    setLoading(true);
    try {
      const result = await importChessComGames({ username: username.trim(), limit, analyze });
      setLastResult(result);
      toast({
        tone: "success",
        title: `Импортировано партий: ${result.imported}`,
        description: `Дубликаты: ${result.skipped_duplicates} · Некорректные: ${result.skipped_invalid} · На анализ: ${result.analysis_queued}`,
      });
      router.refresh();
    } catch (error) {
      toast({ tone: "error", title: importErrorMessage(error), description: "Попробуйте повторить операцию позже." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <BentoCard as="section" className="h-full p-6 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Chess.com</p>
      <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">Импорт партий</h2>
      <form className="mt-6 space-y-5" onSubmit={submit}>
        <Input label="Username" value={username} onChange={(event) => setUsername(event.target.value)} disabled={loading} autoComplete="off" />
        <Select label="Количество" options={limitOptions} value={String(limit)} onChange={(event) => setLimit(Number(event.target.value) as 5 | 10 | 20 | 50)} disabled={loading} />
        <label className="flex cursor-pointer items-start gap-3 text-sm text-text-secondary">
          <input type="checkbox" checked={analyze} onChange={(event) => setAnalyze(event.target.checked)} disabled={loading} className="mt-0.5 size-5 accent-[var(--forest)]" />
          <span><strong className="font-semibold text-text-primary">Сразу анализировать Stockfish</strong><br />Анализ запустится в background после импорта.</span>
        </label>
        <Button type="submit" loading={loading} leftIcon={<Download size={17} />} className="w-full">
          Импортировать партии
        </Button>
      </form>
      {lastResult ? (
        <div className="mt-6 rounded-2xl bg-surface-muted p-4 text-xs leading-6 text-text-secondary" aria-live="polite">
          <p>Импортировано: <strong>{lastResult.imported}</strong></p>
          <p>Пропущено дубликатов: <strong>{lastResult.skipped_duplicates}</strong></p>
          <p>Поставлено на анализ: <strong>{lastResult.analysis_queued}</strong></p>
        </div>
      ) : null}
    </BentoCard>
  );
}

export function ImportCard() {
  return <ToastProvider><ImportForm /></ToastProvider>;
}
