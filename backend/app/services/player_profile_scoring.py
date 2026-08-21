from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import isfinite
from typing import Protocol

from app.models import ErrorType, PlayerStrengthType, ProfileConfidenceLevel
from app.services.player_recurring_errors import RecurringError, RecurringErrorEvidence


MAX_WEAKNESSES = 5
MAX_STRENGTHS = 3

WEAKNESS_FREQUENCY_SATURATION_PER_100 = 2.0
WEAKNESS_RECURRENCE_SATURATION_GAMES = 10
WEAKNESS_SPREAD_WEIGHT = 0.30
WEAKNESS_FREQUENCY_WEIGHT = 0.25
WEAKNESS_SEVERITY_WEIGHT = 0.25
WEAKNESS_RECURRENCE_WEIGHT = 0.20

CONFIDENCE_SAMPLE_SATURATION_GAMES = 30
CONFIDENCE_MOVE_SATURATION = 500
CONFIDENCE_PATTERN_SATURATION_GAMES = 10
CONFIDENCE_SAMPLE_WEIGHT = 0.30
CONFIDENCE_COVERAGE_WEIGHT = 0.30
CONFIDENCE_MOVE_WEIGHT = 0.20
CONFIDENCE_PATTERN_WEIGHT = 0.20
MIN_CONFIDENCE_GAMES = 5
MIN_CONFIDENCE_MOVES = 50
CONFIDENCE_LOW_THRESHOLD = 0.25
CONFIDENCE_MEDIUM_THRESHOLD = 0.50
CONFIDENCE_HIGH_THRESHOLD = 0.75

BLUNDER_RATE_CALIBRATION_MAX_PER_100 = 2.0
MISTAKE_RATE_CALIBRATION_MAX_PER_100 = 4.0
ACPL_CALIBRATION_MAX = 120.0
MIN_STRENGTH_COMPONENT = 0.50


class SampleFacts(Protocol):
    games: int
    user_moves: int


class OverallFacts(Protocol):
    average_cp_loss: float | None
    mistakes_per_100_moves: float | None
    blunders_per_100_moves: float | None
    blunder_free_rate: float | None


class DataQualityFacts(Protocol):
    games_with_move_analysis: int
    moves_with_cp_loss: int
    moves_with_classification: int
    games_with_taxonomy_data: int
    moves_eligible_for_taxonomy: int


@dataclass(frozen=True)
class ProfileConfidence:
    level: ProfileConfidenceLevel
    score: float
    sample_games: int
    eligible_games: int
    coverage_rate: float | None
    eligible_user_moves: int


@dataclass(frozen=True)
class WeaknessComponents:
    spread: float
    frequency: float
    severity: float
    recurrence: float


@dataclass(frozen=True)
class WeaknessEvidenceSummary:
    incidents: int
    games_affected: int
    games_affected_rate: float | None
    incidents_per_100_moves: float | None


@dataclass(frozen=True)
class PlayerWeakness:
    taxonomy: ErrorType
    score: float
    rank: int
    confidence: ProfileConfidence
    components: WeaknessComponents
    evidence_summary: WeaknessEvidenceSummary
    evidence: tuple[RecurringErrorEvidence, ...]


@dataclass(frozen=True)
class PlayerStrength:
    type: PlayerStrengthType
    score: float
    rank: int
    confidence: ProfileConfidence
    normalized_component: float
    metrics: dict[str, float]


def _bounded(value: float | int | None) -> float:
    if value is None:
        return 0.0
    normalized = float(value)
    if not isfinite(normalized):
        return 0.0
    return min(max(normalized, 0.0), 1.0)


def _saturate(value: float | int | None, threshold: float) -> float:
    if value is None or threshold <= 0:
        return 0.0
    numeric = float(value)
    if not isfinite(numeric) or numeric <= 0:
        return 0.0
    return _bounded(numeric / threshold)


def build_profile_confidence(
    *,
    sample_games: int,
    eligible_games: int,
    eligible_user_moves: int,
    pattern_support_games: int,
) -> ProfileConfidence:
    coverage = (
        _bounded(eligible_games / sample_games) if sample_games > 0 else None
    )
    score = (
        CONFIDENCE_SAMPLE_WEIGHT
        * _saturate(sample_games, CONFIDENCE_SAMPLE_SATURATION_GAMES)
        + CONFIDENCE_COVERAGE_WEIGHT * (coverage or 0.0)
        + CONFIDENCE_MOVE_WEIGHT
        * _saturate(eligible_user_moves, CONFIDENCE_MOVE_SATURATION)
        + CONFIDENCE_PATTERN_WEIGHT
        * _saturate(pattern_support_games, CONFIDENCE_PATTERN_SATURATION_GAMES)
    )
    score = _bounded(score)
    if (
        sample_games < MIN_CONFIDENCE_GAMES
        or eligible_games < MIN_CONFIDENCE_GAMES
        or eligible_user_moves < MIN_CONFIDENCE_MOVES
    ):
        level = ProfileConfidenceLevel.INSUFFICIENT
    elif score < CONFIDENCE_LOW_THRESHOLD:
        level = ProfileConfidenceLevel.INSUFFICIENT
    elif score < CONFIDENCE_MEDIUM_THRESHOLD:
        level = ProfileConfidenceLevel.LOW
    elif score < CONFIDENCE_HIGH_THRESHOLD:
        level = ProfileConfidenceLevel.MEDIUM
    else:
        level = ProfileConfidenceLevel.HIGH
    return ProfileConfidence(
        level=level,
        score=round(score, 4),
        sample_games=max(sample_games, 0),
        eligible_games=max(eligible_games, 0),
        coverage_rate=round(coverage, 4) if coverage is not None else None,
        eligible_user_moves=max(eligible_user_moves, 0),
    )


