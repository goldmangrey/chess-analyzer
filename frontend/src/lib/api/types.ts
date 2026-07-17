export type AnalysisStatus = "pending" | "analyzing" | "completed" | "failed";
export type GameResult = "win" | "draw" | "loss";
export type UserColor = "white" | "black";
export type MoveClassification = "normal" | "inaccuracy" | "mistake" | "blunder";

export type StatsSummary = {
  total_games: number;
  analyzed_games: number;
  wins: number;
  draws: number;
  losses: number;
  average_cp_loss: number | null;
  mistakes_total: number;
  blunders_total: number;
  mistakes_per_game: number | null;
  blunders_per_game: number | null;
  blunder_free_games: number;
  blunder_free_percentage: number | null;
};

export type StatsPeriodComparison = {
  recent_games_count: number;
  previous_games_count: number;
  recent_average_cp_loss: number | null;
  previous_average_cp_loss: number | null;
  average_cp_loss_change: number | null;
  recent_mistakes_per_game: number | null;
  previous_mistakes_per_game: number | null;
  mistakes_per_game_change: number | null;
  recent_blunders_per_game: number | null;
  previous_blunders_per_game: number | null;
  blunders_per_game_change: number | null;
};

export type OpeningWeakness = {
  opening_code: string | null;
  opening_name: string | null;
  games_count: number;
  wins: number;
  draws: number;
  losses: number;
  loss_rate: number;
  average_cp_loss: number;
  mistakes_per_game: number;
  blunders_per_game: number;
  weakness_score: number;
};

export type TrendPoint = {
  game_id: number;
  played_at: string | null;
  opponent: string;
  result: GameResult;
  user_color: UserColor;
  opening_code: string | null;
  opening_name: string | null;
  average_cp_loss: number;
  mistakes: number;
  blunders: number;
};

export type RecentGameStats = {
  game_id: number;
  played_at: string | null;
  opponent_username: string;
  user_color: UserColor;
  result: GameResult;
  opening_code: string | null;
  opening_name: string | null;
  time_control: string | null;
  analysis_status: AnalysisStatus;
  average_cp_loss: number | null;
  mistakes: number;
  blunders: number;
};

export type StatisticsDashboard = {
  summary: StatsSummary;
  comparison: StatsPeriodComparison;
  weakest_openings: OpeningWeakness[];
  trends: TrendPoint[];
  recent_games: RecentGameStats[];
};

export type ChessComImportRequest = {
  username: string;
  limit: 5 | 10 | 20 | 50;
  analyze: boolean;
};

export type ChessComImportResponse = {
  requested: number;
  imported: number;
  skipped_duplicates: number;
  skipped_invalid: number;
  examined: number;
  imported_game_ids: number[];
  analysis_queued: number;
};

export type ApiGameListItem = {
  id: number;
  played_at: string | null;
  opponent_username: string;
  user_color: UserColor;
  result: GameResult;
  white_rating: number | null;
  black_rating: number | null;
  opening_code: string | null;
  opening_name: string | null;
  time_control: string | null;
  analysis_status: AnalysisStatus;
  average_cp_loss: number | null;
  mistakes: number;
  blunders: number;
};

export type GamesListResponse = {
  items: ApiGameListItem[];
  limit: number;
  offset: number;
  returned_count: number;
  total: number;
};
