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

export type GamesSort = "newest" | "oldest" | "most_blunders" | "highest_cp_loss";

export type GamesQuery = {
  limit?: number;
  offset?: number;
  result?: GameResult;
  opening?: string;
  analysisStatus?: AnalysisStatus;
  sort?: GamesSort;
};

export type AnalyzeGameResponse = {
  game_id: number;
  status: "queued" | "already_queued" | "already_analyzing" | "already_completed";
  task_id: string | null;
};

export type SystemStatus = {
  status: "ready" | "degraded";
  backend: "ready";
  app_environment: string;
  database: { status: "ready" | "degraded" | "unavailable"; backend: "sqlite" | "postgresql"; path: string | null; writable: boolean; tables_ready: boolean; schema_ready: boolean; migration_revision: string | null };
  stockfish: { status: "ready" | "unavailable"; path: string; executable: boolean };
  chesscom: { configured: boolean; user_agent_configured: boolean };
  analysis_queue: {
    backend: "local" | "cloud_tasks";
    status: "ready" | "degraded";
    configured: boolean;
    queue_name: string | null;
    worker_url_host: string | null;
  };
};

export type SyncStatus = "never" | "running" | "completed" | "failed";
export type SyncMode = "initial" | "incremental";
export type AppSettings = {
  chesscom_username: string | null;
  auto_sync_enabled: boolean;
  auto_analyze_latest: boolean;
  initial_sync_completed: boolean;
  last_sync_started_at: string | null;
  last_sync_completed_at: string | null;
  last_sync_status: SyncStatus;
  last_sync_error: string | null;
};
export type AppSettingsUpdate = {
  chesscom_username?: string;
  auto_sync_enabled?: boolean;
  auto_analyze_latest?: boolean;
};
export type ChessComSyncRequest = {
  username?: string;
  mode?: SyncMode;
  auto_analyze_latest?: boolean;
  initial_months?: 3 | 6 | 12;
};
export type ChessComSyncResponse = {
  mode: SyncMode;
  username: string;
  examined: number;
  imported: number;
  duplicates: number;
  invalid: number;
  imported_game_ids: number[];
  latest_game_id: number | null;
  analysis_queued_game_id: number | null;
  started_at: string;
  completed_at: string;
};

export type GameDetailResponse = {
  id: number;
  external_id: string;
  platform: string;
  played_at: string | null;
  white_username: string;
  black_username: string;
  white_rating: number | null;
  black_rating: number | null;
  user_color: UserColor;
  result: GameResult;
  opening_code: string | null;
  opening_name: string | null;
  time_control: string | null;
  pgn: string;
  analysis_status: AnalysisStatus;
  average_cp_loss: number | null;
  inaccuracies: number;
  mistakes: number;
  blunders: number;
};

export type MoveAnalysis = {
  id: number;
  game_id: number;
  ply: number;
  move_number: number;
  player_color: UserColor;
  is_user_move: boolean;
  fen_before: string;
  played_move_uci: string;
  played_move_san: string | null;
  best_move_uci: string | null;
  best_move_san: string | null;
  evaluation_before_cp: number | null;
  evaluation_after_cp: number | null;
  centipawn_loss: number;
  classification: MoveClassification;
  principal_variation: string | null;
  created_at: string;
};

export type GameMovesResponse = {
  game_id: number;
  analysis_status: AnalysisStatus;
  items: MoveAnalysis[];
};
