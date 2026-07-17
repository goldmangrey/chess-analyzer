import os

import chess
import chess.engine
import pytest

from app.services.stockfish_service import (
    MATE_SCORE,
    StockfishAnalysisError,
    StockfishNotFoundError,
    StockfishService,
    StockfishStartError,
)


class FakeEngine:
    def __init__(self, info=None, error: Exception | None = None) -> None:
        self.info = info
        self.error = error
        self.quit_count = 0
        self.limits = []

    def analyse(self, board, limit):
        self.limits.append(limit)
        if self.error:
            raise self.error
        return self.info

    def quit(self) -> None:
        self.quit_count += 1


def test_missing_and_non_executable_binary(tmp_path) -> None:
    with pytest.raises(StockfishNotFoundError):
        StockfishService(str(tmp_path / "missing"), 250, 6).start()

    binary = tmp_path / "stockfish"
    binary.write_text("fake")
    with pytest.raises(StockfishStartError, match="not executable"):
        StockfishService(str(binary), 250, 6).start()


def test_engine_starts_closes_and_close_is_idempotent(monkeypatch, tmp_path) -> None:
    binary = tmp_path / "stockfish"
    binary.write_text("fake")
    os.chmod(binary, 0o700)
    engine = FakeEngine()
    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda path: engine)

    service = StockfishService(str(binary), 250, 6).start()
    service.close()
    service.close()
    assert engine.quit_count == 1


def test_analysis_time_score_best_move_pv_and_board_safety() -> None:
    board = chess.Board()
    original_fen = board.fen()
    pv = [chess.Move.from_uci(move) for move in ("e2e4", "e7e5", "g1f3")]
    engine = FakeEngine({"score": chess.engine.PovScore(chess.engine.Cp(42), chess.WHITE), "pv": pv})

    with StockfishService("ignored", 250, 2, engine=engine) as service:
        result = service.analyze_position(board)

    assert engine.limits[0].time == 0.25
    assert result.evaluation_cp == 42
    assert (result.best_move_uci, result.best_move_san) == ("e2e4", "e4")
    assert result.principal_variation == ("e4", "e5")
    assert board.fen() == original_fen


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (chess.engine.PovScore(chess.engine.Cp(30), chess.WHITE), 30),
        (chess.engine.PovScore(chess.engine.Cp(30), chess.BLACK), -30),
        (chess.engine.PovScore(chess.engine.Mate(3), chess.WHITE), MATE_SCORE),
        (chess.engine.PovScore(chess.engine.Mate(3), chess.BLACK), -MATE_SCORE),
    ],
)
def test_white_perspective_and_mate(score, expected: int) -> None:
    engine = FakeEngine({"score": score, "pv": []})
    with StockfishService("ignored", 200, 6, engine=engine) as service:
        result = service.analyze_position(chess.Board())
    assert result.evaluation_cp == expected
    assert result.best_move_uci is None
    assert result.best_move_san is None
    assert result.principal_variation == ()


def test_engine_exception_is_domain_error() -> None:
    engine = FakeEngine(error=chess.engine.EngineError("broken"))
    with StockfishService("ignored", 250, 6, engine=engine) as service:
        with pytest.raises(StockfishAnalysisError):
            service.analyze_position(chess.Board())


def test_analysis_before_start_is_rejected() -> None:
    with pytest.raises(StockfishStartError):
        StockfishService("ignored", 250, 6, engine=FakeEngine()).analyze_position(chess.Board())


def test_terminal_position_is_evaluated_without_engine_call() -> None:
    board = chess.Board()
    for move in ("f2f3", "e7e5", "g2g4", "d8h4"):
        board.push_uci(move)
    engine = FakeEngine(error=AssertionError("engine must not be called"))
    with StockfishService("ignored", 250, 6, engine=engine) as service:
        result = service.analyze_position(board)
    assert result.evaluation_cp == -MATE_SCORE
    assert result.best_move_uci is None
