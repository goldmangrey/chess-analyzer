from dataclasses import dataclass
from enum import IntEnum
from math import isfinite
from typing import Sequence

from app.models import (
    Color,
    CriticalMomentType,
    GamePhase,
    MoveAnalysis,
    MoveClassification,
)
from app.services.evaluation_context import (
    MATE_EVALUATION_THRESHOLD,
    MateTransition,
    evaluation_to_user_pov,
    is_winning_mate,
    mate_transition,
)


WINNING_THRESHOLD = 300
ADVANTAGE_THRESHOLD = 100
DISADVANTAGE_THRESHOLD = -100
LOSING_THRESHOLD = -300

TURNING_POINT_MIN_SWING = 150
MISSED_OPPORTUNITY_MIN_BEFORE = 300
MISSED_OPPORTUNITY_MAX_AFTER = 100
MISSED_OPPORTUNITY_MIN_LOSS = 200
BEST_MOVE_MIN_RECOVERY = 150

EVALUATION_SWING_CAP = 1_000
CP_LOSS_SCORE_CAP = 1_000
CP_LOSS_SCORE_WEIGHT = 0.05
EVALUATION_SWING_SCORE_WEIGHT = 0.04
BAND_CHANGE_SCORE = 15.0
LOST_WINNING_POSITION_BONUS = 20.0
MATE_TRANSITION_BONUS = 25.0
ALREADY_LOST_PENALTY = 40.0
MINIMUM_IMPORTANCE_SCORE = 55.0
MINIMUM_PLY_DISTANCE = 3
DEFAULT_CRITICAL_MOMENT_LIMIT = 5
MAX_CRITICAL_MOMENT_LIMIT = 20

TYPE_BASE_SCORE = {
    CriticalMomentType.TURNING_POINT: 45.0,
    CriticalMomentType.BLUNDER: 35.0,
    CriticalMomentType.MISSED_OPPORTUNITY: 55.0,
    CriticalMomentType.MISSED_MATE: 90.0,
    CriticalMomentType.ALLOWED_MATE: 90.0,
    CriticalMomentType.BEST_MOVE: 35.0,
}

PHASE_SCORE = {
    GamePhase.OPENING: 5.0,
    GamePhase.MIDDLEGAME: 10.0,
    GamePhase.ENDGAME: 8.0,
    None: 0.0,
}


class EvaluationBand(IntEnum):
    LOSING = 0
    DISADVANTAGE = 1
    EQUAL = 2
    ADVANTAGE = 3
    WINNING = 4


@dataclass(frozen=True)
class CriticalMoment:
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


def evaluation_band(evaluation: int) -> EvaluationBand:
    if evaluation >= WINNING_THRESHOLD:
        return EvaluationBand.WINNING
    if evaluation >= ADVANTAGE_THRESHOLD:
        return EvaluationBand.ADVANTAGE
    if evaluation > DISADVANTAGE_THRESHOLD:
        return EvaluationBand.EQUAL
    if evaluation > LOSING_THRESHOLD:
        return EvaluationBand.DISADVANTAGE
    return EvaluationBand.LOSING


def _bounded_evaluation(evaluation: int) -> int:
    return max(-EVALUATION_SWING_CAP, min(EVALUATION_SWING_CAP, evaluation))


def _candidate_type(
    move: MoveAnalysis,
    before: int,
    after: int,
) -> CriticalMomentType | None:
    before_band = evaluation_band(before)
    after_band = evaluation_band(after)
    swing = after - before
    deterioration = -swing

    transition = mate_transition(before, after)
    if transition is MateTransition.MISSED_MATE:
        return CriticalMomentType.MISSED_MATE
    if transition is MateTransition.ALLOWED_MATE:
        return CriticalMomentType.ALLOWED_MATE
    if (
        before >= MISSED_OPPORTUNITY_MIN_BEFORE
        and after < MISSED_OPPORTUNITY_MAX_AFTER
        and deterioration >= MISSED_OPPORTUNITY_MIN_LOSS
    ):
        return CriticalMomentType.MISSED_OPPORTUNITY
    if (
        deterioration >= TURNING_POINT_MIN_SWING
        and before_band is not EvaluationBand.LOSING
        and after_band < before_band
    ):
        return CriticalMomentType.TURNING_POINT
    if move.classification is MoveClassification.BLUNDER:
        return CriticalMomentType.BLUNDER
    if (
        transition in {MateTransition.DELIVERED_MATE, MateTransition.ESCAPED_MATE}
        or (swing >= BEST_MOVE_MIN_RECOVERY and after_band > before_band)
    ):
        return CriticalMomentType.BEST_MOVE
    return None


