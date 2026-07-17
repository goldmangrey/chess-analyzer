"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { IconButton } from "@/components/ui";

function visiblePages(current: number, total: number): number[] {
  const start = Math.max(1, Math.min(current - 2, total - 4));
  const end = Math.min(total, start + 4);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

export function GamesPagination({ total, limit, offset }: { total: number; limit: number; offset: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  if (total === 0) return null;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const startItem = offset + 1;
  const endItem = Math.min(offset + limit, total);

  function goTo(page: number) {
    const params = new URLSearchParams(searchParams.toString());
    if (page <= 1) params.delete("page"); else params.set("page", String(page));
    router.push(params.size ? `${pathname}?${params}` : pathname, { scroll: true });
  }

  return (
    <nav aria-label="Пагинация партий" className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-[1.5rem] bg-surface px-4 py-3 shadow-[var(--shadow-soft)]">
      <p className="text-sm text-text-secondary">Показано {startItem}–{endItem} из {total}</p>
      <div className="flex items-center gap-1.5">
        <IconButton label="Предыдущая страница" size="sm" variant="ghost" disabled={currentPage === 1} onClick={() => goTo(currentPage - 1)}><ChevronLeft aria-hidden="true" size={17} /></IconButton>
        <div className="hidden items-center gap-1 sm:flex">
          {visiblePages(currentPage, totalPages).map((page) => (
            <button key={page} type="button" aria-current={page === currentPage ? "page" : undefined} onClick={() => goTo(page)} className={page === currentPage ? "focus-ring size-9 rounded-xl bg-surface-dark text-sm font-semibold text-white" : "focus-ring size-9 rounded-xl text-sm font-semibold text-text-secondary hover:bg-surface-muted"}>{page}</button>
          ))}
        </div>
        <span className="technical-number px-2 text-sm sm:hidden">{currentPage} / {totalPages}</span>
        <IconButton label="Следующая страница" size="sm" variant="ghost" disabled={currentPage === totalPages} onClick={() => goTo(currentPage + 1)}><ChevronRight aria-hidden="true" size={17} /></IconButton>
      </div>
    </nav>
  );
}
