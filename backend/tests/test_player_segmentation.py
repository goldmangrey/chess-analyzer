from types import SimpleNamespace

import pytest

from app.models import Color, GameResult, ProfileConfidenceLevel, TimeControlSegment
from app.services.player_segmentation import build_player_segments, classify_time_control


def _game(game_id, time_control, color, result=GameResult.WIN):
    return SimpleNamespace(
        id=game_id,
        time_control=time_control,
        user_color=color,
        result=result,
    )


def _move(game_id, loss, classification, *, user=True):
    return SimpleNamespace(
        game_id=game_id,
        is_user_move=user,
        centipawn_loss=loss,
        classification=classification,
    )


def test_time_control_classifier_uses_estimated_duration():
    assert classify_time_control("60") == TimeControlSegment.BULLET
    assert classify_time_control("180") == TimeControlSegment.BLITZ
    assert classify_time_control("180+2") == TimeControlSegment.BLITZ
    assert classify_time_control("300") == TimeControlSegment.BLITZ
    assert classify_time_control("600") == TimeControlSegment.RAPID
    assert classify_time_control("900+10") == TimeControlSegment.RAPID
    assert classify_time_control(None) == TimeControlSegment.UNKNOWN
    assert classify_time_control("1/86400") == TimeControlSegment.UNKNOWN
    assert classify_time_control("invalid") == TimeControlSegment.UNKNOWN


def test_segments_have_stable_empty_keys_and_insufficient_confidence():
    segments = build_player_segments((), ())
    assert set(segments.time_controls) == set(TimeControlSegment)
    assert set(segments.colors) == set(Color)
    assert all(item.games == 0 and item.average_cp_loss is None for item in segments.time_controls.values())
    assert all(item.confidence.level == ProfileConfidenceLevel.INSUFFICIENT for item in segments.colors.values())


def test_time_segments_reuse_weighted_user_move_metrics_and_results():
    from app.models import MoveClassification

    games = (
        _game(1, "60", Color.WHITE, GameResult.WIN),
        _game(2, "60", Color.BLACK, GameResult.LOSS),
        _game(3, "600", Color.WHITE, GameResult.DRAW),
        _game(4, None, Color.WHITE, GameResult.WIN),
    )
    moves = (
        _move(1, 100, MoveClassification.MISTAKE),
        _move(1, 900, MoveClassification.BLUNDER, user=False),
        _move(2, 200, MoveClassification.BLUNDER),
        _move(2, 300, MoveClassification.NORMAL),
        _move(3, 20, MoveClassification.NORMAL),
        _move(4, 40, MoveClassification.NORMAL),
    )
    segments = build_player_segments(games, moves)
    bullet = segments.time_controls[TimeControlSegment.BULLET]
    rapid = segments.time_controls[TimeControlSegment.RAPID]
    unknown = segments.time_controls[TimeControlSegment.UNKNOWN]

    assert bullet.games == 2 and bullet.user_moves == 3
    assert bullet.average_cp_loss == 200
    assert bullet.mistakes_per_100_moves == pytest.approx(100 / 3)
    assert bullet.blunders_per_100_moves == pytest.approx(100 / 3)
    assert bullet.serious_errors_per_100_moves == pytest.approx(200 / 3)
    assert bullet.blunder_free_rate == 0.5
    assert (bullet.wins, bullet.draws, bullet.losses) == (1, 0, 1)
    assert rapid.games == 1 and rapid.average_cp_loss == 20
    assert unknown.games == 1
    assert segments.games_with_known_time_control == 3
    assert segments.games_with_known_color == 4


def test_color_segments_exclude_invalid_color_and_keep_current_moves_only():
    from app.models import MoveClassification

    games = (
        _game(1, "300", Color.WHITE, GameResult.WIN),
        _game(2, "300", Color.BLACK, GameResult.LOSS),
        _game(3, "300", "legacy", GameResult.DRAW),
    )
    moves = (
        _move(1, 20, MoveClassification.NORMAL),
        _move(2, 100, MoveClassification.MISTAKE),
        _move(2, 900, MoveClassification.BLUNDER, user=False),
        _move(3, 500, MoveClassification.BLUNDER),
    )
    segments = build_player_segments(games, moves)
    white = segments.colors[Color.WHITE]
    black = segments.colors[Color.BLACK]

    assert (white.games, white.user_moves, white.average_cp_loss) == (1, 1, 20)
    assert (black.games, black.user_moves, black.average_cp_loss) == (1, 1, 100)
    assert (white.wins, white.losses) == (1, 0)
    assert (black.wins, black.losses) == (0, 1)
    assert segments.games_with_known_color == 2


def test_segment_confidence_increases_with_real_support():
    from app.models import MoveClassification

    tiny_games = (_game(1, "60", Color.WHITE),)
    tiny_moves = (_move(1, 0, MoveClassification.NORMAL),)
    supported_games = tuple(_game(index, "60", Color.WHITE) for index in range(1, 11))
    supported_moves = tuple(
        _move(game.id, 10, MoveClassification.NORMAL)
        for game in supported_games
        for _ in range(10)
    )
    tiny = build_player_segments(tiny_games, tiny_moves).time_controls[TimeControlSegment.BULLET]
    supported = build_player_segments(supported_games, supported_moves).time_controls[TimeControlSegment.BULLET]
    assert tiny.confidence.level == ProfileConfidenceLevel.INSUFFICIENT
    assert supported.confidence.score > tiny.confidence.score
