from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session

from app.models import (
    AnalysisStatus,
    Color,
    ErrorConfidence,
    ErrorType,
    Game,
    GamePhase,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)
from app.repositories.move_analysis_repository import list_moves_for_game
from app.services.critical_moment_detector import CriticalMoment, CriticalMomentDetector
from app.services.error_taxonomy_classifier import (
    ErrorClassification,
    ErrorTaxonomyClassifier,
    prepare_taxonomy_contexts,
)
from app.services.game_review_enrichment import MoveReviewEntry, build_move_review_entries
from app.services.opening_recognizer import recognize_pgn
from app.services.human_chess_metrics import HUMAN_METRICS_VERSION, aggregate_move_accuracy, build_game_accuracy, build_move_human_metrics


INTELLIGENCE_VERSION = "1"


@dataclass(frozen=True)
class IntelligenceAnalysisState:
    status: AnalysisStatus
    intelligence_ready: bool


@dataclass(frozen=True)
class IntelligenceGame:
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


@dataclass(frozen=True)
class IntelligenceOpening:
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


@dataclass(frozen=True)
class IntelligenceSummary:
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_total_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: str | None
    user_moves: int
    inaccuracies: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class IntelligencePhase:
    start_ply: int
    end_ply: int
    user_moves: int
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: str | None
    inaccuracies: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class GameIntelligence:
    intelligence_version: str
    human_metrics_version: str
    analysis: IntelligenceAnalysisState
    game: IntelligenceGame
    opening: IntelligenceOpening
    summary: IntelligenceSummary | None
    phases: dict[GamePhase, IntelligencePhase]
    critical_moments: tuple[CriticalMoment, ...]
    errors: tuple[ErrorClassification, ...]
    error_breakdown: dict[ErrorType, int]
    move_reviews: tuple[MoveReviewEntry, ...]


def _summary(all_moves: Sequence[MoveAnalysis], user_color: Color) -> IntelligenceSummary:
    user_moves = [move for move in all_moves if move.is_user_move]
    losses = [move.centipawn_loss for move in user_moves]
    counts = Counter(move.classification for move in user_moves)
    accuracy = build_game_accuracy(all_moves, user_color=user_color)
    return IntelligenceSummary(
        average_cp_loss=round(sum(losses) / len(losses), 1) if losses else None,
        accuracy=accuracy.accuracy,
        accuracy_eligible_moves=accuracy.eligible_moves,
        accuracy_total_moves=accuracy.total_moves,
        accuracy_coverage_rate=accuracy.coverage_rate,
        accuracy_quality_band=accuracy.quality_band,
        user_moves=len(user_moves),
        inaccuracies=counts[MoveClassification.INACCURACY],
        mistakes=counts[MoveClassification.MISTAKE],
        blunders=counts[MoveClassification.BLUNDER],
    )


def _phase_aggregates(moves: Sequence[MoveAnalysis], user_color: Color) -> dict[GamePhase, IntelligencePhase]:
    phases: dict[GamePhase, IntelligencePhase] = {}
    for phase in GamePhase:
        phase_moves = [move for move in moves if move.phase == phase]
        if not phase_moves:
            continue
        user_moves = [move for move in phase_moves if move.is_user_move]
        summary = _summary(phase_moves, user_color)
        phase_accuracy = aggregate_move_accuracy([
            metric.accuracy if (metric := build_move_human_metrics(
                move.evaluation_before_cp,
                move.evaluation_after_cp,
                user_color=user_color,
            )) else None
            for move in user_moves
        ])
        phases[phase] = IntelligencePhase(
            start_ply=min(move.ply for move in phase_moves),
            end_ply=max(move.ply for move in phase_moves),
            user_moves=summary.user_moves,
            average_cp_loss=summary.average_cp_loss,
            accuracy=phase_accuracy.accuracy,
            accuracy_eligible_moves=phase_accuracy.eligible_moves,
            accuracy_coverage_rate=phase_accuracy.coverage_rate,
            accuracy_quality_band=phase_accuracy.quality_band,
            inaccuracies=summary.inaccuracies,
            mistakes=summary.mistakes,
            blunders=summary.blunders,
        )
    return phases


def _error_breakdown(errors: Sequence[ErrorClassification]) -> dict[ErrorType, int]:
    counts = Counter(
        error.primary_type
        for error in errors
        if error.primary_type is not None and error.confidence != ErrorConfidence.LOW
    )
    return {error_type: counts[error_type] for error_type in ErrorType if counts[error_type]}


class GameIntelligenceService:
    def __init__(self, session: Session):
        self._session = session

    def build(
        self,
        game: Game,
        *,
        moves: Sequence[MoveAnalysis] | None = None,
    ) -> GameIntelligence:
        completed = game.analysis_status == AnalysisStatus.COMPLETED
        ordered_moves = tuple(
            sorted(
                moves if moves is not None else list_moves_for_game(self._session, game.id),
                key=lambda move: move.ply,
            )
        ) if completed else ()
        user_moves = tuple(move for move in ordered_moves if move.is_user_move)

        critical_moments: tuple[CriticalMoment, ...] = ()
        errors: tuple[ErrorClassification, ...] = ()
        contexts = None
        opening = recognize_pgn(
            game.pgn,
            eco=game.opening_code,
            opening_name=game.opening_name,
        )
        if completed and ordered_moves:
            critical_moments = CriticalMomentDetector(game.user_color).detect(ordered_moves)
            contexts = prepare_taxonomy_contexts(game, ordered_moves)
            errors = ErrorTaxonomyClassifier().classify_prepared(
                game,
                ordered_moves,
                contexts,
                critical_moments,
            )

        opponent = game.black_username if game.user_color == Color.WHITE else game.white_username
        return GameIntelligence(
            intelligence_version=INTELLIGENCE_VERSION,
            human_metrics_version=HUMAN_METRICS_VERSION,
            analysis=IntelligenceAnalysisState(
                status=game.analysis_status,
                intelligence_ready=completed and bool(ordered_moves),
            ),
            game=IntelligenceGame(
                id=game.id,
                external_id=game.external_id,
                platform=game.platform,
                played_at=game.played_at,
                result=game.result,
                user_color=game.user_color,
                opponent=opponent,
                white_username=game.white_username,
                black_username=game.black_username,
                white_rating=game.white_rating,
                black_rating=game.black_rating,
                time_control=game.time_control,
            ),
            opening=IntelligenceOpening(
                eco=opening.eco,
                name=opening.name,
                family=opening.family,
                variation=opening.variation,
                subvariation=opening.subvariation,
                deepest_match_ply=opening.deepest_match_ply,
                deepest_match_move_san=opening.deepest_match_move_san,
                last_named_match_ply=opening.last_named_match_ply,
                last_named_match_move_san=opening.last_named_match_move_san,
                last_sequence_book_ply=opening.last_sequence_book_ply,
                last_sequence_book_move_san=opening.last_sequence_book_move_san,
                first_deviation_ply=opening.first_deviation_ply,
                first_deviation_move_san=opening.first_deviation_move_san,
                transposition_reentry=opening.transposition_reentry,
                first_reentry_ply=opening.first_reentry_ply,
            ),
            summary=_summary(ordered_moves, game.user_color) if completed else None,
            phases=_phase_aggregates(ordered_moves, game.user_color),
            critical_moments=critical_moments,
            errors=errors,
            error_breakdown=_error_breakdown(errors),
            move_reviews=(
                build_move_review_entries(
                    moves=ordered_moves,
                    user_color=game.user_color,
                    errors=errors,
                    contexts=contexts,
                    opening=opening,
                )
                if completed and ordered_moves
                else ()
            ),
        )
