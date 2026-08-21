from types import SimpleNamespace

import pytest

from app.models import Color
from app.services.human_chess_metrics import (
    aggregate_move_accuracy,
    build_game_accuracy,
    build_move_human_metrics,
    cp_to_win_percent,
    move_accuracy_from_win_percent,
    quality_band,
)


def move(ply, before, after, *, user=True):
    return SimpleNamespace(
        ply=ply,
        is_user_move=user,
        evaluation_before_cp=before,
        evaluation_after_cp=after,
    )


def test_cp_to_win_percent_reference_points_symmetry_and_extremes():
    assert cp_to_win_percent(0) == 50
    assert cp_to_win_percent(100) == pytest.approx(59.103, abs=0.01)
    assert cp_to_win_percent(-100) == pytest.approx(40.897, abs=0.01)
    assert cp_to_win_percent(100) + cp_to_win_percent(-100) == pytest.approx(100)
    assert cp_to_win_percent(100_000) == 100
    assert cp_to_win_percent(-100_000) == 0
    assert 99 < cp_to_win_percent(10_000) <= 100
    assert cp_to_win_percent(None) is None
    assert cp_to_win_percent(float("nan")) is None
    assert cp_to_win_percent(float("inf")) is None


def test_move_accuracy_uses_user_pov_and_never_penalizes_improvement():
    white = build_move_human_metrics(100, -100, user_color=Color.WHITE)
    black = build_move_human_metrics(-100, 100, user_color=Color.BLACK)
    improved = build_move_human_metrics(0, 100, user_color=Color.WHITE)
    assert white == black
    assert white and white.win_percent_loss > 0 and 0 <= white.accuracy < 100
    assert improved and improved.win_percent_loss == 0 and improved.accuracy == 100
    assert build_move_human_metrics(None, 0, user_color=Color.WHITE) is None


def test_move_accuracy_reference_formula_and_bounds():
    assert move_accuracy_from_win_percent(50, 50) == 100
    assert move_accuracy_from_win_percent(50, 49) == pytest.approx(96.60, abs=0.01)
    assert move_accuracy_from_win_percent(50, 40) == pytest.approx(64.58, abs=0.01)
    assert move_accuracy_from_win_percent(50, 20) == pytest.approx(25.78, abs=0.01)
    assert 0 <= move_accuracy_from_win_percent(100, 0) <= 100
    assert move_accuracy_from_win_percent(100, 0) == 0
    assert move_accuracy_from_win_percent(0, 100) == 100


def test_pooled_move_aggregate_coverage_zero_and_quality_bands():
    result = aggregate_move_accuracy([100, 80, None])
    assert result.accuracy == 90
    assert (result.eligible_moves, result.total_moves, result.coverage_rate) == (2, 3, 0.6667)
    assert aggregate_move_accuracy([0, 100]).accuracy == 50
    assert aggregate_move_accuracy([]).coverage_rate is None
    assert aggregate_move_accuracy([None]).accuracy is None
    assert [quality_band(value) for value in (95, 80, 60, 20, None)] == ["excellent", "good", "fair", "poor", None]


def test_game_accuracy_short_long_null_and_color_semantics():
    rows = [move(1, 0, 0), move(2, 0, 100, user=False), move(3, 100, 50)]
    result = build_game_accuracy(rows, user_color=Color.WHITE)
    assert result.eligible_moves == 2 and result.total_moves == 2
    assert result.accuracy is not None and 0 <= result.accuracy <= 100
    missing = build_game_accuracy([move(1, None, None)], user_color=Color.WHITE)
    assert missing.accuracy is None and missing.coverage_rate == 0
    assert build_game_accuracy([], user_color=Color.BLACK).accuracy is None
    long = build_game_accuracy([move(ply, ply * 10, ply * 10 - 5, user=ply % 2 == 1) for ply in range(1, 121)], user_color=Color.WHITE)
    assert long.eligible_moves == 60 and 0 <= long.accuracy <= 100


def test_game_accuracy_is_deterministic_and_not_simple_average():
    rows = [
        move(1, 0, -500), move(2, -500, -450, user=False),
        move(3, -450, -460), move(4, -460, -455, user=False),
        move(5, -455, -900),
    ]
    first = build_game_accuracy(rows, user_color=Color.WHITE)
    second = build_game_accuracy(rows, user_color=Color.WHITE)
    simple = sum(
        build_move_human_metrics(row.evaluation_before_cp, row.evaluation_after_cp, user_color=Color.WHITE).accuracy
        for row in rows if row.is_user_move
    ) / 3
    assert first == second
    assert first.accuracy != round(simple, 1)
