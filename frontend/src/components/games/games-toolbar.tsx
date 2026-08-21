"use client";

import { RotateCcw, Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Input, Select } from "@/components/ui";
import type { GamesUrlState } from "@/lib/games-query";

const resultOptions = [
  { value: "win", label: "Победа" }, { value: "draw", label: "Ничья" }, { value: "loss", label: "Поражение" },
];
const statusOptions = [
  { value: "pending", label: "Ожидает" }, { value: "analyzing", label: "Анализируется" }, { value: "completed", label: "Завершён" }, { value: "failed", label: "Ошибка" },
];
const sortOptions = [
  { value: "newest", label: "Сначала новые" }, { value: "oldest", label: "Сначала старые" }, { value: "most_blunders", label: "Больше зевков" }, { value: "highest_cp_loss", label: "Самые неточные" },
];
const limitOptions = [10, 20, 50].map((value) => ({ value: String(value), label: String(value) }));

export function GamesToolbar({ state }: { state: GamesUrlState }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [opening, setOpening] = useState(state.opening ?? "");

  function navigate(name: string, value: string, replace = false) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(name, value); else params.delete(name);
    params.delete("page");
    const url = params.size ? `${pathname}?${params}` : pathname;
    if (replace) router.replace(url, { scroll: false }); else router.push(url, { scroll: false });
  }

  useEffect(() => {
    const normalizedOpening = opening.trim();
    if (normalizedOpening === (state.opening ?? "")) return;
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (normalizedOpening) params.set("opening", normalizedOpening); else params.delete("opening");
      params.delete("page");
      router.replace(params.size ? `${pathname}?${params}` : pathname, { scroll: false });
    }, 400);
    return () => window.clearTimeout(timer);
  }, [opening, pathname, router, searchParams, state.opening]);

  const hasFilters = Boolean(state.opening || state.result || state.status || state.sort !== "newest");

  return (
    <section aria-label="Фильтры партий" className="rounded-[1.75rem] bg-surface p-4 shadow-[var(--shadow-soft)] sm:p-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(15rem,1.6fr)_1fr_1fr_1.2fr_0.65fr_auto] xl:items-end">
        <Input label="Поиск по дебюту" value={opening} onChange={(event) => setOpening(event.target.value)} prefix={<Search aria-hidden="true" size={16} />} placeholder="Sicilian или B90" />
        <Select label="Результат" placeholder="Все результаты" value={state.result ?? ""} onChange={(event) => navigate("result", event.target.value)} options={resultOptions} />
        <Select label="Статус" placeholder="Все статусы" value={state.status ?? ""} onChange={(event) => navigate("status", event.target.value)} options={statusOptions} />
        <Select label="Сортировка" value={state.sort} onChange={(event) => navigate("sort", event.target.value)} options={sortOptions} />
        <Select label="Строк" value={String(state.limit)} onChange={(event) => navigate("limit", event.target.value)} options={limitOptions} />
        {hasFilters ? <Button variant="ghost" leftIcon={<RotateCcw size={15} />} onClick={() => router.push("/games")}>Сбросить</Button> : <span />}
      </div>
    </section>
  );
}
