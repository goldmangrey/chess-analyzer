from types import SimpleNamespace

import pytest

from app.models import GamePhase, MoveClassification, ProfileConfidenceLevel
from app.services.player_phase_intelligence import (
    PHASE_SCORE_TIE_EPSILON,
    build_phase_intelligence,
)


def _move(
    game_id,
    ply,
    *,
    phase=GamePhase.OPENING,
    classification=MoveClassification.NORMAL,
    loss=0,
    user=True,
):
    return SimpleNamespace(
        game_id=game_id,
        ply=ply,
        phase=phase,
        classification=classification,
        centipawn_loss=loss,
        is_user_move=user,
    )


def _phase_sample(
    phase,
    *,
    first_game,
    games=5,
    moves_per_game=10,
    loss=20,
    serious=0,
):
    moves = []
    index = 0
    for game_id in range(first_game, first_game + games):
        for ply in range(1, moves_per_game * 2, 2):
            classification = (
                MoveClassification.MISTAKE
                if index < serious
                else MoveClassification.NORMAL
            )
            moves.append(
                _move(
                    game_id,
                    ply,
                    phase=phase,
                    classification=classification,
                    loss=loss,
                )
            )
            index += 1
    return moves


def test_empty_and_all_null_phase_profiles_are_safe():
    empty = build_phase_intelligence((), sample_games=0)
    assert set(empty.phases) == set(GamePhase)
    assert all(metrics.user_moves == 0 for metrics in empty.phases.values())
    assert all(metrics.average_cp_loss is None for metrics in empty.phases.values())
    assert empty.profile.strongest_phase is None
    assert empty.profile.weakest_phase is None

    legacy = build_phase_intelligence(
        (_move(1, 1, phase=None), _move(1, 3, phase="legacy")),
        sample_games=1,
    )
    assert legacy.moves_with_phase == 0
    assert legacy.moves_without_phase == 2


def test_phase_metrics_are_user_only_weighted_and_null_safe():
    result = build_phase_intelligence(
        (
            _move(1, 1, loss=100, classification=MoveClassification.INACCURACY),
            _move(1, 2, loss=900, classification=MoveClassification.BLUNDER, user=False),
            _move(1, 3, loss=200, classification=MoveClassification.MISTAKE),
            _move(2, 1, loss=None, classification=MoveClassification.BLUNDER),
        ),
        sample_games=3,
    )
    opening = result.phases[GamePhase.OPENING]

    assert opening.user_moves == 3
    assert opening.games_with_phase == 2
    assert opening.participation_rate == pytest.approx(2 / 3)
    assert opening.average_cp_loss == 150
    assert opening.moves_with_cp_loss == 2
    assert (opening.inaccuracies, opening.mistakes, opening.blunders) == (1, 1, 1)
    assert opening.serious_errors == 2
    assert opening.inaccuracies_per_100_moves == pytest.approx(100 / 3)
    assert opening.mistakes_per_100_moves == pytest.approx(100 / 3)
    assert opening.blunders_per_100_moves == pytest.approx(100 / 3)
    assert opening.serious_errors_per_100_moves == pytest.approx(200 / 3)


def test_all_null_cp_loss_keeps_counts_but_returns_null_acpl():
    result = build_phase_intelligence(
        (_move(1, 1, phase=GamePhase.ENDGAME, loss=None, classification=None),),
        sample_games=1,
    )
    endgame = result.phases[GamePhase.ENDGAME]
    assert endgame.user_moves == 1
    assert endgame.average_cp_loss is None
    assert endgame.moves_with_classification == 0
    assert endgame.serious_errors_per_100_moves == 0


def test_all_three_phases_and_coverage_invariants():
    moves = (
        _move(1, 1, phase=GamePhase.OPENING),
        _move(1, 3, phase=GamePhase.MIDDLEGAME),
        _move(2, 1, phase=GamePhase.ENDGAME),
        _move(2, 3, phase=None),
    )
    result = build_phase_intelligence(moves, sample_games=2)
    assert [result.phases[phase].user_moves for phase in GamePhase] == [1, 1, 1]
    assert result.moves_with_phase == 3
    assert result.moves_without_phase == 1
    assert result.moves_with_phase + result.moves_without_phase == 4
    for metrics in result.phases.values():
        assert metrics.inaccuracies + metrics.mistakes + metrics.blunders <= metrics.moves_with_classification
        assert metrics.serious_errors == metrics.mistakes + metrics.blunders


def test_score_components_are_bounded_and_worse_inputs_raise_score():
    strong = _phase_sample(GamePhase.OPENING, first_game=1, loss=20, serious=0)
    weak = _phase_sample(GamePhase.MIDDLEGAME, first_game=1, loss=100, serious=15)
    result = build_phase_intelligence((*strong, *weak), sample_games=5)
    opening = result.profile.performance[GamePhase.OPENING]
    middle = result.profile.performance[GamePhase.MIDDLEGAME]

    assert 0 <= opening.weakness_score <= 100
    assert 0 <= middle.weakness_score <= 100
    assert all(0 <= value <= 1 for value in vars(opening.components).values())
    assert middle.components.acpl > opening.components.acpl
    assert middle.components.serious_error_rate > opening.components.serious_error_rate
    assert middle.weakness_score > opening.weakness_score


