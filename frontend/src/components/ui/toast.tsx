"use client";

import { Check, Info, TriangleAlert, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/cn";

export type ToastTone = "success" | "error" | "info" | "warning";
export type ToastInput = { title: string; description?: string; tone?: ToastTone };
type ToastItem = ToastInput & { id: number };
type ToastContextValue = { toast: (input: ToastInput) => void };

const ToastContext = createContext<ToastContextValue | null>(null);
const toneClasses: Record<ToastTone, string> = {
  success: "bg-best-surface text-best",
  error: "bg-blunder-surface text-blunder",
  info: "bg-mint-surface text-forest",
  warning: "bg-inaccuracy-surface text-inaccuracy-text",
};

function ToastIcon({ tone }: { tone: ToastTone }) {
  const props = { size: 18, "aria-hidden": true } as const;
  if (tone === "success") return <Check {...props} />;
  if (tone === "error" || tone === "warning") return <TriangleAlert {...props} />;
  return <Info {...props} />;
}

export function ToastProvider({ children, limit = 4 }: { children: ReactNode; limit?: number }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback(
    (input: ToastInput) => {
      const id = ++nextId.current;
      setItems((current) => [...current, { ...input, id }].slice(-limit));
      window.setTimeout(() => dismiss(id), 4500);
    },
    [dismiss, limit],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-3"
      >
        {items.map((item) => {
          const tone = item.tone ?? "info";
          return (
            <div
              key={item.id}
              role={tone === "error" ? "alert" : "status"}
              className="pointer-events-auto flex items-start gap-3 rounded-[1.25rem] border border-[var(--border-subtle)] bg-surface p-4 shadow-[var(--shadow-soft)] motion-safe:animate-[toast-in_180ms_ease-out]"
            >
              <span className={cn("mt-0.5 rounded-full p-1.5", toneClasses[tone])}>
                <ToastIcon tone={tone} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-text-primary">{item.title}</p>
                {item.description ? (
                  <p className="mt-1 text-xs leading-5 text-text-secondary">{item.description}</p>
                ) : null}
              </div>
              <button
                type="button"
                aria-label="Закрыть уведомление"
                onClick={() => dismiss(item.id)}
                className="focus-ring rounded-lg p-1 text-text-muted hover:bg-black/[0.05] hover:text-text-primary"
              >
                <X aria-hidden="true" size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
