from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models import (
    ErrorConfidence,
    ErrorType,
    GamePhase,
    MoveClassification,
    ProfileConfidenceLevel,
    TrendDirection,
)
from app.services.error_taxonomy_classifier import ErrorClassification
from app.services.player_metric_snapshot import PlayerMetricSnapshot
from app.services.player_phase_intelligence import build_phase_intelligence
from app.services.player_recurring_errors import TaxonomyIncident
from app.services.player_trends import (
    TREND_ACPL_ABS_THRESHOLD,
    MetricTrend,
    TrendConfidence,
    build_metric_trend,
    build_player_trends,
)


def _snapshot(
    *,
    games=10,
    moves=100,
    acpl=50.0,
    inaccuracies=1.0,
    mistakes=1.0,
    blunders=0.5,
    serious=1.5,
    free=0.7,
    accuracy=85.0,
):
    return PlayerMetricSnapshot(
        games=games,
        user_moves=moves,
        games_with_move_analysis=games,
        moves_with_cp_loss=moves,
        moves_with_classification=moves,
        average_cp_loss=acpl,
        inaccuracies=0,
        mistakes=0,
        blunders=0,
        inaccuracies_per_game=0,
        mistakes_per_game=0,
        blunders_per_game=0,
        inaccuracies_per_100_moves=inaccuracies,
        mistakes_per_100_moves=mistakes,
        blunders_per_100_moves=blunders,
        serious_errors_per_100_moves=serious,
        blunder_free_games=round(free * games) if free is not None else 0,
        blunder_free_rate=free,
        accuracy=accuracy,
        accuracy_eligible_moves=moves if accuracy is not None else 0,
        accuracy_coverage_rate=1.0 if moves and accuracy is not None else None,
        accuracy_quality_band="good" if accuracy is not None else None,
    )


def _confidence(level=ProfileConfidenceLevel.HIGH):
    return TrendConfidence(
        level=level,
        score=1.0,
        recent_games=10,
        previous_games=10,
        recent_user_moves=100,
        previous_user_moves=100,
        coverage_rate=1.0,
    )


def _empty_phases(games=10):
    return build_phase_intelligence((), sample_games=games)


def _incident(game_id, taxonomy, *, confidence=ErrorConfidence.HIGH):
    return TaxonomyIncident(
        game_id=game_id,
        played_at=datetime(2026, 1, game_id, tzinfo=timezone.utc),
        error=ErrorClassification(
            ply=1,
            move_number=1,
            move_san="e4",
            move_uci="e2e4",
            phase=GamePhase.OPENING,
            severity=MoveClassification.MISTAKE,
            primary_type=taxonomy,
            secondary_types=(ErrorType.FORK,),
            confidence=confidence,
            centipawn_loss=200,
            critical_moment_type=None,
        ),
    )


def _build(recent, previous, **kwargs):
    return build_player_trends(
        window_games=10,
        recent=recent,
        previous=previous,
        recent_phases=kwargs.get("recent_phases", _empty_phases(recent.games)),
        previous_phases=kwargs.get("previous_phases", _empty_phases(previous.games)),
        recent_taxonomy=kwargs.get("recent_taxonomy", ()),
        previous_taxonomy=kwargs.get("previous_taxonomy", ()),
        recent_taxonomy_games=kwargs.get("recent_taxonomy_games", recent.games),
        previous_taxonomy_games=kwargs.get("previous_taxonomy_games", previous.games),
        recent_taxonomy_moves=kwargs.get("recent_taxonomy_moves", recent.user_moves),
        previous_taxonomy_moves=kwargs.get("previous_taxonomy_moves", previous.user_moves),
    )


def test_no_previous_window_is_insufficient_and_null_safe():
    trends = _build(_snapshot(), _snapshot(games=0, moves=0, acpl=None, free=None))
    assert trends.previous_games == 0
    assert trends.overall.average_cp_loss.direction == TrendDirection.INSUFFICIENT
    assert trends.overall.average_cp_loss.absolute_change is None


def test_overall_metric_directions_changes_and_stability():
    trends = _build(
        _snapshot(acpl=50, mistakes=1, blunders=2, free=0.7),
        _snapshot(acpl=70, mistakes=2, blunders=1, free=0.5),
    )
    assert trends.overall.average_cp_loss.direction == TrendDirection.IMPROVING
    assert trends.overall.average_cp_loss.absolute_change == -20
    assert trends.overall.average_cp_loss.relative_change == pytest.approx(-0.2857)
    assert trends.overall.mistakes_per_100_moves.direction == TrendDirection.IMPROVING
    assert trends.overall.blunders_per_100_moves.direction == TrendDirection.WORSENING
    assert trends.overall.blunder_free_rate.direction == TrendDirection.IMPROVING


