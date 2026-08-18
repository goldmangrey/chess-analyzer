import pytest

from app.models import (
    Color,
    CriticalMomentType,
    GamePhase,
    MoveAnalysis,
    MoveClassification,
)
from app.services.critical_moment_detector import (
    MATE_EVALUATION_THRESHOLD,
    detect_critical_moments,
    evaluation_to_user_pov,
)


def analyzed_move(
    ply: int,
    before: int | None,
    after: int | None,
    *,
    user: bool = True,
    loss: int = 0,
    classification: MoveClassification = MoveClassification.NORMAL,
    phase: GamePhase | None = GamePhase.MIDDLEGAME,
) -> MoveAnalysis:
    return MoveAnalysis(
        id=ply,
        game_id=1,
        ply=ply,
        move_number=(ply + 1) // 2,
        player_color=Color.WHITE if ply % 2 else Color.BLACK,
        is_user_move=user,
        fen_before="fen",
        played_move_uci="e2e4",
        played_move_san="e4",
        evaluation_before_cp=before,
        evaluation_after_cp=after,
        centipawn_loss=loss,
        classification=classification,
        phase=phase,
    )


def test_equal_to_losing_is_turning_point_for_white_user() -> None:
    moments = detect_critical_moments(
        Color.WHITE,
        [analyzed_move(31, 25, -340, loss=365, classification=MoveClassification.BLUNDER)],
    )
    assert len(moments) == 1
    assert moments[0].type is CriticalMomentType.TURNING_POINT
    assert (moments[0].evaluation_before_user_pov, moments[0].evaluation_after_user_pov) == (25, -340)


def test_winning_to_equal_is_missed_opportunity() -> None:
    moment = detect_critical_moments(
        Color.WHITE,
        [analyzed_move(21, 450, 80, loss=370, classification=MoveClassification.BLUNDER)],
    )[0]
    assert moment.type is CriticalMomentType.MISSED_OPPORTUNITY


def test_already_lost_blunder_is_contextually_suppressed() -> None:
    moments = detect_critical_moments(
        Color.WHITE,
        [analyzed_move(21, -800, -1050, loss=250, classification=MoveClassification.BLUNDER)],
    )
    assert moments == ()


def test_existing_blunder_remains_a_candidate_when_context_is_meaningful() -> None:
    moment = detect_critical_moments(
        Color.WHITE,
        [analyzed_move(17, 50, -80, loss=200, classification=MoveClassification.BLUNDER)],
    )[0]
    assert moment.type is CriticalMomentType.BLUNDER
    assert moment.severity is MoveClassification.BLUNDER


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        (MATE_EVALUATION_THRESHOLD, 200, CriticalMomentType.MISSED_MATE),
        (0, -MATE_EVALUATION_THRESHOLD, CriticalMomentType.ALLOWED_MATE),
    ],
)
def test_mate_transitions_use_explicit_types(before, after, expected) -> None:
    moment = detect_critical_moments(
        Color.WHITE,
        [analyzed_move(9, before, after, loss=1000, classification=MoveClassification.BLUNDER)],
    )[0]
    assert moment.type is expected
    assert moment.importance_score < 300  # Sentinel magnitude is not used directly.


def test_short_mate_game_and_opponent_move_are_safe() -> None:
    moments = detect_critical_moments(Color.WHITE, [
        analyzed_move(1, 0, 5),
        analyzed_move(2, 5, -MATE_EVALUATION_THRESHOLD, user=False, loss=1000, classification=MoveClassification.BLUNDER),
        analyzed_move(3, -MATE_EVALUATION_THRESHOLD, -MATE_EVALUATION_THRESHOLD, loss=0),
    ])
    assert moments == ()


def test_black_user_pov_is_explicitly_inverted() -> None:
    assert evaluation_to_user_pov(250, Color.BLACK) == -250
    moment = detect_critical_moments(
        Color.BLACK,
        [analyzed_move(18, -25, 340, loss=365, classification=MoveClassification.BLUNDER)],
    )[0]
    assert moment.type is CriticalMomentType.TURNING_POINT
    assert (moment.evaluation_before_user_pov, moment.evaluation_after_user_pov) == (25, -340)


def test_nearby_candidates_are_deduplicated_by_importance() -> None:
    moments = detect_critical_moments(Color.WHITE, [
        analyzed_move(21, 20, -180, loss=200, classification=MoveClassification.BLUNDER),
        analyzed_move(22, 400, -300, loss=700, classification=MoveClassification.BLUNDER),
        analyzed_move(23, 10, -250, loss=260, classification=MoveClassification.BLUNDER),
    ])
    assert [moment.ply for moment in moments] == [22]


def test_limit_and_fewer_than_limit_are_respected() -> None:
    moves = [
        analyzed_move(ply, 50, -200 - ply, loss=250 + ply, classification=MoveClassification.BLUNDER)
        for ply in (5, 10, 15)
    ]
    assert len(detect_critical_moments(Color.WHITE, moves, limit=2)) == 2
    assert len(detect_critical_moments(Color.WHITE, moves, limit=5)) == 3
    with pytest.raises(ValueError):
        detect_critical_moments(Color.WHITE, moves, limit=0)


def test_positive_recovery_is_best_move_and_phase_is_preserved() -> None:
    moment = detect_critical_moments(
        Color.WHITE,
        [analyzed_move(25, -200, 50, phase=GamePhase.ENDGAME)],
    )[0]
    assert moment.type is CriticalMomentType.BEST_MOVE
    assert moment.phase is GamePhase.ENDGAME


def test_quiet_game_and_old_incomplete_rows_have_no_fake_moments() -> None:
    moments = detect_critical_moments(Color.WHITE, [
        analyzed_move(1, 10, 5, phase=None),
        analyzed_move(3, None, None, loss=500, classification=MoveClassification.BLUNDER, phase=None),
    ])
    assert moments == ()
