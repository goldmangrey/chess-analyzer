from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import event

from app.models import (
    AnalysisStatus,
    Color,
    Game,
    GamePhase,
    GameResult,
    MoveAnalysis,
    MoveClassification,
    TimeControlSegment,
)
from app.services.player_intelligence_service import (
    PlayerIntelligenceService,
    aggregate_player_intelligence,
)


def _game(
    game_id: int,
    *,
    color: Color = Color.WHITE,
    result: GameResult = GameResult.WIN,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    played_at: datetime | None = None,
) -> Game:
    return Game(
        id=game_id,
        external_id=f"player-{game_id}",
        played_at=played_at,
        white_username="user" if color is Color.WHITE else "opponent",
        black_username="user" if color is Color.BLACK else "opponent",
        user_color=color,
        result=result,
        pgn="1. e4 *",
        analysis_status=status,
    )


def _move(
    game_id: int,
    ply: int,
    *,
    user: bool,
    loss: int | None = 0,
    classification: MoveClassification | None = MoveClassification.NORMAL,
    phase: GamePhase | None = GamePhase.OPENING,
    evaluations: bool = True,
):
    return SimpleNamespace(
        game_id=game_id,
        ply=ply,
        is_user_move=user,
        centipawn_loss=loss,
        classification=classification,
        phase=phase,
        evaluation_before_cp=0 if evaluations else None,
        evaluation_after_cp=0 if evaluations else None,
    )


def test_empty_profile_is_null_safe():
    profile = aggregate_player_intelligence([], [], requested_games=30)

    assert profile.intelligence_version == "1"
    assert profile.window.available_analyzed_games == 0
    assert profile.sample.games == 0
    assert profile.sample.user_moves == 0
    assert profile.overall.average_cp_loss is None
    assert profile.overall.mistakes_per_game is None
    assert profile.overall.blunders_per_100_moves is None
    assert profile.overall.blunder_free_rate is None


def test_aggregation_uses_only_user_moves_and_is_move_weighted():
    games = [
        _game(1, color=Color.WHITE, result=GameResult.WIN),
        _game(2, color=Color.BLACK, result=GameResult.LOSS),
    ]
    moves = [
        _move(1, 1, user=True, loss=100, classification=MoveClassification.INACCURACY),
        _move(1, 2, user=False, loss=1000, classification=MoveClassification.BLUNDER),
        _move(2, 1, user=False, loss=900, classification=MoveClassification.BLUNDER),
        _move(2, 2, user=True, loss=200, classification=MoveClassification.MISTAKE),
        _move(2, 4, user=True, loss=300, classification=MoveClassification.BLUNDER),
    ]

    profile = aggregate_player_intelligence(games, moves, requested_games=30)

    assert profile.sample.user_moves == 3
    assert profile.sample.white_games == 1
    assert profile.sample.black_games == 1
    assert (profile.sample.wins, profile.sample.losses) == (1, 1)
    assert profile.overall.average_cp_loss == 200.0
    assert profile.overall.inaccuracies == 1
    assert profile.overall.mistakes == 1
    assert profile.overall.blunders == 1
    assert profile.overall.mistakes_per_game == 0.5
    assert profile.overall.blunders_per_100_moves == pytest.approx(100 / 3)


def test_null_legacy_values_are_excluded_from_their_coverage_denominators():
    games = [_game(1), _game(2)]
    moves = [
        _move(1, 1, user=True, loss=120, classification=None, phase=None, evaluations=False),
        _move(1, 3, user=True, loss=None, classification=MoveClassification.MISTAKE),
    ]

    profile = aggregate_player_intelligence(games, moves, requested_games=10)

    assert profile.overall.average_cp_loss == 120.0
    assert profile.overall.mistakes == 1
    assert profile.data_quality.moves_with_cp_loss == 1
    assert profile.data_quality.moves_with_classification == 1
    assert profile.data_quality.games_with_move_analysis == 1
    assert profile.data_quality.games_with_phase_data == 1
    assert profile.data_quality.games_with_complete_evaluations == 0


def test_all_null_cp_loss_produces_null_average_without_non_finite_values():
    profile = aggregate_player_intelligence(
        [_game(1)],
        [_move(1, 1, user=True, loss=None)],
        requested_games=30,
    )

    assert profile.overall.average_cp_loss is None
    assert profile.data_quality.moves_with_cp_loss == 0