def build_weaknesses(
    recurring_errors: Sequence[RecurringError],
    sample: SampleFacts,
    data_quality: DataQualityFacts,
    *,
    limit: int = MAX_WEAKNESSES,
) -> tuple[PlayerWeakness, ...]:
    candidates: list[tuple[float, PlayerWeakness]] = []
    for recurring in recurring_errors:
        spread = _bounded(recurring.games_affected_rate)
        frequency = _saturate(
            recurring.incidents_per_100_moves,
            WEAKNESS_FREQUENCY_SATURATION_PER_100,
        )
        weighted_severity = (
            recurring.severity.inaccuracies
            + recurring.severity.mistakes * 2
            + recurring.severity.blunders * 3
        )
        severity = _bounded(
            weighted_severity / (recurring.incidents * 3)
            if recurring.incidents > 0
            else 0.0
        )
        recurrence = _saturate(
            recurring.games_affected,
            WEAKNESS_RECURRENCE_SATURATION_GAMES,
        )
        raw_score = 100 * (
            WEAKNESS_SPREAD_WEIGHT * spread
            + WEAKNESS_FREQUENCY_WEIGHT * frequency
            + WEAKNESS_SEVERITY_WEIGHT * severity
            + WEAKNESS_RECURRENCE_WEIGHT * recurrence
        )
        confidence = build_profile_confidence(
            sample_games=sample.games,
            eligible_games=data_quality.games_with_taxonomy_data,
            eligible_user_moves=data_quality.moves_eligible_for_taxonomy,
            pattern_support_games=recurring.games_affected,
        )
        candidates.append(
            (
                raw_score,
                PlayerWeakness(
                    taxonomy=recurring.taxonomy,
                    score=round(_bounded(raw_score / 100) * 100, 1),
                    rank=0,
                    confidence=confidence,
                    components=WeaknessComponents(
                        spread=round(spread, 4),
                        frequency=round(frequency, 4),
                        severity=round(severity, 4),
                        recurrence=round(recurrence, 4),
                    ),
                    evidence_summary=WeaknessEvidenceSummary(
                        incidents=recurring.incidents,
                        games_affected=recurring.games_affected,
                        games_affected_rate=recurring.games_affected_rate,
                        incidents_per_100_moves=recurring.incidents_per_100_moves,
                    ),
                    evidence=recurring.evidence,
                ),
            )
        )
    ordered = sorted(
        candidates,
        key=lambda item: (
            -item[0],
            -item[1].confidence.score,
            -item[1].evidence_summary.games_affected,
            -item[1].evidence_summary.incidents,
            item[1].taxonomy.value,
        ),
    )[: max(limit, 0)]
    return tuple(replace(candidate, rank=rank) for rank, (_, candidate) in enumerate(ordered, 1))


def _inverse_component(value: float | None, maximum: float) -> float:
    if value is None or maximum <= 0 or not isfinite(float(value)):
        return 0.0
    return _bounded(1.0 - max(float(value), 0.0) / maximum)


def build_strengths(
    overall: OverallFacts,
    sample: SampleFacts,
    data_quality: DataQualityFacts,
    *,
    limit: int = MAX_STRENGTHS,
) -> tuple[PlayerStrength, ...]:
    if sample.games <= 0 or sample.user_moves <= 0:
        return ()
    specifications = (
        (
            PlayerStrengthType.LOW_BLUNDER_RATE,
            overall.blunders_per_100_moves,
            _inverse_component(
                overall.blunders_per_100_moves,
                BLUNDER_RATE_CALIBRATION_MAX_PER_100,
            ),
            "blunders_per_100_moves",
            data_quality.moves_with_classification,
        ),
        (
            PlayerStrengthType.BLUNDER_FREE_CONSISTENCY,
            overall.blunder_free_rate,
            _bounded(overall.blunder_free_rate),
            "blunder_free_rate",
            data_quality.moves_with_classification,
        ),
        (
            PlayerStrengthType.LOW_MISTAKE_RATE,
            overall.mistakes_per_100_moves,
            _inverse_component(
                overall.mistakes_per_100_moves,
                MISTAKE_RATE_CALIBRATION_MAX_PER_100,
            ),
            "mistakes_per_100_moves",
            data_quality.moves_with_classification,
        ),
        (
            PlayerStrengthType.OVERALL_PRECISION,
            overall.average_cp_loss,
            _inverse_component(overall.average_cp_loss, ACPL_CALIBRATION_MAX),
            "average_cp_loss",
            data_quality.moves_with_cp_loss,
        ),
    )
    candidates: list[PlayerStrength] = []
    for strength_type, value, component, metric_name, eligible_moves in specifications:
        if value is None or component < MIN_STRENGTH_COMPONENT:
            continue
        confidence = build_profile_confidence(
            sample_games=sample.games,
            eligible_games=data_quality.games_with_move_analysis,
            eligible_user_moves=eligible_moves,
            pattern_support_games=data_quality.games_with_move_analysis,
        )
        candidates.append(
            PlayerStrength(
                type=strength_type,
                score=round(component * 100, 1),
                rank=0,
                confidence=confidence,
                normalized_component=round(component, 4),
                metrics={metric_name: float(value)},
            )
        )
    ordered = sorted(
        candidates,
        key=lambda item: (-item.score, -item.confidence.score, item.type.value),
    )[: max(limit, 0)]
    return tuple(replace(candidate, rank=rank) for rank, candidate in enumerate(ordered, 1))