def _importance(
    move: MoveAnalysis,
    moment_type: CriticalMomentType,
    before: int,
    after: int,
) -> float:
    before_band = evaluation_band(before)
    after_band = evaluation_band(after)
    negative = moment_type is not CriticalMomentType.BEST_MOVE
    bounded_swing = abs(_bounded_evaluation(after) - _bounded_evaluation(before))
    score = TYPE_BASE_SCORE[moment_type]
    score += min(bounded_swing, EVALUATION_SWING_CAP) * EVALUATION_SWING_SCORE_WEIGHT
    score += abs(int(after_band) - int(before_band)) * BAND_CHANGE_SCORE
    score += PHASE_SCORE[move.phase]
    if negative:
        score += min(move.centipawn_loss, CP_LOSS_SCORE_CAP) * CP_LOSS_SCORE_WEIGHT
        if before_band >= EvaluationBand.ADVANTAGE and after_band <= EvaluationBand.EQUAL:
            score += LOST_WINNING_POSITION_BONUS
        if before_band is EvaluationBand.LOSING:
            score -= ALREADY_LOST_PENALTY
    if moment_type in {
        CriticalMomentType.MISSED_MATE,
        CriticalMomentType.ALLOWED_MATE,
    } or (is_winning_mate(after) and moment_type is CriticalMomentType.BEST_MOVE):
        score += MATE_TRANSITION_BONUS
    return round(max(0.0, score), 2)


def detect_critical_moments(
    user_color: Color,
    moves: Sequence[MoveAnalysis],
    *,
    limit: int = DEFAULT_CRITICAL_MOMENT_LIMIT,
) -> tuple[CriticalMoment, ...]:
    if not 1 <= limit <= MAX_CRITICAL_MOMENT_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_CRITICAL_MOMENT_LIMIT}")

    candidates: list[CriticalMoment] = []
    for move in sorted(moves, key=lambda item: item.ply):
        if not move.is_user_move:
            continue
        before = evaluation_to_user_pov(move.evaluation_before_cp, user_color)
        after = evaluation_to_user_pov(move.evaluation_after_cp, user_color)
        if before is None or after is None or not isfinite(before) or not isfinite(after):
            continue
        moment_type = _candidate_type(move, before, after)
        if moment_type is None:
            continue
        importance = _importance(move, moment_type, before, after)
        if importance < MINIMUM_IMPORTANCE_SCORE:
            continue
        candidates.append(CriticalMoment(
            ply=move.ply,
            move_number=move.move_number,
            move_san=move.played_move_san,
            move_uci=move.played_move_uci,
            phase=move.phase,
            type=moment_type,
            severity=move.classification,
            centipawn_loss=move.centipawn_loss,
            evaluation_before=move.evaluation_before_cp,
            evaluation_after=move.evaluation_after_cp,
            evaluation_before_user_pov=before,
            evaluation_after_user_pov=after,
            importance_score=importance,
        ))

    ranked = sorted(candidates, key=lambda item: (-item.importance_score, item.ply))
    selected: list[CriticalMoment] = []
    for candidate in ranked:
        if all(abs(candidate.ply - existing.ply) >= MINIMUM_PLY_DISTANCE for existing in selected):
            selected.append(candidate)
            if len(selected) == limit:
                break
    return tuple(selected)


@dataclass(frozen=True)
class CriticalMomentDetector:
    user_color: Color
    limit: int = DEFAULT_CRITICAL_MOMENT_LIMIT

    def detect(self, moves: Sequence[MoveAnalysis]) -> tuple[CriticalMoment, ...]:
        return detect_critical_moments(self.user_color, moves, limit=self.limit)
