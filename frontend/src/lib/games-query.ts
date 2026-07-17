import type { AnalysisStatus, GameResult, GamesQuery, GamesSort } from "@/lib/api/types";

export type GamesUrlState = {
  page: number;
  limit: 10 | 20 | 50;
  result?: GameResult;
  opening?: string;
  status?: AnalysisStatus;
  sort: GamesSort;
};

type RawSearchParams = Record<string, string | string[] | undefined>;
const results: GameResult[] = ["win", "draw", "loss"];
const statuses: AnalysisStatus[] = ["pending", "analyzing", "completed", "failed"];
const sorts: GamesSort[] = ["newest", "oldest", "most_blunders", "highest_cp_loss"];
const limits = [10, 20, 50] as const;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function parseGamesUrlState(raw: RawSearchParams): GamesUrlState {
  const parsedPage = Number.parseInt(first(raw.page) ?? "1", 10);
  const parsedLimit = Number.parseInt(first(raw.limit) ?? "20", 10);
  const result = first(raw.result);
  const status = first(raw.status);
  const sort = first(raw.sort);
  const opening = first(raw.opening)?.trim();
  return {
    page: Number.isFinite(parsedPage) && parsedPage >= 1 ? parsedPage : 1,
    limit: limits.includes(parsedLimit as 10 | 20 | 50) ? (parsedLimit as 10 | 20 | 50) : 20,
    result: results.includes(result as GameResult) ? (result as GameResult) : undefined,
    opening: opening || undefined,
    status: statuses.includes(status as AnalysisStatus) ? (status as AnalysisStatus) : undefined,
    sort: sorts.includes(sort as GamesSort) ? (sort as GamesSort) : "newest",
  };
}

export function toGamesApiQuery(state: GamesUrlState): GamesQuery {
  return {
    limit: state.limit,
    offset: (state.page - 1) * state.limit,
    result: state.result,
    opening: state.opening,
    analysisStatus: state.status,
    sort: state.sort,
  };
}

export function gamesStateToSearchParams(state: GamesUrlState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.page > 1) params.set("page", String(state.page));
  if (state.limit !== 20) params.set("limit", String(state.limit));
  if (state.result) params.set("result", state.result);
  if (state.opening) params.set("opening", state.opening);
  if (state.status) params.set("status", state.status);
  if (state.sort !== "newest") params.set("sort", state.sort);
  return params;
}
