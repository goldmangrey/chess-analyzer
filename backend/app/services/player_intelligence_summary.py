from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from app.models import (
    ErrorType,
    GamePhase,
    OverallDirection,
    PlayerIntelligenceStatus,
    PlayerStrengthType,
    ProfileConfidenceLevel,
    TrendDirection,
)
from app.services.player_profile_scoring import ProfileConfidence


MIN_CORE_TRENDS = 2
SUMMARY_MIN_GAMES = 5
SUMMARY_MIN_USER_MOVES = 50
SUMMARY_READY_GAMES = 20
SUMMARY_READY_MOVE_COVERAGE = 0.80
SUMMARY_READY_TAXONOMY_COVERAGE = 0.60
SUMMARY_READY_CONCLUSIONS = 3

_LEVEL_ORDER = {
    ProfileConfidenceLevel.INSUFFICIENT: 0,
    ProfileConfidenceLevel.LOW: 1,
    ProfileConfidenceLevel.MEDIUM: 2,
    ProfileConfidenceLevel.HIGH: 3,
}


class SampleFacts(Protocol):
    games: int
    user_moves: int


class DataQualityFacts(Protocol):
    games_with_move_analysis: int
    games_with_taxonomy_data: int


@dataclass(frozen=True)
class MainWeakness:
    taxonomy: ErrorType
    score: float
    confidence: ProfileConfidence


@dataclass(frozen=True)
class MainStrength:
    type: PlayerStrengthType
    score: float
    confidence: ProfileConfidence


@dataclass(frozen=True)
class SummaryPhase:
    phase: GamePhase
    weakness_score: float | None
    confidence: ProfileConfidence


@dataclass(frozen=True)
class SummaryConfidence:
    level: ProfileConfidenceLevel
    score: float


@dataclass(frozen=True)
class PlayerIntelligenceSummary:
    status: PlayerIntelligenceStatus
    main_weakness: MainWeakness | None
    main_strength: MainStrength | None
    strongest_phase: SummaryPhase | None
    weakest_phase: SummaryPhase | None
    overall_direction: OverallDirection
    confidence: SummaryConfidence


def _usable(item) -> bool:
    return item is not None and item.confidence.level != ProfileConfidenceLevel.INSUFFICIENT


def _bounded(value: float) -> float:
    return min(max(value if isfinite(value) else 0.0, 0.0), 1.0)


def _direction(trends) -> tuple[OverallDirection, SummaryConfidence | None]:
    if trends is None:
        return OverallDirection.INSUFFICIENT, None
    overall = trends.overall
    metrics = (
        overall.average_cp_loss,
        overall.mistakes_per_100_moves,
        overall.blunders_per_100_moves,
        overall.serious_errors_per_100_moves,
        overall.blunder_free_rate,
    )
    usable = tuple(metric for metric in metrics if metric.direction != TrendDirection.INSUFFICIENT)
    if len(usable) < MIN_CORE_TRENDS:
        return OverallDirection.INSUFFICIENT, None
    directions = {metric.direction for metric in usable}
    if TrendDirection.IMPROVING in directions and TrendDirection.WORSENING in directions:
        direction = OverallDirection.MIXED
    elif TrendDirection.IMPROVING in directions:
        direction = OverallDirection.IMPROVING
    elif TrendDirection.WORSENING in directions:
        direction = OverallDirection.WORSENING
    else:
        direction = OverallDirection.STABLE
    weakest = min(
        usable,
        key=lambda metric: (
            _LEVEL_ORDER[metric.confidence.level],
            metric.confidence.score,
        ),
    ).confidence
    return direction, SummaryConfidence(weakest.level, round(_bounded(weakest.score), 4))


def _compact_phase(value) -> SummaryPhase | None:
    if not _usable(value):
        return None
    return SummaryPhase(value.phase, value.weakness_score, value.confidence)


def build_player_intelligence_summary(
    *,
    sample: SampleFacts,
    data_quality: DataQualityFacts,
    weaknesses: Sequence,
    strengths: Sequence,
    phase_profile,
    trends,
) -> PlayerIntelligenceSummary:
    weakness = next((item for item in weaknesses if _usable(item)), None)
    strength = next((item for item in strengths if _usable(item)), None)
    main_weakness = (
        MainWeakness(weakness.taxonomy, weakness.score, weakness.confidence)
        if weakness else None
    )
    main_strength = (
        MainStrength(strength.type, strength.score, strength.confidence)
        if strength else None
    )
    strongest = _compact_phase(phase_profile.strongest_phase)
    weakest = _compact_phase(phase_profile.weakest_phase)
    direction, direction_confidence = _direction(trends)

    conclusion_confidences = [
        item.confidence
        for item in (main_weakness, main_strength, strongest, weakest)
        if item is not None
    ]
    if direction_confidence is not None:
        conclusion_confidences.append(direction_confidence)
    if conclusion_confidences:
        confidence = min(
            conclusion_confidences,
            key=lambda item: (_LEVEL_ORDER[item.level], item.score),
        )
        summary_confidence = SummaryConfidence(
            confidence.level, round(_bounded(confidence.score), 4)
        )
    else:
        summary_confidence = SummaryConfidence(ProfileConfidenceLevel.INSUFFICIENT, 0.0)

    conclusions = sum(
        item is not None for item in (main_weakness, main_strength, strongest, weakest)
    ) + (direction != OverallDirection.INSUFFICIENT)
    move_coverage = (
        data_quality.games_with_move_analysis / sample.games if sample.games else 0.0
    )
    taxonomy_coverage = (
        data_quality.games_with_taxonomy_data / sample.games if sample.games else 0.0
    )
    if (
        sample.games < SUMMARY_MIN_GAMES
        or sample.user_moves < SUMMARY_MIN_USER_MOVES
        or conclusions == 0
    ):
        status = PlayerIntelligenceStatus.INSUFFICIENT
    elif (
        sample.games >= SUMMARY_READY_GAMES
        and move_coverage >= SUMMARY_READY_MOVE_COVERAGE
        and taxonomy_coverage >= SUMMARY_READY_TAXONOMY_COVERAGE
        and conclusions >= SUMMARY_READY_CONCLUSIONS
    ):
        status = PlayerIntelligenceStatus.READY
    else:
        status = PlayerIntelligenceStatus.LIMITED
    return PlayerIntelligenceSummary(
        status=status,
        main_weakness=main_weakness,
        main_strength=main_strength,
        strongest_phase=strongest,
        weakest_phase=weakest,
        overall_direction=direction,
        confidence=summary_confidence,
    )
