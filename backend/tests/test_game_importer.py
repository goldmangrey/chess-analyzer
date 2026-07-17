from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AnalysisStatus, Color, Game, MoveAnalysis
from app.repositories.games_repository import create_game
from app.schemas import GameCreate
from app.services.chesscom_client import ChessComGameRecord, ChessComNetworkError, ChessComUserNotFoundError
from app.services.game_importer import import_recent_games


def game_pgn(external: str, *, user_black: bool = False, valid: bool = True) -> str:
    if not valid:
        return "broken"
    white, black, result = ("Opponent", "Yeskendir", "0-1") if user_black else ("Yeskendir", "Opponent", "1-0")
    return f'''[Event "{external}"]
[Site "Chess.com"]
[Date "2026.07.16"]
[White "{white}"]
[Black "{black}"]
[Result "{result}"]

1. e4 e5 {result}
'''


class FakeClient:
    def __init__(self, records=(), error: Exception | None = None) -> None:
        self.records = records
        self.error = error
        self.examined_by_client = 0

    def iter_recent_games(self, username: str) -> Iterator[ChessComGameRecord]:
        if self.error:
            raise self.error
        for record in self.records:
            self.examined_by_client += 1
            yield record


def record(identifier: str, *, valid: bool = True, user_black: bool = False) -> ChessComGameRecord:
    return ChessComGameRecord(identifier, identifier, game_pgn(identifier, valid=valid, user_black=user_black), 1)


def test_imports_games_pending_without_moves_and_outer_rollback(db_session: Session) -> None:
    client = FakeClient([record("white"), record("black", user_black=True)])
    result = import_recent_games(db_session, client, "Yeskendir", 2)

    games = db_session.scalars(select(Game).order_by(Game.id)).all()
    assert result.imported == 2
    assert result.imported_game_ids == tuple(game.id for game in games)
    assert [game.user_color for game in games] == [Color.WHITE, Color.BLACK]
    assert all(game.platform == "chess.com" and game.analysis_status is AnalysisStatus.PENDING for game in games)
    assert db_session.scalar(select(func.count(MoveAnalysis.id))) == 0

    db_session.rollback()
    assert db_session.scalar(select(func.count(Game.id))) == 0


def test_external_commit_persists_import(db_session: Session) -> None:
    import_recent_games(db_session, FakeClient([record("commit")]), "Yeskendir", 1)
    db_session.commit()
    assert db_session.scalar(select(func.count(Game.id))) == 1


def test_duplicates_and_invalid_do_not_consume_limit(db_session: Session) -> None:
    create_game(db_session, GameCreate(
        external_id="duplicate", white_username="Yeskendir", black_username="Opponent",
        user_color=Color.WHITE, result="win", pgn=game_pgn("duplicate"),
    ))
    db_session.commit()
    client = FakeClient([record("duplicate"), record("invalid", valid=False), record("new-1"), record("new-2"), record("unread")])

    result = import_recent_games(db_session, client, "Yeskendir", 2)
    assert (result.imported, result.skipped_duplicates, result.skipped_invalid, result.examined) == (2, 1, 1, 4)
    assert client.examined_by_client == 4


def test_archive_exhaustion_can_return_less_than_limit(db_session: Session) -> None:
    result = import_recent_games(db_session, FakeClient([record("only")]), "Yeskendir", 3)
    assert result.imported == 1


@pytest.mark.parametrize(("username", "limit"), [(" ", 1), ("name", 0), ("name", 51)])
def test_invalid_arguments(username: str, limit: int, db_session: Session) -> None:
    with pytest.raises(ValueError):
        import_recent_games(db_session, FakeClient(), username, limit)


@pytest.mark.parametrize("error", [ChessComNetworkError("offline"), ChessComUserNotFoundError("missing")])
def test_chesscom_errors_propagate(error: Exception, db_session: Session) -> None:
    with pytest.raises(type(error)):
        import_recent_games(db_session, FakeClient(error=error), "Yeskendir", 1)


def test_unique_constraint_race_is_local_to_savepoint(monkeypatch, db_session: Session) -> None:
    create_game(db_session, GameCreate(
        external_id="race", white_username="Yeskendir", black_username="Opponent",
        user_color=Color.WHITE, result="win", pgn=game_pgn("race"),
    ))
    db_session.commit()
    monkeypatch.setattr("app.services.game_importer.external_id_exists", lambda session, external_id: False)

    result = import_recent_games(db_session, FakeClient([record("race"), record("after-race")]), "Yeskendir", 1)
    assert result.skipped_duplicates == 1
    assert result.imported == 1
    assert db_session.scalar(select(func.count(Game.id))) == 2
