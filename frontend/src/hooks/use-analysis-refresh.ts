"use client";

import { useEffect, useRef } from "react";

type AnalysisRefreshOptions = {
  enabled: boolean;
  onRefresh: () => void;
  intervalMs?: number;
  maxDurationMs?: number;
};

export function useAnalysisRefresh({
  enabled,
  onRefresh,
  intervalMs = 5_000,
  maxDurationMs = 10 * 60_000,
}: AnalysisRefreshOptions) {
  const refreshRef = useRef(onRefresh);

  useEffect(() => {
    refreshRef.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    if (!enabled) return;
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      if (Date.now() - startedAt >= maxDurationMs) {
        window.clearInterval(timer);
        return;
      }
      if (document.visibilityState === "visible") refreshRef.current();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs, maxDurationMs]);
}
