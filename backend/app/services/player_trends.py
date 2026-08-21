from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

from app.models import (
    ErrorConfidence,
    ErrorType,
    GamePhase,
    ProfileConfidenceLevel,
    TrendDirection,
)
from app.services.player_metric_snapshot import PlayerMetricSnapshot
from app.services.player_phase_intelligence import PhaseIntelligence
from app.services.player_profile_scoring import build_profile_confidence
from app.services.player_recurring_errors import TaxonomyIncident


TREND_ACPL_ABS_THRESHOLD = 5.0
TREND_ACCURACY_ABS_THRESHOLD = 2.0
TREND_RATE_PER_100_ABS_THRESHOLD = 0.5
TREND_BLUNDER_FREE_ABS_THRESHOLD = 0.05
TREND_RELATIVE_THRESHOLD = 0.10
MAX_TAXONOMY_TRENDS = 5


@dataclass(frozen=True)
class TrendConfidence:
    level: ProfileConfidenceLevel
    score: float
    recent_games: int
    previous_games: int
    recent_user_moves: int
    previous_user_moves: int
    coverage_rate: float | None


@dataclass(frozen=True)
class MetricTrend:
    recent: float | None
    previous: float | None
    absolute_change: float | None
    relative_change: float | None
    direction: TrendDirection
    confidence: TrendConfidence


@dataclass(frozen=True)
class OverallTrends:
    average_cp_loss: MetricTrend
    accuracy: MetricTrend
    inaccuracies_per_100_moves: MetricTrend
    mistakes_per_100_moves: MetricTrend
    blunders_per_100_moves: MetricTrend
    serious_errors_per_100_moves: MetricTrend
    blunder_free_rate: MetricTrend


@dataclass(frozen=True)
class PhaseTrends:
    average_cp_loss: MetricTrend
    serious_errors_per_100_moves: MetricTrend


@dataclass(frozen=True)
class TaxonomyTrend:
    taxonomy: ErrorType
    incidents_per_100_moves: MetricTrend
    games_affected_rate: MetricTrend


@dataclass(frozen=True)
class PlayerTrends:
    window_games: int
    recent_games: int
    previous_games: int
    overall: OverallTrends
    phases: dict[GamePhase, PhaseTrends]
    recurring_errors: tuple[TaxonomyTrend, ...]


def _side_confidence(games: int, eligible_games: int, moves: int, support: int):
    return build_profile_confidence(
        sample_games=games,
        eligible_games=eligible_games,
        eligible_user_moves=moves,
        pattern_support_games=support,
    )


def _trend_confidence(
    *,
    recent_games: int,
    previous_games: int,
    recent_eligible_games: int,
    previous_eligible_games: int,
    recent_moves: int,
    previous_moves: int,
    recent_support: int,
    previous_support: int,
) -> TrendConfidence:
    recent = _side_confidence(
        recent_games, recent_eligible_games, recent_moves, recent_support
    )
    previous = _side_confidence(
        previous_games, previous_eligible_games, previous_moves, previous_support
    )
    weaker = recent if recent.score <= previous.score else previous
    coverage = (
        min(recent.coverage_rate, previous.coverage_rate)
        if recent.coverage_rate is not None and previous.coverage_rate is not None
        else None
    )
    return TrendConfidence(
        level=weaker.level,
        score=round(min(recent.score, previous.score), 4),
        recent_games=recent_games,
        previous_games=previous_games,
        recent_user_moves=recent_moves,
        previous_user_moves=previous_moves,
        coverage_rate=round(coverage, 4) if coverage is not None else None,
    )


def build_metric_trend(
    recent: float | None,
    previous: float | None,
    *,
    lower_is_better: bool,
    absolute_threshold: float,
    confidence: TrendConfidence,
) -> MetricTrend:
    if (
        recent is None
        or previous is None
        or not isfinite(float(recent))
        or not isfinite(float(previous))
    ):
        return MetricTrend(
            recent=recent,
            previous=previous,
            absolute_change=None,
            relative_change=None,
            direction=TrendDirection.INSUFFICIENT,
            confidence=confidence,
        )
    absolute = float(recent) - float(previous)
    relative = absolute / abs(float(previous)) if previous != 0 else None
    meaningful = abs(absolute) >= absolute_threshold and (
        relative is None or abs(relative) >= TREND_RELATIVE_THRESHOLD
    )
    if confidence.level == ProfileConfidenceLevel.INSUFFICIENT:
        direction = TrendDirection.INSUFFICIENT
    elif not meaningful:
        direction = TrendDirection.STABLE
    else:
        improving = absolute < 0 if lower_is_better else absolute > 0
        direction = TrendDirection.IMPROVING if improving else TrendDirection.WORSENING
    return MetricTrend(
        recent=float(recent),
        previous=float(previous),
        absolute_change=round(absolute, 4),
        relative_change=round(relative, 4) if relative is not None else None,
        direction=direction,
        confidence=confidence,
    )


