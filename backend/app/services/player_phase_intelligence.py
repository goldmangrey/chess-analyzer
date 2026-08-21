from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

from app.models import Color, GamePhase, MoveClassification, ProfileConfidenceLevel
from app.services.human_chess_metrics import aggregate_move_accuracy, build_move_human_metrics
from app.services.player_profile_scoring import (
    ProfileConfidence,
    build_profile_confidence,
)


PHASE_ACPL_SATURATION = 120.0
PHASE_SERIOUS_ERROR_RATE_SATURATION_PER_100 = 6.0
PHASE_ACPL_WEIGHT = 0.55
PHASE_SERIOUS_ERROR_WEIGHT = 0.45
PHASE_SCORE_TIE_EPSILON = 2.0

_PHASE_ORDER = {
    GamePhase.OPENING: 0,
    GamePhase.MIDDLEGAME: 1,
    GamePhase.ENDGAME: 2,
}
_SERIOUS = {MoveClassification.MISTAKE, MoveClassification.BLUNDER}


@dataclass(frozen=True)
class PlayerPhaseMetrics:
    user_moves: int
    games_with_phase: int
    participation_rate: float | None
    moves_with_cp_loss: int
    moves_with_classification: int
    average_cp_loss: float | None
    accuracy: float | None
    accuracy_eligible_moves: int
    accuracy_coverage_rate: float | None
    accuracy_quality_band: str | None
    inaccuracies: int
    mistakes: int
    blunders: int
    inaccuracies_per_100_moves: float | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    serious_errors: int
    serious_errors_per_100_moves: float | None


@dataclass(frozen=True)
class PhaseScoreComponents:
    acpl: float | None
    serious_error_rate: float | None


@dataclass(frozen=True)
class PhasePerformance:
    phase: GamePhase
    weakness_score: float | None
    components: PhaseScoreComponents
    confidence: ProfileConfidence


@dataclass(frozen=True)
class FirstSeriousBreakdown:
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


@dataclass(frozen=True)
class PhaseProfile:
    performance: dict[GamePhase, PhasePerformance]
    strongest_phase: PhasePerformance | None
    weakest_phase: PhasePerformance | None
    first_serious_breakdown: FirstSeriousBreakdown


@dataclass(frozen=True)
class PhaseIntelligence:
    phases: dict[GamePhase, PlayerPhaseMetrics]
    profile: PhaseProfile
    moves_with_phase: int
    moves_without_phase: int


