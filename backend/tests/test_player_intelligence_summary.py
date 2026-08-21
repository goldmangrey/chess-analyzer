from types import SimpleNamespace

import pytest

from app.models import (
    ErrorType,
    GamePhase,
    OverallDirection,
    PlayerIntelligenceStatus,
    PlayerStrengthType,
    ProfileConfidenceLevel,
    TrendDirection,
)
from app.services.player_intelligence_summary import build_player_intelligence_summary
from app.services.player_profile_scoring import ProfileConfidence


def _confidence(level=ProfileConfidenceLevel.MEDIUM, score=0.6):
    return ProfileConfidence(level, score, 20, 20, 1.0, 400)


def _metric(direction, level=ProfileConfidenceLevel.MEDIUM, score=0.6):
    return SimpleNamespace(
        direction=direction,
        confidence=SimpleNamespace(level=level, score=score),
    )


def _trends(*directions):
    values = list(directions) + [TrendDirection.INSUFFICIENT] * (5 - len(directions))
    metrics = [_metric(value) for value in values]
    return SimpleNamespace(
        overall=SimpleNamespace(
            average_cp_loss=metrics[0],
            mistakes_per_100_moves=metrics[1],
            blunders_per_100_moves=metrics[2],
            serious_errors_per_100_moves=metrics[3],
            blunder_free_rate=metrics[4],
        )
    )


def _build(
    *, games=20, moves=400, weaknesses=(), strengths=(), strongest=None,
    weakest=None, trends=None, move_games=20, taxonomy_games=20,
):
    return build_player_intelligence_summary(
        sample=SimpleNamespace(games=games, user_moves=moves),
        data_quality=SimpleNamespace(
            games_with_move_analysis=move_games,
            games_with_taxonomy_data=taxonomy_games,
        ),
        weaknesses=weaknesses,
        strengths=strengths,
        phase_profile=SimpleNamespace(
            strongest_phase=strongest, weakest_phase=weakest
        ),
        trends=trends,
    )


def test_empty_profile_is_insufficient_and_null_safe():
    result = _build(games=0, moves=0, move_games=0, taxonomy_games=0)

    assert result.status is PlayerIntelligenceStatus.INSUFFICIENT
    assert result.main_weakness is None
    assert result.main_strength is None
    assert result.overall_direction is OverallDirection.INSUFFICIENT
    assert result.confidence.score == 0.0


def test_main_conclusions_skip_insufficient_candidates():
    weak_bad = SimpleNamespace(
        taxonomy=ErrorType.KING_SAFETY, score=90.0,
        confidence=_confidence(ProfileConfidenceLevel.INSUFFICIENT, 0.2),
    )
    weak_good = SimpleNamespace(
        taxonomy=ErrorType.HANGING_PIECE, score=70.0, confidence=_confidence()
    )
    strength_bad = SimpleNamespace(
        type=PlayerStrengthType.OVERALL_PRECISION, score=95.0,
        confidence=_confidence(ProfileConfidenceLevel.INSUFFICIENT, 0.2),
    )
    strength_good = SimpleNamespace(
        type=PlayerStrengthType.LOW_BLUNDER_RATE, score=75.0, confidence=_confidence()
    )

    result = _build(
        weaknesses=(weak_bad, weak_good), strengths=(strength_bad, strength_good)
    )

    assert result.main_weakness.taxonomy is ErrorType.HANGING_PIECE
    assert result.main_strength.type is PlayerStrengthType.LOW_BLUNDER_RATE


def test_phase_conclusions_are_reused_and_insufficient_remains_null():
    usable = SimpleNamespace(
        phase=GamePhase.OPENING, weakness_score=20.0, confidence=_confidence()
    )
    insufficient = SimpleNamespace(
        phase=GamePhase.ENDGAME, weakness_score=10.0,
        confidence=_confidence(ProfileConfidenceLevel.INSUFFICIENT, 0.2),
    )

    result = _build(strongest=usable, weakest=insufficient)

    assert result.strongest_phase.phase is GamePhase.OPENING
    assert result.strongest_phase.weakness_score == 20.0
    assert result.weakest_phase is None


@pytest.mark.parametrize(
    ("directions", "expected"),
    [
        ((TrendDirection.IMPROVING, TrendDirection.STABLE), OverallDirection.IMPROVING),
        ((TrendDirection.WORSENING, TrendDirection.STABLE), OverallDirection.WORSENING),
        ((TrendDirection.STABLE, TrendDirection.STABLE), OverallDirection.STABLE),
        ((TrendDirection.IMPROVING, TrendDirection.WORSENING), OverallDirection.MIXED),
        ((TrendDirection.IMPROVING,), OverallDirection.INSUFFICIENT),
    ],
)
def test_overall_direction_is_conservative(directions, expected):
    result = _build(trends=_trends(*directions))
    assert result.overall_direction is expected


def test_summary_confidence_never_exceeds_weakest_source():
    trends = _trends(TrendDirection.IMPROVING, TrendDirection.STABLE)
    trends.overall.average_cp_loss.confidence.score = 0.35
    trends.overall.average_cp_loss.confidence.level = ProfileConfidenceLevel.LOW

    result = _build(trends=trends)

    assert result.confidence.level is ProfileConfidenceLevel.LOW
    assert result.confidence.score == 0.35


def test_ready_requires_sample_coverage_and_multiple_conclusions():
    weak = SimpleNamespace(
        taxonomy=ErrorType.KING_SAFETY, score=70.0, confidence=_confidence()
    )
    strength = SimpleNamespace(
        type=PlayerStrengthType.LOW_BLUNDER_RATE, score=70.0, confidence=_confidence()
    )
    result = _build(
        weaknesses=(weak,), strengths=(strength,),
        trends=_trends(TrendDirection.STABLE, TrendDirection.STABLE),
    )
    assert result.status is PlayerIntelligenceStatus.READY


def test_summary_is_limited_when_coverage_is_partial():
    weak = SimpleNamespace(
        taxonomy=ErrorType.KING_SAFETY, score=70.0, confidence=_confidence()
    )
    result = _build(
        weaknesses=(weak,), trends=_trends(TrendDirection.STABLE, TrendDirection.STABLE),
        taxonomy_games=5,
    )
    assert result.status is PlayerIntelligenceStatus.LIMITED


def test_summary_confidence_is_bounded_for_non_finite_input():
    weak = SimpleNamespace(
        taxonomy=ErrorType.KING_SAFETY, score=70.0,
        confidence=_confidence(ProfileConfidenceLevel.LOW, float("inf")),
    )
    result = _build(weaknesses=(weak,))
    assert 0.0 <= result.confidence.score <= 1.0
