from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from app.models import (
    Color,
    ErrorConfidence,
    GamePhase,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)
from app.repositories.player_intelligence_repository import (
    PlayerIntelligenceGameRow,
    list_intelligence_moves,
    list_latest_analyzed_games,
)
from app.services.error_taxonomy_classifier import (
    ErrorTaxonomyClassifier,
    prepare_taxonomy_contexts,
)
from app.services.player_recurring_errors import (
    RecurringError,
    TaxonomyIncident,
    aggregate_recurring_errors,
)
from app.services.player_profile_scoring import (
    PlayerStrength,
    PlayerWeakness,
    build_strengths,
    build_weaknesses,
)
from app.services.player_phase_intelligence import (
    PhaseIntelligence,
    PhaseProfile,
    PlayerPhaseMetrics,
    build_phase_intelligence,
)
from app.services.player_metric_snapshot import build_metric_snapshot
from app.services.player_segmentation import PlayerSegments, build_player_segments
from app.services.player_trends import PlayerTrends, build_player_trends
from app.services.player_intelligence_summary import (
    PlayerIntelligenceSummary,
    build_player_intelligence_summary,
)
from app.services.player_opening_intelligence import (
    PlayerOpeningIntelligence,
    build_player_opening_intelligence,
)


PLAYER_INTELLIGENCE_VERSION = "1"


@dataclass(frozen=True)
class PlayerIntelligenceWindow:
    requested_games: int
    available_analyzed_games: int
    selected_games: int
    total_available_analyzed_games: int


@dataclass(frozen=True)
class PlayerIntelligenceSample:
    games: int
    user_moves: int
    white_games: int
    black_games: int
    wins: int
    draws: int
    losses: int


@dataclass(frozen=True)
class PlayerIntelligenceOverall:
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: str | None
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


@dataclass(frozen=True)
class PlayerIntelligenceDataQuality:
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


@dataclass(frozen=True)
class PlayerIntelligence:
    intelligence_version: str
    human_metrics_version: str
    window: PlayerIntelligenceWindow
    sample: PlayerIntelligenceSample
    overall: PlayerIntelligenceOverall
    data_quality: PlayerIntelligenceDataQuality
    recurring_errors: tuple[RecurringError, ...]
    weaknesses: tuple[PlayerWeakness, ...]
    strengths: tuple[PlayerStrength, ...]
    phases: dict[GamePhase, PlayerPhaseMetrics]
    phase_profile: PhaseProfile
    trends: PlayerTrends | None = None
    segments: PlayerSegments | None = None
    summary: PlayerIntelligenceSummary | None = None
    openings: PlayerOpeningIntelligence | None = None


