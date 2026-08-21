from types import SimpleNamespace

import pytest

from app.models import (
    ErrorType,
    MoveClassification,
    PlayerStrengthType,
    ProfileConfidenceLevel,
)
from app.services.player_profile_scoring import (
    MAX_STRENGTHS,
    MAX_WEAKNESSES,
    build_profile_confidence,
    build_strengths,
    build_weaknesses,
)
from app.services.player_recurring_errors import (
    RecurringError,
    RecurringErrorEvidence,
    RecurringErrorPhases,
    RecurringErrorSeverity,
)


def _sample(games=30, moves=500):
    return SimpleNamespace(games=games, user_moves=moves)


def _quality(
    *,
    game_moves=30,
    cp_moves=500,
    classified_moves=500,
    taxonomy_games=30,
    taxonomy_moves=500,
):
    return SimpleNamespace(
        games_with_move_analysis=game_moves,
        moves_with_cp_loss=cp_moves,
        moves_with_classification=classified_moves,
        games_with_taxonomy_data=taxonomy_games,
        moves_eligible_for_taxonomy=taxonomy_moves,
    )


def _overall(
    *,
    acpl=40.0,
    mistakes=1.0,
    blunders=0.5,
    blunder_free=0.7,
):
    return SimpleNamespace(
        average_cp_loss=acpl,
        mistakes_per_100_moves=mistakes,
        blunders_per_100_moves=blunders,
        blunder_free_rate=blunder_free,
    )


def _recurring(
    taxonomy=ErrorType.KING_SAFETY,
    *,
    incidents=4,
    games=3,
    rate=0.3,
    per_100=1.0,
    inaccuracies=1,
    mistakes=2,
    blunders=1,
):
    evidence = (
        RecurringErrorEvidence(
            game_id=10,
            ply=7,
            classification=MoveClassification.BLUNDER,
            phase=None,
            played_move_san="Qh5",
            played_move_uci="d1h5",
            centipawn_loss=300,
        ),
    )
    return RecurringError(
        taxonomy=taxonomy,
        incidents=incidents,
        games_affected=games,
        games_affected_rate=rate,
        incidents_per_game=incidents / 10,
        incidents_per_100_moves=per_100,
        severity=RecurringErrorSeverity(
            inaccuracies=inaccuracies,
            mistakes=mistakes,
            blunders=blunders,
        ),
        phases=RecurringErrorPhases(opening=0, middlegame=incidents, endgame=0, unknown=0),
        evidence=evidence,
    )


def test_no_recurring_errors_produces_no_weaknesses():
    assert build_weaknesses((), _sample(), _quality()) == ()


def test_weakness_components_and_final_score_are_bounded_and_deterministic():
    recurring = _recurring(per_100=1_000, games=1_000, rate=4.0)

    first = build_weaknesses((recurring,), _sample(), _quality())[0]
    second = build_weaknesses((recurring,), _sample(), _quality())[0]

    assert first == second
    assert 0 <= first.score <= 100
    assert all(0 <= value <= 1 for value in vars(first.components).values())
    assert first.components.frequency == 1
    assert first.components.recurrence == 1


def test_wider_spread_and_more_severe_distribution_raise_weakness_score():
    narrow = _recurring(rate=0.1, inaccuracies=4, mistakes=0, blunders=0)
    wide = _recurring(rate=0.5, inaccuracies=4, mistakes=0, blunders=0)
    severe = _recurring(rate=0.1, inaccuracies=0, mistakes=0, blunders=4)

    narrow_score = build_weaknesses((narrow,), _sample(), _quality())[0]
    wide_score = build_weaknesses((wide,), _sample(), _quality())[0]
    severe_score = build_weaknesses((severe,), _sample(), _quality())[0]

    assert wide_score.components.spread > narrow_score.components.spread
    assert wide_score.score > narrow_score.score
    assert severe_score.components.severity > narrow_score.components.severity
    assert severe_score.score > narrow_score.score


def test_same_incident_count_across_more_games_has_more_spread_and_recurrence():
    concentrated = _recurring(incidents=4, games=2, rate=0.2)
    distributed = _recurring(incidents=4, games=4, rate=0.4)

    concentrated_result = build_weaknesses(
        (concentrated,), _sample(), _quality()
    )[0]
    distributed_result = build_weaknesses((distributed,), _sample(), _quality())[0]

    assert distributed_result.components.spread > concentrated_result.components.spread
    assert (
        distributed_result.components.recurrence
        > concentrated_result.components.recurrence
    )
    assert distributed_result.score > concentrated_result.score