def test_accuracy_trend_uses_higher_is_better_and_noise_band():
    improving = _build(_snapshot(accuracy=92), _snapshot(accuracy=80))
    stable = _build(_snapshot(accuracy=85), _snapshot(accuracy=84))
    missing = _build(_snapshot(accuracy=None), _snapshot(accuracy=84))
    assert improving.overall.accuracy.direction == TrendDirection.IMPROVING
    assert stable.overall.accuracy.direction == TrendDirection.STABLE
    assert missing.overall.accuracy.direction == TrendDirection.INSUFFICIENT

    stable = _build(_snapshot(acpl=52), _snapshot(acpl=50))
    assert stable.overall.average_cp_loss.direction == TrendDirection.STABLE


def test_threshold_boundary_and_previous_zero_relative_change():
    at_boundary = build_metric_trend(
        45,
        50,
        lower_is_better=True,
        absolute_threshold=TREND_ACPL_ABS_THRESHOLD,
        confidence=_confidence(),
    )
    zero = build_metric_trend(
        1,
        0,
        lower_is_better=True,
        absolute_threshold=0.5,
        confidence=_confidence(),
    )
    assert at_boundary.direction == TrendDirection.IMPROVING
    assert zero.relative_change is None
    assert zero.direction == TrendDirection.WORSENING


def test_tiny_or_partial_sample_limits_trend_confidence():
    trends = _build(_snapshot(games=5, moves=60), _snapshot(games=2, moves=20))
    confidence = trends.overall.average_cp_loss.confidence
    assert confidence.level == ProfileConfidenceLevel.INSUFFICIENT
    assert 0 <= confidence.score <= 1
    assert confidence.previous_games == 2


def test_phase_trends_compare_facts_and_missing_side_is_insufficient():
    recent_moves = tuple(
        SimpleNamespace(
            game_id=game,
            ply=ply,
            phase=GamePhase.OPENING,
            classification=MoveClassification.NORMAL,
            centipawn_loss=20,
            is_user_move=True,
        )
        for game in range(1, 11)
        for ply in range(1, 21, 2)
    )
    previous_moves = tuple(
        SimpleNamespace(
            game_id=game,
            ply=ply,
            phase=GamePhase.OPENING,
            classification=MoveClassification.MISTAKE if ply <= 5 else MoveClassification.NORMAL,
            centipawn_loss=80,
            is_user_move=True,
        )
        for game in range(11, 21)
        for ply in range(1, 21, 2)
    )
    trends = _build(
        _snapshot(),
        _snapshot(),
        recent_phases=build_phase_intelligence(recent_moves, sample_games=10),
        previous_phases=build_phase_intelligence(previous_moves, sample_games=10),
    )
    opening = trends.phases[GamePhase.OPENING]
    assert opening.average_cp_loss.direction == TrendDirection.IMPROVING
    assert opening.serious_errors_per_100_moves.direction == TrendDirection.IMPROVING
    assert trends.phases[GamePhase.ENDGAME].average_cp_loss.direction == TrendDirection.INSUFFICIENT


def test_taxonomy_union_new_disappeared_low_confidence_and_ordering():
    recent = (
        _incident(1, ErrorType.KING_SAFETY),
        _incident(2, ErrorType.KING_SAFETY),
        _incident(3, ErrorType.PIN, confidence=ErrorConfidence.LOW),
    )
    previous = (
        _incident(4, ErrorType.HANGING_PIECE),
        _incident(5, ErrorType.HANGING_PIECE),
    )
    trends = _build(
        _snapshot(),
        _snapshot(),
        recent_taxonomy=recent,
        previous_taxonomy=previous,
    )
    found = {item.taxonomy: item for item in trends.recurring_errors}
    assert set(found) == {ErrorType.KING_SAFETY, ErrorType.HANGING_PIECE}
    assert found[ErrorType.KING_SAFETY].incidents_per_100_moves.relative_change is None
    assert found[ErrorType.KING_SAFETY].incidents_per_100_moves.direction == TrendDirection.WORSENING
    assert found[ErrorType.HANGING_PIECE].incidents_per_100_moves.direction == TrendDirection.IMPROVING
    assert [item.taxonomy.value for item in trends.recurring_errors] == sorted(
        (item.taxonomy.value for item in trends.recurring_errors),
    )
