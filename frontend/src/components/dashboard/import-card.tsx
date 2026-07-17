"use client";

import { RefreshCw, Unplug, UserRoundCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { BentoCard, Button, Input, Select, ToastProvider, useToast } from "@/components/ui";
import { useChessComSync } from "@/hooks/use-chesscom-sync";
import { syncChessCom, updateAppSettings } from "@/lib/api";
import type { AppSettings } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

const monthOptions = [3, 6, 12].map((value) => ({ value: String(value), label: `${value} месяцев` }));

function ChessComCard({ settings }: { settings: AppSettings }) {
  const router = useRouter();
  const { toast } = useToast();
  const [username, setUsername] = useState(settings.chesscom_username ?? "");
  const [months, setMonths] = useState<3 | 6 | 12>(12);
  const [autoAnalyze, setAutoAnalyze] = useState(settings.auto_analyze_latest);
  const [autoSync, setAutoSync] = useState(settings.auto_sync_enabled);
  const [loading, setLoading] = useState(false);
  const connected = Boolean(settings.chesscom_username && settings.initial_sync_completed);
  useChessComSync({ enabled: connected && autoSync });

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = username.trim();
    if (!normalized) return toast({ tone: "warning", title: "Введите Chess.com username" });
    setLoading(true);
    try {
      await updateAppSettings({ chesscom_username: normalized, auto_sync_enabled: autoSync, auto_analyze_latest: autoAnalyze });
      const result = await syncChessCom({ username: normalized, mode: "initial", initial_months: months, auto_analyze_latest: autoAnalyze });
      toast({ tone: "success", title: `Загружено партий: ${result.imported}`, description: result.analysis_queued_game_id ? "Создаём отчёт для последней партии." : "История сохранена без массового анализа." });
      router.refresh();
    } catch {
      toast({ tone: "error", title: "Не удалось подключить Chess.com", description: "Проверьте username и доступность Chess.com." });
    } finally { setLoading(false); }
  }

  async function refreshGames() {
    setLoading(true);
    try {
      const result = await syncChessCom({ mode: "incremental" });
      toast({ tone: "success", title: result.imported ? `Загружено новых партий: ${result.imported}` : "Новых партий не найдено", description: result.analysis_queued_game_id ? "Создаём отчёт для последней партии." : undefined });
      router.refresh();
    } catch {
      toast({ tone: "error", title: "Не удалось обновить партии" });
    } finally { setLoading(false); }
  }

  async function savePreference(field: "auto_sync_enabled" | "auto_analyze_latest", value: boolean) {
    if (field === "auto_sync_enabled") setAutoSync(value); else setAutoAnalyze(value);
    try { await updateAppSettings({ [field]: value }); router.refresh(); }
    catch { toast({ tone: "error", title: "Не удалось сохранить настройку" }); }
  }

  async function saveUsername() {
    const normalized = username.trim();
    if (!normalized) return toast({ tone: "warning", title: "Введите Chess.com username" });
    setLoading(true);
    try {
      await updateAppSettings({ chesscom_username: normalized });
      toast({ tone: "success", title: "Username сохранён", description: "Существующая локальная история останется без изменений." });
      router.refresh();
    } catch { toast({ tone: "error", title: "Не удалось сохранить username" }); }
    finally { setLoading(false); }
  }

  if (!connected) return (
    <BentoCard as="section" id="import" className="h-full scroll-mt-8 p-6 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Chess.com</p>
      <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">Подключите Chess.com</h2>
      <p className="mt-2 text-sm leading-6 text-text-secondary">Введите username, чтобы быстро загрузить историю без ожидания Stockfish.</p>
      <form className="mt-6 space-y-5" onSubmit={connect}>
        <Input label="Chess.com username" value={username} onChange={(event) => setUsername(event.target.value)} disabled={loading} autoComplete="off" />
        <Select label="Начальный период" options={monthOptions} value={String(months)} onChange={(event) => setMonths(Number(event.target.value) as 3 | 6 | 12)} disabled={loading} />
        <label className="flex cursor-pointer items-start gap-3 text-sm text-text-secondary"><input type="checkbox" checked={autoAnalyze} onChange={(event) => setAutoAnalyze(event.target.checked)} disabled={loading} className="mt-0.5 size-5 accent-[var(--forest)]" /><span><strong className="font-semibold text-text-primary">Анализировать самую свежую новую партию</strong><br />Старая история не анализируется автоматически.</span></label>
        <Button type="submit" loading={loading} leftIcon={<UserRoundCheck size={17} />} className="w-full">{loading ? "Получаем историю Chess.com" : "Подключить и загрузить партии"}</Button>
      </form>
    </BentoCard>
  );

  return (
    <BentoCard as="section" id="import" tone="mint" className="h-full scroll-mt-8 p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-forest-light">Chess.com подключён</p><h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">{settings.chesscom_username}</h2></div><UserRoundCheck aria-hidden="true" className="text-forest" /></div>
      <p className="mt-5 text-sm text-text-secondary">Последняя синхронизация:<br /><strong className="text-text-primary">{formatDateTime(settings.last_sync_completed_at)}</strong></p>
      <Button className="mt-6 w-full" loading={loading} leftIcon={<RefreshCw size={17} />} onClick={refreshGames}>Обновить партии</Button>
      <div className="mt-6 space-y-3 border-t border-[var(--border-subtle)] pt-5">
        <label className="flex items-center justify-between gap-3 text-sm"><span>Автоматическая синхронизация</span><input type="checkbox" checked={autoSync} onChange={(event) => savePreference("auto_sync_enabled", event.target.checked)} className="size-5 accent-[var(--forest)]" /></label>
        <label className="flex items-center justify-between gap-3 text-sm"><span>Отчёт для свежей партии</span><input type="checkbox" checked={autoAnalyze} onChange={(event) => savePreference("auto_analyze_latest", event.target.checked)} className="size-5 accent-[var(--forest)]" /></label>
      </div>
      <details className="mt-5 rounded-2xl bg-white/60 p-4 text-sm">
        <summary className="cursor-pointer font-semibold text-forest">Изменить настройки</summary>
        <div className="mt-4 space-y-3"><Input label="Chess.com username" value={username} onChange={(event) => setUsername(event.target.value)} disabled={loading} /><p className="text-xs leading-5 text-text-muted">При смене username существующая локальная история не удаляется.</p><Button type="button" variant="secondary" size="sm" loading={loading} onClick={saveUsername}>Сохранить username</Button></div>
      </details>
      {!autoSync ? <p className="mt-4 flex items-center gap-2 text-xs text-text-muted"><Unplug size={14} /> Автообновление выключено</p> : <p className="mt-4 text-xs text-text-muted">Проверяем новые партии каждые 3 минуты, пока вкладка открыта.</p>}
    </BentoCard>
  );
}

export function ImportCard({ settings }: { settings: AppSettings }) {
  return <ToastProvider><ChessComCard settings={settings} /></ToastProvider>;
}
