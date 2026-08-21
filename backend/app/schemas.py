from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from app.models import (
    AnalysisStatus,
    Color,
    CriticalMomentType,
    ErrorConfidence,
    ErrorType,
    GamePhase,
    GameResult,
    MoveClassification,
    OverallDirection,
    PlayerIntelligenceStatus,
    PlayerStrengthType,
    ProfileConfidenceLevel,
    TimeControlSegment,
    TrendDirection,
    SyncStatus,
)


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
    phase: GamePhase | None = None
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
    phase: GamePhase | None
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
    analyze: bool = False

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
    task_id: str | None = None


class AnalyzeGameRequest(ApiSchema):
    force: bool = False


class AnalyzeGameTaskRequest(ApiSchema):
    game_id: int = Field(gt=0)
    force: bool = False
    schema_version: Literal[1] = 1


class AnalyzeGameTaskResponse(ApiSchema):
    game_id: int
    status: Literal["completed", "already_completed"]


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


class GamePhaseStatistics(ApiSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    start_ply: int
    end_ply: int
    user_moves: int
    average_cp_loss: float | None
    accuracy: float | None = None
    accuracy_eligible_moves: int = 0
    accuracy_coverage_rate: float | None = None
    accuracy_quality_band: Literal["excellent", "good", "fair", "poor"] | None = None
    inaccuracies: int
    mistakes: int
    blunders: int


class CriticalMomentResponse(ApiSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    ply: int
    move_number: int
    move_san: str | None
    move_uci: str
    phase: GamePhase | None
    type: CriticalMomentType
    severity: MoveClassification
    centipawn_loss: int
    evaluation_before: int
    evaluation_after: int
    evaluation_before_user_pov: int
    evaluation_after_user_pov: int
    importance_score: float


class ErrorClassificationResponse(ApiSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    ply: int
    move_number: int
    move_san: str | None
    phase: GamePhase | None
    severity: MoveClassification
    primary_type: ErrorType | None
    secondary_types: tuple[ErrorType, ...]
    confidence: ErrorConfidence
    centipawn_loss: int
    critical_moment_type: CriticalMomentType | None


class IntelligenceSchema(ApiSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class IntelligenceAnalysisResponse(IntelligenceSchema):
    status: AnalysisStatus
    intelligence_ready: bool


class IntelligenceGameResponse(IntelligenceSchema):
    id: int
    external_id: str
    platform: str
    played_at: datetime | None
    result: GameResult
    user_color: Color
    opponent: str
    white_username: str
    black_username: str
    white_rating: int | None
    black_rating: int | None
    time_control: str | None


class IntelligenceOpeningResponse(IntelligenceSchema):
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    subvariation: str | None
    deepest_match_ply: int | None
    deepest_match_move_san: str | None
    last_named_match_ply: int | None
    last_named_match_move_san: str | None
    last_sequence_book_ply: int | None
    last_sequence_book_move_san: str | None
    first_deviation_ply: int | None
    first_deviation_move_san: str | None
    transposition_reentry: bool
    first_reentry_ply: int | None


class MoveCommentaryResponse(IntelligenceSchema):
    headline: str
    summary: str
    details: tuple[str, ...]
    recommendation: str | None
    intent: str


class MoveHumanMetricsResponse(IntelligenceSchema):
    win_percent_before: float
    win_percent_after: float
    win_percent_loss: float
    accuracy: float
    quality_band: Literal["excellent", "good", "fair", "poor"]


class MoveReviewEntryResponse(IntelligenceSchema):
    ply: int
    commentary: MoveCommentaryResponse
    opening_status: Literal["book", "deviation", "post_book", "reentry"] | None
    human_metrics: MoveHumanMetricsResponse | None


class IntelligenceSummaryResponse(IntelligenceSchema):
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_total_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: Literal["excellent", "good", "fair", "poor"] | None
    user_moves: int
    inaccuracies: int
    mistakes: int
    blunders: int


class GameIntelligenceResponse(IntelligenceSchema):
    intelligence_version: str
    human_metrics_version: str
    analysis: IntelligenceAnalysisResponse
    game: IntelligenceGameResponse
    opening: IntelligenceOpeningResponse
    summary: IntelligenceSummaryResponse | None
    phases: dict[GamePhase, GamePhaseStatistics]
    critical_moments: tuple[CriticalMomentResponse, ...]
    errors: tuple[ErrorClassificationResponse, ...]
    error_breakdown: dict[ErrorType, int]
    move_reviews: tuple[MoveReviewEntryResponse, ...]


class PlayerIntelligenceWindowResponse(IntelligenceSchema):
    requested_games: int = Field(description="Requested current/recent game window.")
    available_analyzed_games: int = Field(
        description="Backward-compatible alias for selected_games."
    )
    selected_games: int = Field(
        description="Completed analyzed games selected into the current profile."
    )
    total_available_analyzed_games: int = Field(
        description="All completed analyzed games available before window limiting."
    )


class PlayerIntelligenceSampleResponse(IntelligenceSchema):
    games: int
    user_moves: int
    white_games: int
    black_games: int
    wins: int
    draws: int
    losses: int


class PlayerIntelligenceOverallResponse(IntelligenceSchema):
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: Literal["excellent", "good", "fair", "poor"] | None
    inaccuracies: int
    mistakes: int
    blunders: int
    inaccuracies_per_game: float | None
    mistakes_per_game: float | None
    blunders_per_game: float | None
    inaccuracies_per_100_moves: float | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    blunder_free_games: int
    blunder_free_rate: float | None


class PlayerIntelligenceDataQualityResponse(IntelligenceSchema):
    games_with_move_analysis: int
    games_with_phase_data: int
    games_with_complete_evaluations: int
    moves_with_cp_loss: int
    moves_with_classification: int
    games_with_taxonomy_data: int
    moves_eligible_for_taxonomy: int
    moves_with_primary_taxonomy: int
    moves_with_phase: int
    moves_without_phase: int
    games_with_known_time_control: int
    games_with_known_color: int
    moves_eligible_for_accuracy: int
    accuracy_coverage_rate: float | None


class RecurringErrorSeverityResponse(IntelligenceSchema):
    inaccuracies: int
    mistakes: int
    blunders: int


class RecurringErrorPhasesResponse(IntelligenceSchema):
    opening: int
    middlegame: int
    endgame: int
    unknown: int


class RecurringErrorEvidenceResponse(IntelligenceSchema):
    game_id: int
    ply: int
    classification: MoveClassification
    phase: GamePhase | None
    played_move_san: str | None
    played_move_uci: str
    centipawn_loss: int


class RecurringErrorResponse(IntelligenceSchema):
    taxonomy: ErrorType
    incidents: int
    games_affected: int
    games_affected_rate: float | None
    incidents_per_game: float | None
    incidents_per_100_moves: float | None
    severity: RecurringErrorSeverityResponse
    phases: RecurringErrorPhasesResponse
    evidence: tuple[RecurringErrorEvidenceResponse, ...]


class ProfileConfidenceResponse(IntelligenceSchema):
    level: ProfileConfidenceLevel
    score: float
    sample_games: int
    eligible_games: int
    coverage_rate: float | None
    eligible_user_moves: int


class WeaknessComponentsResponse(IntelligenceSchema):
    spread: float
    frequency: float
    severity: float
    recurrence: float


class WeaknessEvidenceSummaryResponse(IntelligenceSchema):
    incidents: int
    games_affected: int
    games_affected_rate: float | None
    incidents_per_100_moves: float | None


class PlayerWeaknessResponse(IntelligenceSchema):
    taxonomy: ErrorType
    score: float
    rank: int
    confidence: ProfileConfidenceResponse
    components: WeaknessComponentsResponse
    evidence_summary: WeaknessEvidenceSummaryResponse
    evidence: tuple[RecurringErrorEvidenceResponse, ...]


class PlayerStrengthResponse(IntelligenceSchema):
    type: PlayerStrengthType
    score: float
    rank: int
    confidence: ProfileConfidenceResponse
    normalized_component: float
    metrics: dict[str, float]


class PlayerPhaseMetricsResponse(IntelligenceSchema):
    user_moves: int
    games_with_phase: int
    participation_rate: float | None
    moves_with_cp_loss: int
    moves_with_classification: int
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: Literal["excellent", "good", "fair", "poor"] | None
    inaccuracies: int
    mistakes: int
    blunders: int
    inaccuracies_per_100_moves: float | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    serious_errors: int
    serious_errors_per_100_moves: float | None


class PhaseScoreComponentsResponse(IntelligenceSchema):
    acpl: float | None
    serious_error_rate: float | None


class PhasePerformanceResponse(IntelligenceSchema):
    phase: GamePhase
    weakness_score: float | None
    components: PhaseScoreComponentsResponse
    confidence: ProfileConfidenceResponse


class FirstSeriousBreakdownResponse(IntelligenceSchema):
    eligible_games: int
    games_with_serious_error: int
    opening: int
    middlegame: int
    endgame: int
    unknown: int
    no_serious_error: int
    opening_share: float | None
    middlegame_share: float | None
    endgame_share: float | None
    unknown_share: float | None


class PhaseProfileResponse(IntelligenceSchema):
    performance: dict[GamePhase, PhasePerformanceResponse]
    strongest_phase: PhasePerformanceResponse | None
    weakest_phase: PhasePerformanceResponse | None
    first_serious_breakdown: FirstSeriousBreakdownResponse


class TrendConfidenceResponse(IntelligenceSchema):
    level: ProfileConfidenceLevel
    score: float
    recent_games: int
    previous_games: int
    recent_user_moves: int
    previous_user_moves: int
    coverage_rate: float | None


class MetricTrendResponse(IntelligenceSchema):
    recent: float | None
    previous: float | None
    absolute_change: float | None
    relative_change: float | None
    direction: TrendDirection
    confidence: TrendConfidenceResponse


class OverallTrendsResponse(IntelligenceSchema):
    average_cp_loss: MetricTrendResponse
    accuracy: MetricTrendResponse
    inaccuracies_per_100_moves: MetricTrendResponse
    mistakes_per_100_moves: MetricTrendResponse
    blunders_per_100_moves: MetricTrendResponse
    serious_errors_per_100_moves: MetricTrendResponse
    blunder_free_rate: MetricTrendResponse


class PhaseTrendsResponse(IntelligenceSchema):
    average_cp_loss: MetricTrendResponse
    serious_errors_per_100_moves: MetricTrendResponse


class TaxonomyTrendResponse(IntelligenceSchema):
    taxonomy: ErrorType
    incidents_per_100_moves: MetricTrendResponse
    games_affected_rate: MetricTrendResponse


class PlayerTrendsResponse(IntelligenceSchema):
    window_games: int
    recent_games: int
    previous_games: int
    overall: OverallTrendsResponse
    phases: dict[GamePhase, PhaseTrendsResponse]
    recurring_errors: tuple[TaxonomyTrendResponse, ...]


class SegmentMetricsResponse(IntelligenceSchema):
    games: int
    user_moves: int
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: Literal["excellent", "good", "fair", "poor"] | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    serious_errors_per_100_moves: float | None
    blunder_free_rate: float | None
    wins: int
    draws: int
    losses: int
    confidence: ProfileConfidenceResponse


class PlayerSegmentsResponse(IntelligenceSchema):
    time_controls: dict[TimeControlSegment, SegmentMetricsResponse]
    colors: dict[Color, SegmentMetricsResponse]
    games_with_known_time_control: int
    games_with_known_color: int


class SummaryConfidenceResponse(IntelligenceSchema):
    level: ProfileConfidenceLevel
    score: float


class MainWeaknessResponse(IntelligenceSchema):
    taxonomy: ErrorType
    score: float
    confidence: ProfileConfidenceResponse


class MainStrengthResponse(IntelligenceSchema):
    type: PlayerStrengthType
    score: float
    confidence: ProfileConfidenceResponse


class SummaryPhaseResponse(IntelligenceSchema):
    phase: GamePhase
    weakness_score: float | None
    confidence: ProfileConfidenceResponse


class PlayerIntelligenceSummaryResponse(IntelligenceSchema):
    status: PlayerIntelligenceStatus = Field(
        description="ready, limited, or insufficient based on sample, coverage, and conclusions."
    )
    main_weakness: MainWeaknessResponse | None
    main_strength: MainStrengthResponse | None
    strongest_phase: SummaryPhaseResponse | None
    weakest_phase: SummaryPhaseResponse | None
    overall_direction: OverallDirection = Field(
        description="Conservative synthesis of five core overall factual trends."
    )
    confidence: SummaryConfidenceResponse


class PlayerOpeningRecordResponse(IntelligenceSchema):
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    subvariation: str | None
    games: int
    wins: int
    draws: int
    losses: int


class PlayerOpeningIntelligenceResponse(IntelligenceSchema):
    selected_games: int
    games_with_recognized_opening: int
    games_with_opening_identity: int
    recognition_coverage_rate: float | None
    top: tuple[PlayerOpeningRecordResponse, ...]
    by_color: dict[Color, tuple[PlayerOpeningRecordResponse, ...]]


class PlayerIntelligenceResponse(IntelligenceSchema):
    intelligence_version: str
    human_metrics_version: str
    window: PlayerIntelligenceWindowResponse
    sample: PlayerIntelligenceSampleResponse
    overall: PlayerIntelligenceOverallResponse
    data_quality: PlayerIntelligenceDataQualityResponse
    recurring_errors: tuple[RecurringErrorResponse, ...]
    weaknesses: tuple[PlayerWeaknessResponse, ...]
    strengths: tuple[PlayerStrengthResponse, ...]
    phases: dict[GamePhase, PlayerPhaseMetricsResponse]
    phase_profile: PhaseProfileResponse
    trends: PlayerTrendsResponse
    segments: PlayerSegmentsResponse
    summary: PlayerIntelligenceSummaryResponse
    openings: PlayerOpeningIntelligenceResponse


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
    phases: dict[GamePhase, GamePhaseStatistics]
    critical_moments: tuple[CriticalMomentResponse, ...]
    errors: tuple[ErrorClassificationResponse, ...]


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
    backend: str
    path: str | None
    writable: bool
    tables_ready: bool
    schema_ready: bool
    migration_revision: str | None


class StockfishStatus(ApiSchema):
    status: str
    path: str
    executable: bool


class ChessComStatus(ApiSchema):
    configured: bool
    user_agent_configured: bool


class AnalysisQueueStatus(ApiSchema):
    backend: Literal["local", "cloud_tasks"]
    status: Literal["ready", "degraded"]
    configured: bool
    queue_name: str | None = None
    worker_url_host: str | None = None


class ScheduledSyncStatus(ApiSchema):
    enabled: bool
    mode: Literal["server", "browser"]
    status: Literal["ready", "disabled", "degraded"]


class SystemStatusResponse(ApiSchema):
    status: str
    backend: str
    app_environment: str
    database: DatabaseStatus
    stockfish: StockfishStatus
    chesscom: ChessComStatus
    analysis_queue: AnalysisQueueStatus
    scheduled_sync: ScheduledSyncStatus


class AppSettingsResponse(ReadSchema):
    chesscom_username: str | None
    auto_sync_enabled: bool
    auto_analyze_latest: bool
    initial_sync_completed: bool
    last_sync_started_at: datetime | None
    last_sync_completed_at: datetime | None
    last_sync_status: SyncStatus
    last_sync_error: str | None


class AppSettingsUpdateRequest(ApiSchema):
    chesscom_username: str | None = Field(default=None, min_length=1, max_length=100)
    auto_sync_enabled: StrictBool | None = None
    auto_analyze_latest: StrictBool | None = None

    @field_validator("chesscom_username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("username must not be empty")
        normalized = value.strip()
        if not normalized:
            raise ValueError("username must not be empty")
        return normalized


class SyncMode(str, Enum):
    INITIAL = "initial"
    INCREMENTAL = "incremental"


class ChessComSyncRequest(ApiSchema):
    username: str | None = Field(default=None, max_length=100)
    mode: SyncMode = SyncMode.INCREMENTAL
    auto_analyze_latest: StrictBool | None = None
    initial_months: int | None = Field(default=None, ge=1, le=24)

    @field_validator("username")
    @classmethod
    def normalize_sync_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("username must not be empty")
        return normalized


class ChessComSyncResponse(ApiSchema):
    mode: SyncMode
    username: str
    examined: int
    imported: int
    duplicates: int
    invalid: int
    imported_game_ids: tuple[int, ...]
    latest_game_id: int | None
    analysis_queued_game_id: int | None
    started_at: datetime
    completed_at: datetime


class ScheduledSyncRequest(ApiSchema):
    schema_version: Literal[1] = 1


class ScheduledSyncResponse(ApiSchema):
    status: Literal["completed", "already_running", "disabled"]
    username: str | None = None
    examined: int = 0
    imported: int = 0
    duplicates: int = 0
    invalid: int = 0
    latest_game_id: int | None = None
    analysis_queued_game_id: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
