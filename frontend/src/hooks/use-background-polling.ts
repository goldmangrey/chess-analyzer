"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type BackgroundPollingOptions<T> = {
  enabled?: boolean;
  intervalMs: number;
  fetcher: (signal: AbortSignal) => Promise<T>;
  onSuccess: (value: T) => void;
};

export function useBackgroundPolling<T>({ enabled = true, intervalMs, fetcher, onSuccess }: BackgroundPollingOptions<T>) {
  const fetcherRef = useRef(fetcher);
  const successRef = useRef(onSuccess);
  const runningRef = useRef(false);
  const timerRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastError, setLastError] = useState<unknown>(null);

  useEffect(() => { fetcherRef.current = fetcher; }, [fetcher]);
  useEffect(() => { successRef.current = onSuccess; }, [onSuccess]);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const runRef = useRef<() => Promise<void>>(async () => undefined);

  useEffect(() => {
    if (!enabled) return;
    let active = true;

    const schedule = () => {
      clearTimer();
      if (!active || document.hidden) return;
      timerRef.current = window.setTimeout(() => void runRef.current(), intervalMs);
    };

    runRef.current = async () => {
      if (!active || document.hidden || runningRef.current) return;
      runningRef.current = true;
      setIsRefreshing(true);
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const value = await fetcherRef.current(controller.signal);
        if (active) {
          successRef.current(value);
          setLastError(null);
        }
      } catch (error) {
        if (active && !controller.signal.aborted) setLastError(error);
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        runningRef.current = false;
        if (active) setIsRefreshing(false);
        schedule();
      }
    };

    const onVisibilityChange = () => {
      clearTimer();
      if (!document.hidden) void runRef.current();
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    schedule();
    return () => {
      active = false;
      clearTimer();
      abortRef.current?.abort();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [clearTimer, enabled, intervalMs]);

  return { isRefreshing, lastError, refresh: () => runRef.current() };
}