def _enum_value(value, enum_type):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _rate(numerator: int | float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    value = float(numerator) / denominator
    return value if isfinite(value) else None


def _finite_number(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _component(value: float | None, saturation: float) -> float | None:
    if value is None or saturation <= 0:
        return None
    return min(max(value / saturation, 0.0), 1.0)


def _phase_metrics(
    moves: Sequence,
    *,
    sample_games: int,
) -> PlayerPhaseMetrics:
    counts = Counter(
        classification
        for move in moves
        if (classification := _enum_value(getattr(move, "classification", None), MoveClassification))
        is not None
    )
    cp_losses = tuple(
        value
        for move in moves
        if (value := _finite_number(getattr(move, "centipawn_loss", None)))
        is not None
    )
    user_moves = len(moves)
    games = {move.game_id for move in moves}
    inaccuracies = counts[MoveClassification.INACCURACY]
    mistakes = counts[MoveClassification.MISTAKE]
    blunders = counts[MoveClassification.BLUNDER]
    serious = mistakes + blunders
    accuracy_values = []
    for move in moves:
        color = _enum_value(getattr(move, "player_color", None), Color)
        metric = build_move_human_metrics(
            getattr(move, "evaluation_before_cp", None),
            getattr(move, "evaluation_after_cp", None),
            user_color=color,
        ) if color is not None else None
        accuracy_values.append(metric.accuracy if metric else None)
    accuracy = aggregate_move_accuracy(accuracy_values)
    return PlayerPhaseMetrics(
        user_moves=user_moves,
        games_with_phase=len(games),
        participation_rate=_rate(len(games), sample_games),
        moves_with_cp_loss=len(cp_losses),
        moves_with_classification=sum(counts.values()),
        average_cp_loss=sum(cp_losses) / len(cp_losses) if cp_losses else None,
        accuracy=accuracy.accuracy,
        accuracy_eligible_moves=accuracy.eligible_moves,
        accuracy_coverage_rate=accuracy.coverage_rate,
        accuracy_quality_band=accuracy.quality_band,
        inaccuracies=inaccuracies,
        mistakes=mistakes,
        blunders=blunders,
        inaccuracies_per_100_moves=_rate(inaccuracies * 100, user_moves),
        mistakes_per_100_moves=_rate(mistakes * 100, user_moves),
        blunders_per_100_moves=_rate(blunders * 100, user_moves),
        serious_errors=serious,
        serious_errors_per_100_moves=_rate(serious * 100, user_moves),
    )


def _performance(
    phase: GamePhase,
    metrics: PlayerPhaseMetrics,
    *,
    sample_games: int,
) -> tuple[float | None, PhasePerformance]:
    acpl = _component(metrics.average_cp_loss, PHASE_ACPL_SATURATION)
    serious = _component(
        metrics.serious_errors_per_100_moves,
        PHASE_SERIOUS_ERROR_RATE_SATURATION_PER_100,
    )
    raw_score = (
        100 * (PHASE_ACPL_WEIGHT * acpl + PHASE_SERIOUS_ERROR_WEIGHT * serious)
        if acpl is not None and serious is not None
        else None
    )
    confidence = build_profile_confidence(
        sample_games=sample_games,
        eligible_games=metrics.games_with_phase,
        eligible_user_moves=min(
            metrics.moves_with_cp_loss,
            metrics.moves_with_classification,
        ),
        pattern_support_games=metrics.games_with_phase,
    )
    return raw_score, PhasePerformance(
        phase=phase,
        weakness_score=round(raw_score, 1) if raw_score is not None else None,
        components=PhaseScoreComponents(
            acpl=round(acpl, 4) if acpl is not None else None,
            serious_error_rate=round(serious, 4) if serious is not None else None,
        ),
        confidence=confidence,
    )


def _first_serious_breakdown(user_moves: Sequence) -> FirstSeriousBreakdown:
    by_game: dict[int, list] = defaultdict(list)
    for move in user_moves:
        by_game[move.game_id].append(move)
    buckets = Counter()
    for moves in by_game.values():
        first = next(
            (
                move
                for move in sorted(moves, key=lambda item: item.ply)
                if _enum_value(getattr(move, "classification", None), MoveClassification)
                in _SERIOUS
            ),
            None,
        )
        if first is None:
            buckets["no_serious_error"] += 1
            continue
        phase = _enum_value(getattr(first, "phase", None), GamePhase)
        buckets[phase.value if phase is not None else "unknown"] += 1
    serious_games = (
        buckets[GamePhase.OPENING.value]
        + buckets[GamePhase.MIDDLEGAME.value]
        + buckets[GamePhase.ENDGAME.value]
        + buckets["unknown"]
    )
    return FirstSeriousBreakdown(
        eligible_games=len(by_game),
        games_with_serious_error=serious_games,
        opening=buckets[GamePhase.OPENING.value],
        middlegame=buckets[GamePhase.MIDDLEGAME.value],
        endgame=buckets[GamePhase.ENDGAME.value],
        unknown=buckets["unknown"],
        no_serious_error=buckets["no_serious_error"],
        opening_share=_rate(buckets[GamePhase.OPENING.value], serious_games),
        middlegame_share=_rate(buckets[GamePhase.MIDDLEGAME.value], serious_games),
        endgame_share=_rate(buckets[GamePhase.ENDGAME.value], serious_games),
        unknown_share=_rate(buckets["unknown"], serious_games),
    )


def build_phase_intelligence(
    moves: Sequence,
    *,
    sample_games: int,
) -> PhaseIntelligence:
    user_moves = tuple(move for move in moves if getattr(move, "is_user_move", False))
    by_phase = {
        phase: tuple(
            move
            for move in user_moves
            if _enum_value(getattr(move, "phase", None), GamePhase) == phase
        )
        for phase in GamePhase
    }
    phases = {
        phase: _phase_metrics(phase_moves, sample_games=sample_games)
        for phase, phase_moves in by_phase.items()
    }
    raw_performance = {
        phase: _performance(phase, metrics, sample_games=sample_games)
        for phase, metrics in phases.items()
    }
    performance = {phase: item[1] for phase, item in raw_performance.items()}
    eligible = sorted(
        (
            (raw_score, phase, result)
            for phase, (raw_score, result) in raw_performance.items()
            if raw_score is not None
            and result.confidence.level != ProfileConfidenceLevel.INSUFFICIENT
        ),
        key=lambda item: (item[0], _PHASE_ORDER[item[1]]),
    )
    strongest = weakest = None
    if len(eligible) >= 2:
        if eligible[1][0] - eligible[0][0] >= PHASE_SCORE_TIE_EPSILON:
            strongest = eligible[0][2]
        if eligible[-1][0] - eligible[-2][0] >= PHASE_SCORE_TIE_EPSILON:
            weakest = eligible[-1][2]

    moves_with_phase = sum(len(phase_moves) for phase_moves in by_phase.values())
    return PhaseIntelligence(
        phases=phases,
        profile=PhaseProfile(
            performance=performance,
            strongest_phase=strongest,
            weakest_phase=weakest,
            first_serious_breakdown=_first_serious_breakdown(user_moves),
        ),
        moves_with_phase=moves_with_phase,
        moves_without_phase=len(user_moves) - moves_with_phase,
    )