def _snapshot_confidence(
    recent: PlayerMetricSnapshot,
    previous: PlayerMetricSnapshot,
    *,
    recent_moves: int,
    previous_moves: int,
) -> TrendConfidence:
    return _trend_confidence(
        recent_games=recent.games,
        previous_games=previous.games,
        recent_eligible_games=recent.games_with_move_analysis,
        previous_eligible_games=previous.games_with_move_analysis,
        recent_moves=recent_moves,
        previous_moves=previous_moves,
        recent_support=recent.games_with_move_analysis,
        previous_support=previous.games_with_move_analysis,
    )


def _taxonomy_facts(
    incidents: Sequence[TaxonomyIncident],
    *,
    eligible_games: int,
    eligible_moves: int,
) -> dict[ErrorType, tuple[float | None, float | None, int]]:
    grouped: dict[ErrorType, list[TaxonomyIncident]] = defaultdict(list)
    seen = set()
    for incident in incidents:
        taxonomy = incident.error.primary_type
        if taxonomy is None or incident.error.confidence == ErrorConfidence.LOW:
            continue
        identity = (incident.game_id, incident.error.ply, taxonomy)
        if identity in seen:
            continue
        seen.add(identity)
        grouped[taxonomy].append(incident)
    return {
        taxonomy: (
            len(rows) * 100 / eligible_moves if eligible_moves else None,
            len({row.game_id for row in rows}) / eligible_games
            if eligible_games
            else None,
            len({row.game_id for row in rows}),
        )
        for taxonomy, rows in grouped.items()
    }


