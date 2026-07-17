"use client";

import { X } from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  useSyncExternalStore,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import { IconButton } from "@/components/ui/icon-button";

export type ModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
};

const focusableSelector =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const subscribeToMount = () => () => undefined;

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: ModalProps) {
  const mounted = useSyncExternalStore(subscribeToMount, () => true, () => false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) return;

    returnFocusRef.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => {
      const focusable = dialogRef.current?.querySelector<HTMLElement>(focusableSelector);
      (focusable ?? dialogRef.current)?.focus();
    });

    return () => {
      document.body.style.overflow = previousOverflow;
      returnFocusRef.current?.focus();
    };
  }, [open]);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onOpenChange(false);
      return;
    }

    if (event.key !== "Tab" || !dialogRef.current) return;
    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector),
    );
    if (focusable.length === 0) {
      event.preventDefault();
      dialogRef.current.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  if (!mounted || !open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onOpenChange(false);
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="w-full max-w-lg rounded-[1.75rem] border border-white/60 bg-surface p-5 shadow-[0_24px_80px_rgba(0,0,0,0.16)] outline-none sm:p-7"
      >
        <div className="flex items-start justify-between gap-5">
          <div>
            <h2 id={titleId} className="text-2xl font-semibold tracking-[-0.04em]">
              {title}
            </h2>
            {description ? (
              <p id={descriptionId} className="mt-2 text-sm leading-6 text-text-secondary">
                {description}
              </p>
            ) : null}
          </div>
          <IconButton
            label="Закрыть диалог"
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            <X aria-hidden="true" size={18} />
          </IconButton>
        </div>
        <div className="mt-6">{children}</div>
        {footer ? <div className="mt-7 flex flex-wrap justify-end gap-3">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}