def _enum_value(value, enum_type):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def aggregate_player_intelligence(
    games: Sequence[PlayerIntelligenceGameRow],
    moves: Sequence[MoveAnalysis],
    *,
    requested_games: int,
    taxonomy_incidents: Sequence[TaxonomyIncident] = (),
    taxonomy_eligible_games: int = 0,
    taxonomy_eligible_user_moves: int = 0,
    games_with_known_time_control: int = 0,
    games_with_known_color: int = 0,
    total_available_analyzed_games: int | None = None,
) -> PlayerIntelligence:
    user_moves = tuple(move for move in moves if getattr(move, "is_user_move", False))
    moves_by_game: dict[int, list[MoveAnalysis]] = defaultdict(list)
    for move in user_moves:
        moves_by_game[move.game_id].append(move)

    snapshot = build_metric_snapshot(games, moves)
    games_with_moves = {
        game_id for game_id, game_moves in moves_by_game.items() if game_moves
    }
    games_with_phase = {
        game_id
        for game_id, game_moves in moves_by_game.items()
        if any(getattr(move, "phase", None) is not None for move in game_moves)
    }
    games_with_complete_evaluations = {
        game_id
        for game_id, game_moves in moves_by_game.items()
        if game_moves
        and all(
            getattr(move, "evaluation_before_cp", None) is not None
            and getattr(move, "evaluation_after_cp", None) is not None
            for move in game_moves
        )
    }
    game_count = len(games)
    user_move_count = len(user_moves)
    color_counts = Counter(
        _enum_value(getattr(game, "user_color", None), Color) for game in games
    )
    result_counts = Counter(
        _enum_value(getattr(game, "result", None), GameResult) for game in games
    )

    sample = PlayerIntelligenceSample(
        games=game_count,
        user_moves=user_move_count,
        white_games=color_counts[Color.WHITE],
        black_games=color_counts[Color.BLACK],
        wins=result_counts[GameResult.WIN],
        draws=result_counts[GameResult.DRAW],
        losses=result_counts[GameResult.LOSS],
    )
    overall = PlayerIntelligenceOverall(
        average_cp_loss=snapshot.average_cp_loss,
        accuracy=snapshot.accuracy,
        accuracy_eligible_moves=snapshot.accuracy_eligible_moves,
        accuracy_coverage_rate=snapshot.accuracy_coverage_rate,
        accuracy_quality_band=snapshot.accuracy_quality_band,
        inaccuracies=snapshot.inaccuracies,
        mistakes=snapshot.mistakes,
        blunders=snapshot.blunders,
        inaccuracies_per_game=snapshot.inaccuracies_per_game,
        mistakes_per_game=snapshot.mistakes_per_game,
        blunders_per_game=snapshot.blunders_per_game,
        inaccuracies_per_100_moves=snapshot.inaccuracies_per_100_moves,
        mistakes_per_100_moves=snapshot.mistakes_per_100_moves,
        blunders_per_100_moves=snapshot.blunders_per_100_moves,
        blunder_free_games=snapshot.blunder_free_games,
        blunder_free_rate=snapshot.blunder_free_rate,
    )
    phase_intelligence = build_phase_intelligence(
        moves,
        sample_games=game_count,
    )
    data_quality = PlayerIntelligenceDataQuality(
        games_with_move_analysis=len(games_with_moves),
        games_with_phase_data=len(games_with_phase),
        games_with_complete_evaluations=len(games_with_complete_evaluations),
        moves_with_cp_loss=snapshot.moves_with_cp_loss,
        moves_with_classification=snapshot.moves_with_classification,
        games_with_taxonomy_data=taxonomy_eligible_games,
        moves_eligible_for_taxonomy=taxonomy_eligible_user_moves,
        moves_with_primary_taxonomy=len(taxonomy_incidents),
        moves_with_phase=phase_intelligence.moves_with_phase,
        moves_without_phase=phase_intelligence.moves_without_phase,
        games_with_known_time_control=games_with_known_time_control,
        games_with_known_color=games_with_known_color,
        moves_eligible_for_accuracy=snapshot.accuracy_eligible_moves,
        accuracy_coverage_rate=snapshot.accuracy_coverage_rate,
    )
    recurring_errors = aggregate_recurring_errors(
        taxonomy_incidents,
        eligible_games=taxonomy_eligible_games,
        eligible_user_moves=taxonomy_eligible_user_moves,
    )
    return PlayerIntelligence(
        intelligence_version=PLAYER_INTELLIGENCE_VERSION,
        human_metrics_version="1",
        window=PlayerIntelligenceWindow(
            requested_games=requested_games,
            available_analyzed_games=game_count,
            selected_games=game_count,
            total_available_analyzed_games=(
                game_count
                if total_available_analyzed_games is None
                else total_available_analyzed_games
            ),
        ),
        sample=sample,
        overall=overall,
        data_quality=data_quality,
        recurring_errors=recurring_errors,
        weaknesses=build_weaknesses(recurring_errors, sample, data_quality),
        strengths=build_strengths(overall, sample, data_quality),
        phases=phase_intelligence.phases,
        phase_profile=phase_intelligence.profile,
    )


@dataclass(frozen=True)
class _TaxonomyGame:
    id: int
    pgn: str
    user_color: Color


@dataclass(frozen=True)
class _TaxonomyReconstruction:
    incidents: tuple[TaxonomyIncident, ...]
    eligible_game_ids: frozenset[int]
    eligible_user_moves_by_game: dict[int, int]


def _taxonomy_subset(
    reconstruction: _TaxonomyReconstruction,
    game_ids: set[int],
) -> tuple[tuple[TaxonomyIncident, ...], int, int]:
    return (
        tuple(
            incident
            for incident in reconstruction.incidents
            if incident.game_id in game_ids
        ),
        len(reconstruction.eligible_game_ids & game_ids),
        sum(
            count
            for game_id, count in reconstruction.eligible_user_moves_by_game.items()
            if game_id in game_ids
        ),
    )


