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


@dataclass(frozen=True)
class IntelligenceSummary:
    average_cp_loss: float | None
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
    inaccuracies: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class GameIntelligence:
    intelligence_version: str
    analysis: IntelligenceAnalysisState
    game: IntelligenceGame
    opening: IntelligenceOpening
    summary: IntelligenceSummary | None
    phases: dict[GamePhase, IntelligencePhase]
    critical_moments: tuple[CriticalMoment, ...]
    errors: tuple[ErrorClassification, ...]
    error_breakdown: dict[ErrorType, int]


def _summary(user_moves: Sequence[MoveAnalysis]) -> IntelligenceSummary:
    losses = [move.centipawn_loss for move in user_moves]
    counts = Counter(move.classification for move in user_moves)
    return IntelligenceSummary(
        average_cp_loss=round(sum(losses) / len(losses), 1) if losses else None,
        user_moves=len(user_moves),
        inaccuracies=counts[MoveClassification.INACCURACY],
        mistakes=counts[MoveClassification.MISTAKE],
        blunders=counts[MoveClassification.BLUNDER],
    )


def _phase_aggregates(moves: Sequence[MoveAnalysis]) -> dict[GamePhase, IntelligencePhase]:
    phases: dict[GamePhase, IntelligencePhase] = {}
    for phase in GamePhase:
        phase_moves = [move for move in moves if move.phase == phase]
        if not phase_moves:
            continue
        user_moves = [move for move in phase_moves if move.is_user_move]
        summary = _summary(user_moves)
        phases[phase] = IntelligencePhase(
            start_ply=min(move.ply for move in phase_moves),
            end_ply=max(move.ply for move in phase_moves),
            user_moves=summary.user_moves,
            average_cp_loss=summary.average_cp_loss,
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
            opening=IntelligenceOpening(eco=game.opening_code, name=game.opening_name),
            summary=_summary(user_moves) if completed else None,
            phases=_phase_aggregates(ordered_moves),
            critical_moments=critical_moments,
            errors=errors,
            error_breakdown=_error_breakdown(errors),
        )
