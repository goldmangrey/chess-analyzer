from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AnalysisStatus, Color, GameResult, MoveClassification
from app.repositories.games_repository import (
    create_game,
    external_id_exists,
    get_game_by_external_id,
    get_game_by_id,
    list_analyzable_games,
    list_games,
    list_games_by_analysis_status,
    set_analysis_status,
)
from app.repositories.move_analysis_repository import create_move_analysis
from app.schemas import GameCreate, MoveAnalysisCreate


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def game_data(external_id: str, **overrides: object) -> GameCreate:
    values = {
        "external_id": external_id,
        "played_at": NOW,
        "white_username": "Yeskendir",
        "black_username": "Opponent",
        "user_color": Color.WHITE,
        "result": GameResult.WIN,
        "opening_code": "C20",
        "opening_name": "King's Pawn Game",
        "pgn": "1. e4 e5",
    }
    values.update(overrides)
    return GameCreate(**values)


def move_data(
    game_id: int,
    ply: int,
    *,
    user: bool,
    loss: int,
    classification: MoveClassification = MoveClassification.NORMAL,
) -> MoveAnalysisCreate:
    return MoveAnalysisCreate(
        game_id=game_id,
        ply=ply,
        move_number=(ply + 1) // 2,
        player_color=Color.WHITE if ply % 2 else Color.BLACK,
        is_user_move=user,
        fen_before="fen",
        played_move_uci="e2e4" if ply % 2 else "e7e5",
        centipawn_loss=loss,
        classification=classification,
    )


def test_create_flushes_id_without_committing(db_session: Session) -> None:
    game = create_game(db_session, game_data("uncommitted"))
    assert game.id is not None

    db_session.rollback()
    assert get_game_by_external_id(db_session, "uncommitted") is None


def test_get_and_exists_operations(db_session: Session) -> None:
    game = create_game(db_session, game_data("lookup"))
    db_session.commit()

    assert get_game_by_id(db_session, game.id) is game
    assert get_game_by_external_id(db_session, "lookup") is game
    assert external_id_exists(db_session, "lookup") is True
    assert external_id_exists(db_session, "missing") is False
    assert get_game_by_id(db_session, 99999) is None


def test_duplicate_external_id_uses_database_constraint(db_session: Session) -> None:
    create_game(db_session, game_data("duplicate"))
    db_session.commit()

    with pytest.raises(IntegrityError):
        create_game(db_session, game_data("duplicate"))
    db_session.rollback()


def test_analysis_status_transitions_and_timestamp(db_session: Session) -> None:
    game = create_game(db_session, game_data("status"))
    assert set_analysis_status(db_session, game, AnalysisStatus.ANALYZING).analyzed_at is None

    set_analysis_status(db_session, game, AnalysisStatus.COMPLETED)
    assert game.analyzed_at is not None
    assert game.analyzed_at.tzinfo is not None

    set_analysis_status(db_session, game, AnalysisStatus.FAILED)
    assert game.analyzed_at is None

    with pytest.raises(ValueError, match="invalid analysis status"):
        set_analysis_status(db_session, game, "invalid")  # type: ignore[arg-type]


def test_pending_failed_and_filters(db_session: Session) -> None:
    pending = create_game(db_session, game_data("pending", result=GameResult.DRAW))
    failed = create_game(
        db_session,
        game_data(
            "failed",
            analysis_status=AnalysisStatus.FAILED,
            opening_name="SICILIAN Defense",
        ),
    )
    create_game(db_session, game_data("done", analysis_status=AnalysisStatus.COMPLETED))
    db_session.commit()

    assert [g.id for g in list_analyzable_games(db_session)] == [pending.id, failed.id]
    assert list_games_by_analysis_status(db_session, AnalysisStatus.FAILED) == [failed]
    assert list_games(db_session, result=GameResult.DRAW) == [pending]
    assert list_games(db_session, analysis_status=AnalysisStatus.FAILED) == [failed]
    assert list_games(db_session, opening="sicilian") == [failed]
    assert list_games(db_session, opening=" b20 ") == []
    assert len(list_games(db_session, opening="   ")) == 3


def test_pagination_sorting_and_validation(db_session: Session) -> None:
    games = [
        create_game(db_session, game_data(f"page-{index}", played_at=NOW + timedelta(days=index)))
        for index in range(4)
    ]
    db_session.commit()

    assert list_games(db_session, sort="newest") == list(reversed(games))
    assert list_games(db_session, sort="oldest") == games
    assert list_games(db_session, sort="oldest", limit=2, offset=1) == games[1:3]

    for kwargs in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"sort": "unsafe SQL"}):
        with pytest.raises(ValueError):
            list_games(db_session, **kwargs)


def test_personal_analytics_sorts_before_pagination(db_session: Session) -> None:
    games = [
        create_game(db_session, game_data(f"analytics-{index}", played_at=NOW + timedelta(days=index)))
        for index in range(4)
    ]
    db_session.flush()

    # ID order differs from both rankings. Opponent extremes must not contribute.
    specifications = [
        [(True, 20, MoveClassification.NORMAL), (False, 9999, MoveClassification.BLUNDER)],
        [(True, 300, MoveClassification.BLUNDER)],
        [(True, 200, MoveClassification.BLUNDER), (True, 200, MoveClassification.BLUNDER)],
        [],
    ]
    for game, moves in zip(games, specifications, strict=True):
        for index, (user, loss, classification) in enumerate(moves, start=1):
            create_move_analysis(
                db_session,
                move_data(game.id, index, user=user, loss=loss, classification=classification),
            )
    db_session.commit()

    assert list_games(db_session, sort="most_blunders", limit=2) == [games[2], games[1]]
    assert list_games(db_session, sort="highest_cp_loss", limit=2) == [games[1], games[2]]
    assert list_games(db_session, sort="most_blunders")[-1] is games[3]
    assert list_games(db_session, sort="highest_cp_loss")[-1] is games[3]


def test_analytics_tie_breaker_is_stable(db_session: Session) -> None:
    older = create_game(db_session, game_data("tie-old", played_at=NOW))
    newer = create_game(db_session, game_data("tie-new", played_at=NOW + timedelta(days=1)))
    db_session.flush()
    for game in (older, newer):
        create_move_analysis(db_session, move_data(game.id, 1, user=True, loss=100))
    db_session.commit()

    assert list_games(db_session, sort="highest_cp_loss") == [newer, older]
