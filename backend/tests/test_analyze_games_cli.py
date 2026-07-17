from app.config import Settings
from app.models import AnalysisStatus, Game
from app.services.analysis_service import AnalysisResult, AnalysisServiceError
from scripts import analyze_games as cli


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def fake_game(game_id: int) -> Game:
    return Game(id=game_id, external_id=str(game_id), white_username="W", black_username="B", user_color="white", result="win", pgn="pgn", analysis_status=AnalysisStatus.PENDING)


def test_pending_limit_success_output_and_resources(monkeypatch, capsys) -> None:
    session = FakeSession()
    games = [fake_game(1), fake_game(2)]
    monkeypatch.setattr(cli, "list_games_by_analysis_status", lambda session, status, limit: games[:limit])
    calls = []

    def analyzer(session, game_id):
        calls.append(game_id)
        return AnalysisResult(game_id, AnalysisStatus.COMPLETED, 4)

    result = cli.main(
        ["--pending", "--limit", "2"],
        settings=Settings(_env_file=None),
        session_factory=lambda: session,
        init_database=lambda: None,
        analyzer=analyzer,
    )
    output = capsys.readouterr().out
    assert result == 0
    assert calls == [1, 2]
    assert "Completed: 4 plies" in output
    assert "Summary:\nCompleted: 2\nFailed: 0" in output
    assert session.closed


def test_game_id_selection(monkeypatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(cli, "get_game_by_id", lambda session, game_id: fake_game(game_id))
    calls = []
    result = cli.main(
        ["--game-id", "42"], settings=Settings(_env_file=None),
        session_factory=lambda: session, init_database=lambda: None,
        analyzer=lambda session, game_id: calls.append(game_id) or AnalysisResult(game_id, AnalysisStatus.COMPLETED, 1),
    )
    assert result == 0
    assert calls == [42]


def test_failure_continues_and_prints_stockfish_path(monkeypatch, capsys) -> None:
    session = FakeSession()
    monkeypatch.setattr(cli, "list_games_by_analysis_status", lambda session, status, limit: [fake_game(1), fake_game(2)])

    def analyzer(session, game_id):
        if game_id == 1:
            raise AnalysisServiceError("Stockfish binary not found")
        return AnalysisResult(game_id, AnalysisStatus.COMPLETED, 2)

    result = cli.main(
        ["--failed"], settings=Settings(_env_file=None, STOCKFISH_PATH="/missing/stockfish"),
        session_factory=lambda: session, init_database=lambda: None, analyzer=analyzer,
    )
    captured = capsys.readouterr()
    assert result == 1
    assert "Completed: 1\nFailed: 1" in captured.out
    assert "Check STOCKFISH_PATH (/missing/stockfish)" in captured.err
    assert session.closed