def _reconstruct_taxonomy(
    games: Sequence[PlayerIntelligenceGameRow],
    moves: Sequence[MoveAnalysis],
) -> _TaxonomyReconstruction:
    moves_by_game: dict[int, list[MoveAnalysis]] = defaultdict(list)
    for move in moves:
        moves_by_game[move.game_id].append(move)

    classifier = ErrorTaxonomyClassifier()
    incidents: list[TaxonomyIncident] = []
    eligible_game_ids: set[int] = set()
    eligible_user_moves_by_game: dict[int, int] = {}
    for game_row in games:
        color = _enum_value(game_row.user_color, Color)
        game_moves = tuple(moves_by_game.get(game_row.id, ()))
        user_moves = tuple(
            move for move in game_moves if getattr(move, "is_user_move", False)
        )
        if color is None or not game_moves or not user_moves:
            continue
        game = _TaxonomyGame(id=game_row.id, pgn=game_row.pgn, user_color=color)
        try:
            contexts = prepare_taxonomy_contexts(game, game_moves)  # type: ignore[arg-type]
            if contexts is None:
                continue
            errors = classifier.classify_prepared(
                game,  # type: ignore[arg-type]
                game_moves,
                contexts,
                critical_moments=(),
            )
        except Exception:
            # One malformed legacy game must not make the cross-game profile fail.
            continue
        eligible_game_ids.add(game_row.id)
        eligible_user_moves_by_game[game_row.id] = len(user_moves)
        incidents.extend(
            TaxonomyIncident(
                game_id=game_row.id,
                played_at=game_row.played_at,
                error=error,
            )
            for error in errors
            if error.primary_type is not None
            and error.confidence != ErrorConfidence.LOW
            and error.severity
            in {
                MoveClassification.INACCURACY,
                MoveClassification.MISTAKE,
                MoveClassification.BLUNDER,
            }
        )
    return _TaxonomyReconstruction(
        incidents=tuple(incidents),
        eligible_game_ids=frozenset(eligible_game_ids),
        eligible_user_moves_by_game=eligible_user_moves_by_game,
    )


class PlayerIntelligenceService:
    def __init__(self, session: Session):
        self._session = session

    def build(self, *, window: int = 30) -> PlayerIntelligence:
        if not 1 <= window <= 100:
            raise ValueError("window must be between 1 and 100")
        all_games = list_latest_analyzed_games(self._session, limit=window * 2)
        total_available = (
            all_games[0].total_available_analyzed_games if all_games else 0
        )
        all_moves = list_intelligence_moves(
            self._session,
            [game.id for game in all_games],
        )
        current_games = all_games[:window]
        previous_games = all_games[window:]
        current_ids = {game.id for game in current_games}
        previous_ids = {game.id for game in previous_games}
        current_moves = tuple(move for move in all_moves if move.game_id in current_ids)
        previous_moves = tuple(move for move in all_moves if move.game_id in previous_ids)

        taxonomy = _reconstruct_taxonomy(all_games, all_moves)
        current_taxonomy = _taxonomy_subset(taxonomy, current_ids)
        previous_taxonomy = _taxonomy_subset(taxonomy, previous_ids)
        segments = build_player_segments(current_games, current_moves)
        intelligence = aggregate_player_intelligence(
            current_games,
            current_moves,
            requested_games=window,
            taxonomy_incidents=current_taxonomy[0],
            taxonomy_eligible_games=current_taxonomy[1],
            taxonomy_eligible_user_moves=current_taxonomy[2],
            games_with_known_time_control=segments.games_with_known_time_control,
            games_with_known_color=segments.games_with_known_color,
            total_available_analyzed_games=total_available,
        )
        previous_snapshot = build_metric_snapshot(previous_games, previous_moves)
        previous_phases = build_phase_intelligence(
            previous_moves,
            sample_games=len(previous_games),
        )
        trends = build_player_trends(
            window_games=window,
            recent=build_metric_snapshot(current_games, current_moves),
            previous=previous_snapshot,
            recent_phases=PhaseIntelligence(
                phases=intelligence.phases,
                profile=intelligence.phase_profile,
                moves_with_phase=intelligence.data_quality.moves_with_phase,
                moves_without_phase=intelligence.data_quality.moves_without_phase,
            ),
            previous_phases=previous_phases,
            recent_taxonomy=current_taxonomy[0],
            previous_taxonomy=previous_taxonomy[0],
            recent_taxonomy_games=current_taxonomy[1],
            previous_taxonomy_games=previous_taxonomy[1],
            recent_taxonomy_moves=current_taxonomy[2],
            previous_taxonomy_moves=previous_taxonomy[2],
        )
        summary = build_player_intelligence_summary(
            sample=intelligence.sample,
            data_quality=intelligence.data_quality,
            weaknesses=intelligence.weaknesses,
            strengths=intelligence.strengths,
            phase_profile=intelligence.phase_profile,
            trends=trends,
        )
        return replace(
            intelligence,
            trends=trends,
            segments=segments,
            summary=summary,
            openings=build_player_opening_intelligence(current_games),
        )
