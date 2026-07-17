from app.config import Settings
from app.services.chesscom_client import ChessComNetworkError
from app.services.game_importer import ImportGamesResult
from scripts.import_games import main


class FakeSession:
    def __init__(self) -> None:
        self.committed = self.rolled_back = self.closed = False

    def commit(self) -> None: self.committed = True
    def rollback(self) -> None: self.rolled_back = True
    def close(self) -> None: self.closed = True


class FakeClient:
    def __init__(self) -> None: self.closed = False
    def close(self) -> None: self.closed = True


def test_cli_arguments_defaults_success_output_and_cleanup(capsys) -> None:
    settings = Settings(_env_file=None, CHESS_USERNAME="Default", IMPORT_GAMES_LIMIT=7)
    session = FakeSession()
    client = FakeClient()
    calls = []

    def importer(active_session, active_client, username, limit):
        calls.append((active_session, active_client, username, limit))
        return ImportGamesResult(limit, 2, 1, 3, 6, (1, 2))

    exit_code = main(
        [], settings=settings, session_factory=lambda: session,
        client_factory=lambda user_agent: client, init_database=lambda: None, importer=importer,
    )
    assert exit_code == 0
    assert calls[0][2:] == ("Default", 7)
    assert session.committed and session.closed and client.closed
    assert "Imported: 2\nDuplicates: 1\nInvalid: 3\nExamined: 6" in capsys.readouterr().out

    other_session, other_client = FakeSession(), FakeClient()
    main(
        ["--username", "Explicit", "--limit", "4"], settings=settings,
        session_factory=lambda: other_session, client_factory=lambda user_agent: other_client,
        init_database=lambda: None, importer=importer,
    )
    assert calls[-1][2:] == ("Explicit", 4)


def test_cli_error_rolls_back_closes_and_returns_nonzero(capsys) -> None:
    session, client = FakeSession(), FakeClient()

    def failing_importer(*args):
        raise ChessComNetworkError("offline")

    exit_code = main(
        [], settings=Settings(_env_file=None), session_factory=lambda: session,
        client_factory=lambda user_agent: client, init_database=lambda: None,
        importer=failing_importer,
    )
    assert exit_code == 1
    assert session.rolled_back and session.closed and client.closed
    assert "Import failed: offline" in capsys.readouterr().err