def test_blunder_free_requires_usable_user_move_analysis():
    games = [_game(1), _game(2), _game(3)]
    moves = [
        _move(1, 1, user=True),
        _move(1, 2, user=False, classification=MoveClassification.BLUNDER),
        _move(2, 2, user=True, classification=MoveClassification.BLUNDER),
    ]

    profile = aggregate_player_intelligence(games, moves, requested_games=30)

    assert profile.overall.blunder_free_games == 1
    assert profile.overall.blunder_free_rate == 0.5
    assert profile.data_quality.games_with_move_analysis == 2


def test_zero_user_moves_does_not_divide_by_zero():
    profile = aggregate_player_intelligence(
        [_game(1)],
        [_move(1, 2, user=False, classification=MoveClassification.BLUNDER)],
        requested_games=30,
    )

    assert profile.sample.user_moves == 0
    assert profile.overall.inaccuracies_per_100_moves is None
    assert profile.overall.mistakes_per_100_moves is None
    assert profile.overall.blunders_per_100_moves is None
    assert profile.overall.blunder_free_games == 0


def test_invalid_legacy_color_and_result_do_not_break_profile():
    game = SimpleNamespace(id=1, user_color="legacy", result=None)

    profile = aggregate_player_intelligence([game], [], requested_games=30)

    assert profile.sample.games == 1
    assert profile.sample.white_games == 0
    assert profile.sample.black_games == 0
    assert profile.sample.wins == 0
    assert profile.sample.draws == 0
    assert profile.sample.losses == 0


def test_service_selects_only_latest_completed_games_with_stable_id_tie_break(db_session):
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _game(1, played_at=timestamp),
            _game(2, played_at=timestamp),
            _game(3, played_at=datetime(2025, 1, 1, tzinfo=timezone.utc)),
            _game(4, status=AnalysisStatus.FAILED, played_at=datetime(2027, 1, 1, tzinfo=timezone.utc)),
            _game(5, status=AnalysisStatus.PENDING, played_at=datetime(2028, 1, 1, tzinfo=timezone.utc)),
        ]
    )
    db_session.flush()
    db_session.add(
        MoveAnalysis(
            game_id=2,
            ply=1,
            move_number=1,
            player_color=Color.WHITE,
            is_user_move=True,
            fen_before="start",
            played_move_uci="e2e4",
            centipawn_loss=55,
            classification=MoveClassification.NORMAL,
        )
    )
    db_session.commit()

    profile = PlayerIntelligenceService(db_session).build(window=1)

    assert profile.sample.games == 1
    assert profile.sample.user_moves == 1
    assert profile.overall.average_cp_loss == 55.0


def test_service_uses_at_most_two_select_queries(db_session, test_engine):
    db_session.add(_game(1))
    db_session.commit()
    selects = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        nonlocal selects
        if statement.lstrip().upper().startswith("SELECT"):
            selects += 1

    event.listen(test_engine, "before_cursor_execute", count_selects)
    try:
        PlayerIntelligenceService(db_session).build(window=30)
    finally:
        event.remove(test_engine, "before_cursor_execute", count_selects)

    assert selects <= 2


def test_current_window_isolated_from_previous_trend_and_segments(db_session):
    games = []
    for game_id, loss, time_control in (
        (1, 200, "300"),
        (2, 100, "300"),
        (3, 20, "600"),
        (4, 10, "60"),
    ):
        game = _game(
            game_id,
            played_at=datetime(2026, 1, game_id, tzinfo=timezone.utc),
        )
        game.time_control = time_control
        db_session.add(game)
        games.append((game, loss))
    db_session.flush()
    for game, loss in games:
        db_session.add(
            MoveAnalysis(
                game_id=game.id,
                ply=1,
                move_number=1,
                player_color=Color.WHITE,
                is_user_move=True,
                fen_before="legacy",
                played_move_uci="e2e4",
                centipawn_loss=loss,
                classification=MoveClassification.NORMAL,
            )
        )
    db_session.commit()

    profile = PlayerIntelligenceService(db_session).build(window=2)

    assert profile.sample.games == 2
    assert profile.sample.user_moves == 2
    assert profile.overall.average_cp_loss == 15
    assert profile.trends.recent_games == 2
    assert profile.trends.previous_games == 2
    assert profile.trends.overall.average_cp_loss.recent == 15
    assert profile.trends.overall.average_cp_loss.previous == 150
    assert profile.segments.time_controls[TimeControlSegment.BULLET].games == 1
    assert profile.segments.time_controls[TimeControlSegment.RAPID].games == 1
    assert profile.segments.time_controls[TimeControlSegment.BLITZ].games == 0
