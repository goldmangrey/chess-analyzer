export type SearchParamValue = string | string[] | undefined;

export function gameMomentHref(gameId: number, ply: number): string {
  return `/games/${gameId}?ply=${ply}`;
}

export function parseInitialSelectedPly(value: SearchParamValue, maxPly: number): number {
  if (Array.isArray(value) || typeof value !== "string" || !/^\d+$/.test(value)) return 0;
  const ply = Number(value);
  return Number.isSafeInteger(ply) && ply >= 0 && ply <= maxPly ? ply : 0;
}