def build_player_trends(
    *,
    window_games: int,
    recent: PlayerMetricSnapshot,
    previous: PlayerMetricSnapshot,
    recent_phases: PhaseIntelligence,
    previous_phases: PhaseIntelligence,
    recent_taxonomy: Sequence[TaxonomyIncident],
    previous_taxonomy: Sequence[TaxonomyIncident],
    recent_taxonomy_games: int,
    previous_taxonomy_games: int,
    recent_taxonomy_moves: int,
    previous_taxonomy_moves: int,
) -> PlayerTrends:
    classification_confidence = _snapshot_confidence(
        recent,
        previous,
        recent_moves=recent.moves_with_classification,
        previous_moves=previous.moves_with_classification,
    )
    cp_confidence = _snapshot_confidence(
        recent,
        previous,
        recent_moves=recent.moves_with_cp_loss,
        previous_moves=previous.moves_with_cp_loss,
    )
    def trend(recent_value, previous_value, *, acpl=False, accuracy=False, positive=False):
        return build_metric_trend(
            recent_value,
            previous_value,
            lower_is_better=not positive,
            absolute_threshold=(
                TREND_ACPL_ABS_THRESHOLD if acpl else
                TREND_ACCURACY_ABS_THRESHOLD if accuracy
                else TREND_BLUNDER_FREE_ABS_THRESHOLD
                if positive
                else TREND_RATE_PER_100_ABS_THRESHOLD
            ),
            confidence=cp_confidence if acpl or accuracy else classification_confidence,
        )
    overall = OverallTrends(
        average_cp_loss=trend(recent.average_cp_loss, previous.average_cp_loss, acpl=True),
        accuracy=trend(recent.accuracy, previous.accuracy, accuracy=True, positive=True),
        inaccuracies_per_100_moves=trend(recent.inaccuracies_per_100_moves, previous.inaccuracies_per_100_moves),
        mistakes_per_100_moves=trend(recent.mistakes_per_100_moves, previous.mistakes_per_100_moves),
        blunders_per_100_moves=trend(recent.blunders_per_100_moves, previous.blunders_per_100_moves),
        serious_errors_per_100_moves=trend(recent.serious_errors_per_100_moves, previous.serious_errors_per_100_moves),
        blunder_free_rate=trend(recent.blunder_free_rate, previous.blunder_free_rate, positive=True),
    )
    phase_trends = {}
    for phase in GamePhase:
        recent_phase = recent_phases.phases[phase]
        previous_phase = previous_phases.phases[phase]
        cp_phase_confidence = _trend_confidence(
            recent_games=recent.games,
            previous_games=previous.games,
            recent_eligible_games=recent_phase.games_with_phase,
            previous_eligible_games=previous_phase.games_with_phase,
            recent_moves=recent_phase.moves_with_cp_loss,
            previous_moves=previous_phase.moves_with_cp_loss,
            recent_support=recent_phase.games_with_phase,
            previous_support=previous_phase.games_with_phase,
        )
        classification_phase_confidence = _trend_confidence(
            recent_games=recent.games,
            previous_games=previous.games,
            recent_eligible_games=recent_phase.games_with_phase,
            previous_eligible_games=previous_phase.games_with_phase,
            recent_moves=recent_phase.moves_with_classification,
            previous_moves=previous_phase.moves_with_classification,
            recent_support=recent_phase.games_with_phase,
            previous_support=previous_phase.games_with_phase,
        )
        phase_trends[phase] = PhaseTrends(
            average_cp_loss=build_metric_trend(
                recent_phase.average_cp_loss,
                previous_phase.average_cp_loss,
                lower_is_better=True,
                absolute_threshold=TREND_ACPL_ABS_THRESHOLD,
                confidence=cp_phase_confidence,
            ),
            serious_errors_per_100_moves=build_metric_trend(
                recent_phase.serious_errors_per_100_moves,
                previous_phase.serious_errors_per_100_moves,
                lower_is_better=True,
                absolute_threshold=TREND_RATE_PER_100_ABS_THRESHOLD,
                confidence=classification_phase_confidence,
            ),
        )
    recent_facts = _taxonomy_facts(
        recent_taxonomy,
        eligible_games=recent_taxonomy_games,
        eligible_moves=recent_taxonomy_moves,
    )
    previous_facts = _taxonomy_facts(
        previous_taxonomy,
        eligible_games=previous_taxonomy_games,
        eligible_moves=previous_taxonomy_moves,
    )
    taxonomy_confidence = _trend_confidence(
        recent_games=recent.games,
        previous_games=previous.games,
        recent_eligible_games=recent_taxonomy_games,
        previous_eligible_games=previous_taxonomy_games,
        recent_moves=recent_taxonomy_moves,
        previous_moves=previous_taxonomy_moves,
        recent_support=recent_taxonomy_games,
        previous_support=previous_taxonomy_games,
    )
    taxonomy_trends = []
    for taxonomy in set(recent_facts) | set(previous_facts):
        recent_frequency, recent_spread, _ = recent_facts.get(taxonomy, (0.0, 0.0, 0))
        previous_frequency, previous_spread, _ = previous_facts.get(taxonomy, (0.0, 0.0, 0))
        taxonomy_trends.append(
            TaxonomyTrend(
                taxonomy=taxonomy,
                incidents_per_100_moves=build_metric_trend(
                    recent_frequency,
                    previous_frequency,
                    lower_is_better=True,
                    absolute_threshold=TREND_RATE_PER_100_ABS_THRESHOLD,
                    confidence=taxonomy_confidence,
                ),
                games_affected_rate=build_metric_trend(
                    recent_spread,
                    previous_spread,
                    lower_is_better=True,
                    absolute_threshold=TREND_BLUNDER_FREE_ABS_THRESHOLD,
                    confidence=taxonomy_confidence,
                ),
            )
        )
    taxonomy_trends.sort(
        key=lambda item: (
            -abs(item.incidents_per_100_moves.absolute_change or 0.0),
            item.taxonomy.value,
        )
    )
    return PlayerTrends(
        window_games=window_games,
        recent_games=recent.games,
        previous_games=previous.games,
        overall=overall,
        phases=phase_trends,
        recurring_errors=tuple(taxonomy_trends[:MAX_TAXONOMY_TRENDS]),
    )