def test_weakness_order_limit_tie_break_and_evidence_reuse():
    recurring = tuple(
        _recurring(taxonomy, rate=0.3, games=3)
        for taxonomy in (
            ErrorType.PIN,
            ErrorType.FORK,
            ErrorType.KING_SAFETY,
            ErrorType.BAD_EXCHANGE,
            ErrorType.DEVELOPMENT,
            ErrorType.PAWN_STRUCTURE,
        )
    )

    weaknesses = build_weaknesses(recurring, _sample(), _quality())

    assert len(weaknesses) == MAX_WEAKNESSES
    assert [item.rank for item in weaknesses] == list(range(1, MAX_WEAKNESSES + 1))
    assert [item.taxonomy.value for item in weaknesses] == sorted(
        item.taxonomy.value for item in weaknesses
    )
    source = next(item for item in recurring if item.taxonomy == weaknesses[0].taxonomy)
    assert weaknesses[0].evidence is source.evidence


def test_confidence_is_coverage_and_sample_aware_with_insufficient_state():
    tiny = build_profile_confidence(
        sample_games=3,
        eligible_games=2,
        eligible_user_moves=40,
        pattern_support_games=2,
    )
    poor_coverage = build_profile_confidence(
        sample_games=30,
        eligible_games=6,
        eligible_user_moves=100,
        pattern_support_games=2,
    )
    strong = build_profile_confidence(
        sample_games=30,
        eligible_games=30,
        eligible_user_moves=500,
        pattern_support_games=10,
    )

    assert tiny.level == ProfileConfidenceLevel.INSUFFICIENT
    assert poor_coverage.level == ProfileConfidenceLevel.LOW
    assert strong.level == ProfileConfidenceLevel.HIGH
    assert 0 <= tiny.score < poor_coverage.score < strong.score <= 1
    assert poor_coverage.coverage_rate == 0.2


def test_weakness_can_exist_with_explicit_insufficient_confidence():
    weakness = build_weaknesses(
        (_recurring(games=2, rate=2 / 3),),
        _sample(games=3, moves=40),
        _quality(taxonomy_games=2, taxonomy_moves=40),
    )[0]
    assert weakness.confidence.level == ProfileConfidenceLevel.INSUFFICIENT


def test_no_strengths_without_sample_or_user_moves():
    assert build_strengths(_overall(), _sample(games=0, moves=0), _quality()) == ()
    assert build_strengths(_overall(), _sample(games=1, moves=0), _quality()) == ()


def test_allowed_strength_types_use_independent_objective_metrics():
    strengths = build_strengths(_overall(), _sample(), _quality(), limit=10)
    found = {item.type: item for item in strengths}

    assert set(found) == {
        PlayerStrengthType.LOW_BLUNDER_RATE,
        PlayerStrengthType.BLUNDER_FREE_CONSISTENCY,
        PlayerStrengthType.LOW_MISTAKE_RATE,
        PlayerStrengthType.OVERALL_PRECISION,
    }
    assert found[PlayerStrengthType.LOW_BLUNDER_RATE].metrics == {
        "blunders_per_100_moves": 0.5
    }
    assert all(0 <= item.score <= 100 for item in strengths)
    assert all(0 <= item.normalized_component <= 1 for item in strengths)


def test_poor_or_null_metrics_do_not_create_fake_strengths():
    strengths = build_strengths(
        _overall(acpl=None, mistakes=4.0, blunders=2.0, blunder_free=0.2),
        _sample(),
        _quality(),
        limit=10,
    )
    assert strengths == ()


def test_one_clean_game_strength_candidate_is_insufficient_not_high_confidence():
    strengths = build_strengths(
        _overall(acpl=0, mistakes=0, blunders=0, blunder_free=1),
        _sample(games=1, moves=20),
        _quality(game_moves=1, cp_moves=20, classified_moves=20),
    )
    assert strengths
    assert all(
        item.confidence.level == ProfileConfidenceLevel.INSUFFICIENT
        for item in strengths
    )


def test_strength_order_limit_and_no_taxonomy_or_phase_conclusions():
    strengths = build_strengths(_overall(), _sample(), _quality())
    assert len(strengths) == MAX_STRENGTHS
    assert [item.rank for item in strengths] == [1, 2, 3]
    assert [item.score for item in strengths] == sorted(
        (item.score for item in strengths), reverse=True
    )
    assert all(item.type in PlayerStrengthType for item in strengths)
    assert all("phase" not in key for item in strengths for key in item.metrics)


def test_strengths_are_independent_from_weaknesses():
    strengths = build_strengths(_overall(), _sample(), _quality())
    weaknesses = build_weaknesses(
        (_recurring(ErrorType.KING_SAFETY),),
        _sample(),
        _quality(),
    )
    assert strengths and weaknesses
    assert all(not hasattr(item, "taxonomy") for item in strengths)
