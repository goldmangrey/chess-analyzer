from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AnalysisStatus, Color, GameResult, MoveClassification


class CreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoveAnalysisCreate(CreateSchema):
    game_id: int = Field(ge=1)
    ply: int = Field(ge=1)
    move_number: int = Field(ge=1)
    player_color: Color
    is_user_move: bool
    fen_before: str = Field(min_length=1)
    played_move_uci: str = Field(min_length=1)
    played_move_san: str | None = None
    best_move_uci: str | None = None
    best_move_san: str | None = None
    evaluation_before_cp: int | None = None
    evaluation_after_cp: int | None = None
    centipawn_loss: int = Field(ge=0)
    classification: MoveClassification
    principal_variation: str | None = None


class MoveAnalysisRead(ReadSchema):
    id: int
    game_id: int
    ply: int
    move_number: int
    player_color: Color
    is_user_move: bool
    fen_before: str
    played_move_uci: str
    played_move_san: str | None
    best_move_uci: str | None
    best_move_san: str | None
    evaluation_before_cp: int | None
    evaluation_after_cp: int | None
    centipawn_loss: int
    classification: MoveClassification
    principal_variation: str | None
    created_at: datetime


class GameCreate(CreateSchema):
    external_id: str = Field(min_length=1)
    platform: str = Field(default="chess.com", min_length=1)
    played_at: datetime | None = None
    white_username: str = Field(min_length=1)
    black_username: str = Field(min_length=1)
    white_rating: int | None = None
    black_rating: int | None = None
    user_color: Color
    result: GameResult
    time_control: str | None = None
    opening_code: str | None = None
    opening_name: str | None = None
    pgn: str = Field(min_length=1)
    analysis_status: AnalysisStatus = AnalysisStatus.PENDING
    analyzed_at: datetime | None = None


class GameListItem(ReadSchema):
    id: int
    external_id: str
    platform: str
    played_at: datetime | None = None
    white_username: str
    black_username: str
    white_rating: int | None = None
    black_rating: int | None = None
    user_color: Color
    result: GameResult
    time_control: str | None = None
    opening_code: str | None = None
    opening_name: str | None = None
    analysis_status: AnalysisStatus
    created_at: datetime
    updated_at: datetime
    analyzed_at: datetime | None = None


class GameRead(GameListItem):
    pgn: str
    move_analyses: list[MoveAnalysisRead] = Field(default_factory=list)


class StatisticsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StatsSummary(StatisticsSchema):
    total_games: int
    analyzed_games: int
    wins: int
    draws: int
    losses: int
    average_cp_loss: float | None
    mistakes_total: int
    blunders_total: int
    mistakes_per_game: float | None
    blunders_per_game: float | None
    blunder_free_games: int
    blunder_free_percentage: float | None


class StatsPeriodComparison(StatisticsSchema):
    recent_games_count: int
    previous_games_count: int
    recent_average_cp_loss: float | None
    previous_average_cp_loss: float | None
    average_cp_loss_change: float | None
    recent_mistakes_per_game: float | None
    previous_mistakes_per_game: float | None
    mistakes_per_game_change: float | None
    recent_blunders_per_game: float | None
    previous_blunders_per_game: float | None
    blunders_per_game_change: float | None


class OpeningWeakness(StatisticsSchema):
    opening_code: str | None
    opening_name: str | None
    games_count: int
    wins: int
    draws: int
    losses: int
    loss_rate: float
    average_cp_loss: float
    mistakes_per_game: float
    blunders_per_game: float
    weakness_score: float


class TrendPoint(StatisticsSchema):
    game_id: int
    played_at: datetime | None
    opponent: str
    result: GameResult
    user_color: Color
    opening_code: str | None
    opening_name: str | None
    average_cp_loss: float
    mistakes: int
    blunders: int


class RecentGameStats(StatisticsSchema):
    game_id: int
    played_at: datetime | None
    opponent_username: str
    user_color: Color
    result: GameResult
    opening_code: str | None
    opening_name: str | None
    time_control: str | None
    analysis_status: AnalysisStatus
    average_cp_loss: float | None
    mistakes: int
    blunders: int


class StatisticsDashboard(StatisticsSchema):
    summary: StatsSummary
    comparison: StatsPeriodComparison
    weakest_openings: tuple[OpeningWeakness, ...]
    trends: tuple[TrendPoint, ...]
    recent_games: tuple[RecentGameStats, ...]


class ApiSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChessComImportRequest(ApiSchema):
    username: str | None = None
    limit: int | None = Field(default=None, ge=1, le=50)
    analyze: bool = True

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("username must not be empty")
        return value.strip() if value is not None else None


class ChessComImportResponse(ApiSchema):
    requested: int
    imported: int
    skipped_duplicates: int
    skipped_invalid: int
    examined: int
    imported_game_ids: tuple[int, ...]
    analysis_queued: int


class AnalyzeGameResponse(ApiSchema):
    game_id: int
    status: str


class ApiGameListItem(ApiSchema):
    id: int
    played_at: datetime | None
    opponent_username: str
    user_color: Color
    result: GameResult
    white_rating: int | None
    black_rating: int | None
    opening_code: str | None
    opening_name: str | None
    time_control: str | None
    analysis_status: AnalysisStatus
    average_cp_loss: float | None
    mistakes: int
    blunders: int


class GamesListResponse(ApiSchema):
    items: tuple[ApiGameListItem, ...]
    limit: int
    offset: int
    returned_count: int
    total: int


class GameDetailResponse(ApiSchema):
    id: int
    external_id: str
    platform: str
    played_at: datetime | None
    white_username: str
    black_username: str
    white_rating: int | None
    black_rating: int | None
    user_color: Color
    result: GameResult
    opening_code: str | None
    opening_name: str | None
    time_control: str | None
    pgn: str
    analysis_status: AnalysisStatus
    average_cp_loss: float | None
    inaccuracies: int
    mistakes: int
    blunders: int


class GameMovesResponse(ApiSchema):
    game_id: int
    analysis_status: AnalysisStatus
    items: tuple[MoveAnalysisRead, ...]


class TrendsResponse(ApiSchema):
    items: tuple[TrendPoint, ...]


class OpeningsResponse(ApiSchema):
    items: tuple[OpeningWeakness, ...]


class ApiErrorResponse(ApiSchema):
    error: str
    message: str


class DatabaseStatus(ApiSchema):
    status: str
    path: str
    writable: bool
    tables_ready: bool


class StockfishStatus(ApiSchema):
    status: str
    path: str
    executable: bool


class ChessComStatus(ApiSchema):
    configured: bool
    user_agent_configured: bool


class SystemStatusResponse(ApiSchema):
    status: str
    backend: str
    database: DatabaseStatus
    stockfish: StockfishStatus
    chesscom: ChessComStatus
