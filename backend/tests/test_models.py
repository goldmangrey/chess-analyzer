from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AnalysisStatus,
    Color,
    Game,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)


def make_game(external_id: str = "game-1", **overrides: object) -> Game:
    values = {
        "external_id": external_id,
        "white_username": "Yeskendir",
        "black_username": "Opponent",
        "user_color": Color.WHITE,
        "result": GameResult.WIN,
        "pgn": "1. e4 e5",
    }
    values.update(overrides)
    return Game(**values)


def make_move(game: Game, ply: int = 1, **overrides: object) -> MoveAnalysis:
    values = {
        "game": game,
        "ply": ply,
        "move_number": (ply + 1) // 2,
        "player_color": Color.WHITE if ply % 2 else Color.BLACK,
        "is_user_move": ply % 2 == 1,
        "fen_before": "initial-fen",
        "played_move_uci": "e2e4" if ply % 2 else "e7e5",
        "centipawn_loss": 0,
        "classification": MoveClassification.NORMAL,
    }
    values.update(overrides)
    return MoveAnalysis(**values)


def commit_expect_integrity_error(session: Session, instance: object) -> None:
    session.add(instance)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_game_is_saved_with_defaults_and_timestamps(db_session: Session) -> None:
    game = make_game()
    db_session.add(game)
    db_session.commit()

    assert game.id is not None
    assert game.platform == "chess.com"
    assert game.analysis_status is AnalysisStatus.PENDING
    assert isinstance(game.created_at, datetime)
    assert isinstance(game.updated_at, datetime)


def test_external_id_is_unique(db_session: Session) -> None:
    db_session.add(make_game("duplicate"))
    db_session.commit()

    commit_expect_integrity_error(db_session, make_game("duplicate"))


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("user_color", "green"),
        ("result", "unknown"),
        ("analysis_status", "queued"),
    ],
)
def test_invalid_game_enum_values_are_rejected_by_database(
    db_session: Session,
    field: str,
    invalid_value: str,
) -> None:
    commit_expect_integrity_error(
        db_session,
        make_game(**{field: invalid_value}),
    )


def test_both_players_moves_are_stored(db_session: Session) -> None:
    game = make_game()
    white_move = make_move(game, 1, is_user_move=True)
    black_move = make_move(game, 2, is_user_move=False)
    db_session.add_all([game, white_move, black_move])
    db_session.commit()

    moves = db_session.scalars(
        select(MoveAnalysis).order_by(MoveAnalysis.ply)
    ).all()
    assert [(move.player_color, move.is_user_move) for move in moves] == [
        (Color.WHITE, True),
        (Color.BLACK, False),
    ]


def test_user_move_flags_can_be_reversed_for_black_user(
    db_session: Session,
) -> None:
    game = make_game(user_color=Color.BLACK)
    game.move_analyses = [
        make_move(game, 1, is_user_move=False),
        make_move(game, 2, is_user_move=True),
    ]
    db_session.add(game)
    db_session.commit()

    assert [move.is_user_move for move in game.move_analyses] == [False, True]


def test_duplicate_game_and_ply_is_rejected(db_session: Session) -> None:
    game = make_game()
    db_session.add_all([game, make_move(game, 1)])
    db_session.commit()

    commit_expect_integrity_error(db_session, make_move(game, 1))


def test_same_ply_is_allowed_for_different_games(db_session: Session) -> None:
    first = make_game("first")
    second = make_game("second")
    db_session.add_all([make_move(first, 1), make_move(second, 1)])
    db_session.commit()

    assert len(db_session.scalars(select(MoveAnalysis)).all()) == 2


@pytest.mark.parametrize(
    ("overrides"),
    [
        {"centipawn_loss": -1},
        {"ply": 0},
        {"move_number": 0},
        {"classification": "excellent"},
        {"player_color": "green"},
    ],
)
def test_invalid_move_values_are_rejected_by_database(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    game = make_game()
    commit_expect_integrity_error(db_session, make_move(game, **overrides))


def test_deleting_game_cascades_to_moves(db_session: Session) -> None:
    game = make_game()
    game.move_analyses.append(make_move(game, 1))
    db_session.add(game)
    db_session.commit()

    db_session.delete(game)
    db_session.commit()

    assert db_session.scalars(select(MoveAnalysis)).all() == []


def test_relationship_orders_moves_by_ply(db_session: Session) -> None:
    game = make_game()
    game.move_analyses = [make_move(game, 3), make_move(game, 1), make_move(game, 2)]
    db_session.add(game)
    db_session.commit()
    db_session.expire(game, ["move_analyses"])

    assert [move.ply for move in game.move_analyses] == [1, 2, 3]