def test_strongest_weakest_ignore_insufficient_phase():
    opening = _phase_sample(GamePhase.OPENING, first_game=1, loss=20)
    middle = _phase_sample(GamePhase.MIDDLEGAME, first_game=1, loss=100, serious=15)
    tiny_endgame = _phase_sample(
        GamePhase.ENDGAME,
        first_game=1,
        games=1,
        moves_per_game=8,
        loss=1,
    )
    result = build_phase_intelligence(
        (*opening, *middle, *tiny_endgame),
        sample_games=5,
    )

    assert result.profile.performance[GamePhase.ENDGAME].confidence.level == ProfileConfidenceLevel.INSUFFICIENT
    assert result.profile.strongest_phase.phase == GamePhase.OPENING
    assert result.profile.weakest_phase.phase == GamePhase.MIDDLEGAME


def test_one_eligible_phase_or_tied_phases_do_not_create_fake_comparison():
    opening = _phase_sample(GamePhase.OPENING, first_game=1, loss=20)
    one = build_phase_intelligence(opening, sample_games=5)
    assert one.profile.strongest_phase is None
    assert one.profile.weakest_phase is None

    middle = _phase_sample(GamePhase.MIDDLEGAME, first_game=1, loss=20)
    tied = build_phase_intelligence((*opening, *middle), sample_games=5)
    assert tied.profile.strongest_phase is None
    assert tied.profile.weakest_phase is None
    scores = [
        tied.profile.performance[phase].weakness_score
        for phase in (GamePhase.OPENING, GamePhase.MIDDLEGAME)
    ]
    assert abs(scores[0] - scores[1]) < PHASE_SCORE_TIE_EPSILON


def test_phase_confidence_improves_with_support_and_reflects_participation():
    tiny = build_phase_intelligence(
        _phase_sample(GamePhase.ENDGAME, first_game=1, games=2, moves_per_game=5),
        sample_games=30,
    ).profile.performance[GamePhase.ENDGAME].confidence
    supported = build_phase_intelligence(
        _phase_sample(GamePhase.ENDGAME, first_game=1, games=20, moves_per_game=25),
        sample_games=30,
    ).profile.performance[GamePhase.ENDGAME].confidence
    assert tiny.level == ProfileConfidenceLevel.INSUFFICIENT
    assert tiny.coverage_rate == pytest.approx(0.0667)
    assert supported.score > tiny.score
    assert supported.level != ProfileConfidenceLevel.INSUFFICIENT


def test_first_serious_breakdown_uses_first_user_error_and_exactly_one_bucket():
    moves = (
        _move(1, 1, classification=MoveClassification.INACCURACY),
        _move(1, 3, phase=GamePhase.MIDDLEGAME, classification=MoveClassification.MISTAKE),
        _move(1, 5, phase=GamePhase.ENDGAME, classification=MoveClassification.BLUNDER),
        _move(2, 1, classification=MoveClassification.BLUNDER, user=False),
        _move(2, 2, phase=GamePhase.OPENING, classification=MoveClassification.MISTAKE),
        _move(3, 1, classification=MoveClassification.NORMAL),
        _move(4, 5, phase=None, classification=MoveClassification.BLUNDER),
    )
    breakdown = build_phase_intelligence(moves, sample_games=5).profile.first_serious_breakdown

    assert breakdown.eligible_games == 4
    assert breakdown.games_with_serious_error == 3
    assert (breakdown.opening, breakdown.middlegame, breakdown.endgame) == (1, 1, 0)
    assert breakdown.unknown == 1
    assert breakdown.no_serious_error == 1
    assert breakdown.opening_share == pytest.approx(1 / 3)
    assert breakdown.middlegame_share == pytest.approx(1 / 3)
    assert breakdown.unknown_share == pytest.approx(1 / 3)
    assert (
        breakdown.opening
        + breakdown.middlegame
        + breakdown.endgame
        + breakdown.unknown
        + breakdown.no_serious_error
        == breakdown.eligible_games
    )


def test_first_serious_breakdown_explicitly_orders_by_ply():
    moves = (
        _move(1, 9, phase=GamePhase.ENDGAME, classification=MoveClassification.BLUNDER),
        _move(1, 3, phase=GamePhase.OPENING, classification=MoveClassification.MISTAKE),
    )
    breakdown = build_phase_intelligence(moves, sample_games=1).profile.first_serious_breakdown
    assert breakdown.opening == 1
    assert breakdown.endgame == 0
